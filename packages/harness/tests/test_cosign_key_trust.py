from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import replace
from importlib.metadata import Distribution
from pathlib import Path
from typing import Any

import pytest

from robotics_acceptance_harness.evaluator_trust import (
    AuthenticatedWheel,
    CosignKeyVerifierProfile,
    CosignKeyWheelPolicy,
    EvaluatorTrustError,
    TrustLimits,
    authenticate_wheel_with_cosign_key,
    verify_installed_wheel,
)
from tests.test_evaluator_trust import DIST_INFO, fixture_wheel

PREDICATE = "urn:org.example:evaluator-qualification:v1"


def cosign(tool: Path, root: Path, *arguments: str) -> bytes:
    # Temporary publisher only; no key material is printed or retained.
    environment = {
        "HOME": str(root),
        "XDG_CONFIG_HOME": str(root / "config"),
        "COSIGN_PASSWORD": "",
        "LC_ALL": "C.UTF-8",
    }
    completed = subprocess.run(
        [str(tool), *arguments],
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode:
        raise AssertionError("stock Cosign fixture operation refused") from None
    return completed.stdout


@pytest.fixture
def local_publisher(tmp_path: Path) -> tuple[Any, ...]:
    profile_path = os.environ.get("ROBOTICS_COSIGN_PROFILE")
    if profile_path is None:
        pytest.skip("an externally admitted actual Cosign profile is required")
    values = json.loads(Path(profile_path).read_bytes())
    tool = Path(values["executable"])
    assert hashlib.sha256(tool.read_bytes()).hexdigest() == values["executable_sha256"]
    version = json.loads(cosign(tool, tmp_path, "version", "--json"))
    assert version["gitVersion"] == values["version"]
    wheel, installed = fixture_wheel(tmp_path)
    cosign(tool, tmp_path, "signing-config", "create", "--out", "signing.json")
    cosign(tool, tmp_path, "trusted-root", "create", "--out", "roots.json")
    cosign(tool, tmp_path, "generate-key-pair", "--output-key-prefix", "publisher")
    predicate = tmp_path / "predicate.json"
    predicate.write_text('{"scope":"temporary local publisher unit method controls"}')
    bundle = tmp_path / "wheel.sigstore.json"
    cosign(
        tool,
        tmp_path,
        "attest-blob",
        "--yes",
        "--key",
        "publisher.key",
        "--signing-config",
        "signing.json",
        "--trusted-root",
        "roots.json",
        "--type",
        PREDICATE,
        "--predicate",
        str(predicate),
        "--bundle",
        str(bundle),
        str(wheel),
    )
    key, root = tmp_path / "publisher.pub", tmp_path / "roots.json"
    profile = CosignKeyVerifierProfile(
        tool,
        values["executable_sha256"],
        values["version"],
        key,
        hashlib.sha256(key.read_bytes()).hexdigest(),
        root,
        hashlib.sha256(root.read_bytes()).hexdigest(),
    )
    policy = CosignKeyWheelPolicy(
        hashlib.sha256(wheel.read_bytes()).hexdigest(),
        PREDICATE,
        profile.public_key_sha256,
        "key_only_no_tlog",
    )
    # Remove the temporary private signing material before verification tests.
    (tmp_path / "publisher.key").unlink()
    return wheel, bundle, installed, profile, policy


def test_actual_local_key_authenticates_original_wheel_and_installation(
    local_publisher: tuple[Any, ...],
) -> None:
    wheel, bundle, installed, profile, policy = local_publisher
    authenticated = authenticate_wheel_with_cosign_key(
        wheel, bundle, profile=profile, policy=policy
    )
    bound = verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))
    assert bound.wheel_sha256 == policy.wheel_sha256
    assert isinstance(authenticated.policy, CosignKeyWheelPolicy)
    assert authenticated.policy.trust_mode == "key_only_no_tlog"
    wheel.write_bytes(b"changed after original authenticated capture")
    assert authenticated.wheel_bytes != wheel.read_bytes()


@pytest.mark.parametrize("fault", ["wrong-key", "dsse", "subject", "predicate", "fake-report"])
def test_actual_local_key_rejects_unadmitted_crypto_inputs(
    local_publisher: tuple[Any, ...], tmp_path: Path, fault: str
) -> None:
    wheel, bundle, _, profile, policy = local_publisher
    if fault == "wrong-key":
        cosign(profile.executable, tmp_path, "generate-key-pair", "--output-key-prefix", "other")
        key = tmp_path / "other.pub"
        profile = replace(
            profile, public_key=key, public_key_sha256=hashlib.sha256(key.read_bytes()).hexdigest()
        )
        policy = replace(policy, public_key_sha256=profile.public_key_sha256)
        (tmp_path / "other.key").unlink()
    elif fault == "dsse":
        data = json.loads(bundle.read_bytes())
        data["dsseEnvelope"]["payload"] += "A"
        bundle.write_text(json.dumps(data))
    elif fault == "subject":
        wheel.write_bytes(wheel.read_bytes() + b"altered subject")
        policy = replace(policy, wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest())
    elif fault == "predicate":
        policy = replace(policy, predicate_type=PREDICATE + "-other")
    else:
        bundle.write_text('{"verificationResult":{"status":"passed"}}')
    with pytest.raises(EvaluatorTrustError):
        authenticate_wheel_with_cosign_key(wheel, bundle, profile=profile, policy=policy)


def test_local_key_report_or_constructor_cannot_issue_admission(
    local_publisher: tuple[Any, ...],
) -> None:
    wheel, bundle, installed, profile, policy = local_publisher
    real = authenticate_wheel_with_cosign_key(wheel, bundle, profile=profile, policy=policy)
    fabricated = AuthenticatedWheel(
        real.filename,
        real.wheel_bytes,
        real.sha256,
        real.bundle_sha256,
        policy,
        real.verifier_sha256,
        real.trusted_root_sha256,
        b"Verified OK",
        real.limits,
    )
    for value in (fabricated, replace(real)):
        with pytest.raises(EvaluatorTrustError, match="authenticated in-memory"):
            verify_installed_wheel(value, Distribution.at(installed / DIST_INFO))


def test_actual_local_key_raw_inputs_are_bounded(local_publisher: tuple[Any, ...]) -> None:
    wheel, bundle, _, profile, policy = local_publisher
    with pytest.raises(EvaluatorTrustError, match="bounded regular file"):
        authenticate_wheel_with_cosign_key(
            wheel,
            bundle,
            profile=profile,
            policy=policy,
            limits=TrustLimits(max_bundle_bytes=1),
        )


def test_key_only_policy_requires_explicit_mode() -> None:
    with pytest.raises(EvaluatorTrustError, match="explicit choice"):
        CosignKeyWheelPolicy("a" * 64, PREDICATE, "b" * 64, "github")  # type: ignore[arg-type]


def test_vendor_dirty_version_cannot_be_relabelled_clean(
    local_publisher: tuple[Any, ...],
) -> None:
    wheel, bundle, _, profile, policy = local_publisher
    with pytest.raises(EvaluatorTrustError, match="version differs"):
        authenticate_wheel_with_cosign_key(
            wheel,
            bundle,
            profile=replace(profile, version="v3.1.3"),
            policy=policy,
        )


def test_fake_executable_cannot_replace_the_admitted_verifier(
    local_publisher: tuple[Any, ...], tmp_path: Path
) -> None:
    wheel, bundle, _, profile, policy = local_publisher
    executable = tmp_path / "fake-verifier"
    executable.write_bytes(b"echo Verified OK")
    with pytest.raises(EvaluatorTrustError, match="pinned digest"):
        authenticate_wheel_with_cosign_key(
            wheel,
            bundle,
            profile=replace(profile, executable=executable),
            policy=policy,
        )


def test_combined_cosign_audit_cannot_exceed_the_declared_report_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from robotics_acceptance_harness import evaluator_trust as trust

    def run(_command: list[str], **keywords: Any) -> SimpleNamespace:
        keywords["stdout"].write(b"abc")
        keywords["stderr"].write(b"def")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(EvaluatorTrustError, match="combined verifier audit"):
        trust._run_tool(
            [str(tmp_path / "cosign"), "verify-blob-attestation"],
            tmp_path,
            TrustLimits(max_report_bytes=4),
            tool_name="cosign",
        )
