from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from robotics_acceptance_harness import _cosign_key_verifier as cosign
from robotics_acceptance_harness import _oci_manifest_trust as oci
from robotics_acceptance_harness.evaluator_trust import (
    DEFAULT_TRUST_LIMITS,
    CosignKeyVerifierProfile,
    CosignKeyWheelPolicy,
    EvaluatorTrustError,
    TrustLimits,
)

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX verifier input profile")
PLATFORM = {"os": "linux", "architecture": "amd64"}
MANIFEST_TYPE = "application/vnd.oci.image.manifest.v1+json"
CONFIG_TYPE = "application/vnd.oci.image.config.v1+json"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fake_profile(root: Path, version: str = "v3.1.4+dirty") -> CosignKeyVerifierProfile:
    tool, key, trust_root = root / "unit-cosign", root / "key.pub", root / "root.json"
    key.write_bytes(b"unit-key")
    trust_root.write_bytes(b"{}")
    tool.write_text(
        f"#!{sys.executable}\n"
        "import hashlib, json, os, signal, stat, sys\n"
        "from pathlib import Path\n"
        "signal.alarm(3)\n"
        "args = sys.argv[1:]\n"
        f"if args == ['version', '--json']:\n    print(json.dumps({{'gitVersion': {version!r}}}))\n"
        "else:\n"
        "    mode = args.pop(0)\n"
        "    if mode == 'verify-blob-attestation':\n"
        "        assert args[:3] == ['--check-claims=true', '--type', 'urn:unit:wheel']\n"
        "        args = args[3:]\n"
        "        os.write(1, b'legacy')\n"
        "    else:\n        assert mode == 'verify-blob'\n"
        "    assert args[0::2][:3] == ['--bundle', '--key', '--trusted-root']\n"
        "    assert args[6] == '--insecure-ignore-tlog' and len(args) == 8\n"
        "    paths = [Path(args[i]) for i in [1, 3, 5, 7]]\n"
        "    assert all(stat.S_IMODE(p.stat().st_mode) == 0o400 for p in paths)\n"
        "    assert paths[1].read_bytes() == b'unit-key'\n"
        "    assert paths[2].read_bytes() == b'{}'\n"
        "    expected = hashlib.sha256(paths[3].read_bytes()).hexdigest().encode()\n"
        "    if paths[0].read_bytes() != expected:\n"
        "        os.write(2, b'unit fixture refused'); sys.exit(1)\n"
        "    assert os.read(0, 1) == b''\n"
        "    os.write(2, b'unit fixture verified')\n"
    )
    tool.chmod(0o500)
    return CosignKeyVerifierProfile(
        tool,
        digest(tool.read_bytes()),
        version,
        key,
        digest(key.read_bytes()),
        trust_root,
        digest(trust_root.read_bytes()),
    )


def inputs(root: Path) -> tuple[Path, Path, Path, str]:
    config = json.dumps(PLATFORM).encode()
    manifest = json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": MANIFEST_TYPE,
            "config": {
                "mediaType": CONFIG_TYPE,
                "digest": "sha256:" + digest(config),
                "size": len(config),
            },
            "layers": [],
        }
    ).encode()
    paths = root / "manifest.json", root / "config.json", root / "bundle.json"
    for path, raw in zip(paths, (manifest, config, digest(manifest).encode()), strict=True):
        path.write_bytes(raw)
    return *paths, "sha256:" + digest(manifest)


def call(root: Path, *, limits: TrustLimits = DEFAULT_TRUST_LIMITS) -> tuple[bytes, bytes, bytes]:
    manifest, config, bundle, expected = inputs(root)
    return oci.authenticate_manifest(
        (manifest, config, bundle),
        expected_digest=expected,
        platform=PLATFORM,
        profile=fake_profile(root),
        limits=limits,
    )


def test_finite_fake_verifier_accepts_empty_stdout_and_retains_exact_bytes(tmp_path: Path) -> None:
    manifest, config, audit = call(tmp_path)
    assert manifest == (tmp_path / "manifest.json").read_bytes()
    assert config == (tmp_path / "config.json").read_bytes()
    assert audit == b"unit fixture verified"


@pytest.mark.parametrize(
    "fault",
    [
        "index",
        "schema-version",
        "config-media",
        "config-digest",
        "config-size",
        "boolean-size",
        "os",
        "architecture",
        "variant",
        "duplicate-key",
        "nonfinite",
    ],
)
def test_identity_refuses_before_verifier_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    manifest, config, bundle, _ = inputs(tmp_path)
    document = json.loads(manifest.read_bytes())
    if fault == "index":
        document["mediaType"] = "application/vnd.oci.image.index.v1+json"
    elif fault == "schema-version":
        document["schemaVersion"] = 1
    elif fault.startswith("config-"):
        field = fault.removeprefix("config-")
        field = "mediaType" if field == "media" else field
        document["config"][field] = 1 if field == "size" else "wrong"
    elif fault == "boolean-size":
        document["config"]["size"] = True
    elif fault in {"os", "architecture", "variant"}:
        values = {**PLATFORM, fault: "wrong"}
        config.write_bytes(json.dumps(values).encode())
        document["config"]["digest"] = "sha256:" + digest(config.read_bytes())
        document["config"]["size"] = config.stat().st_size
    raw = json.dumps(document).encode()
    if fault == "duplicate-key":
        raw = raw.replace(b'"schemaVersion": 2', b'"schemaVersion": 2, "schemaVersion": 2')
    if fault == "nonfinite":
        raw = raw.replace(b'"schemaVersion": 2', b'"schemaVersion": NaN')
    manifest.write_bytes(raw)

    def forbidden(*args: Any, **kwargs: Any) -> bytes:
        pytest.fail("identity refusal reached verifier")

    monkeypatch.setattr(oci, "verify_blob_snapshot", forbidden)
    with pytest.raises(EvaluatorTrustError):
        oci.authenticate_manifest(
            (manifest, config, bundle),
            expected_digest="sha256:" + digest(raw),
            platform=PLATFORM,
            profile=fake_profile(tmp_path),
        )


@pytest.mark.parametrize("expected", ["a" * 64, "sha512:" + "a" * 64, "sha256:" + "a" * 64])
def test_external_subject_must_match_original_manifest(tmp_path: Path, expected: str) -> None:
    manifest, config, bundle, _ = inputs(tmp_path)
    with pytest.raises(EvaluatorTrustError):
        oci.authenticate_manifest(
            (manifest, config, bundle),
            expected_digest=expected,
            platform=PLATFORM,
            profile=fake_profile(tmp_path),
        )


@pytest.mark.parametrize("platform", [{}, {**PLATFORM, "variant": ""}, {**PLATFORM, "extra": "x"}])
def test_external_platform_is_closed(tmp_path: Path, platform: dict[str, str]) -> None:
    manifest, config, bundle, expected = inputs(tmp_path)
    with pytest.raises(EvaluatorTrustError, match="platform requires"):
        oci.authenticate_manifest(
            (manifest, config, bundle),
            expected_digest=expected,
            platform=platform,
            profile=fake_profile(tmp_path),
        )


def test_capture_survives_original_path_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, config, bundle, expected = inputs(tmp_path)
    original = manifest.read_bytes(), config.read_bytes()
    verifier = cosign.verify_blob_snapshot

    def changed(
        raw: bytes, signature: bytes, profile: CosignKeyVerifierProfile, limits: TrustLimits
    ) -> bytes:
        for path in (manifest, config, bundle):
            path.write_bytes(b"changed original path")
        return verifier(raw, signature, profile, limits)

    monkeypatch.setattr(oci, "verify_blob_snapshot", changed)
    observed = oci.authenticate_manifest(
        (manifest, config, bundle),
        expected_digest=expected,
        platform=PLATFORM,
        profile=fake_profile(tmp_path),
    )
    assert observed[:2] == original


@pytest.mark.parametrize("fault", ["bundle", "key-pin", "tool-pin", "version", "old-version"])
def test_verifier_refusal_cannot_return_captured_admission(tmp_path: Path, fault: str) -> None:
    manifest, config, bundle, expected = inputs(tmp_path)
    profile = fake_profile(tmp_path)
    if fault == "bundle":
        bundle.write_bytes(b"not the unit verifier fixture")
    elif fault == "key-pin":
        profile.public_key.write_bytes(b"wrong pinned key")
    elif fault == "tool-pin":
        profile.executable.unlink()
        profile.executable.write_bytes(b"replaced executable")
    elif fault == "version":
        profile = replace(profile, version="v3.1.4")
    else:
        profile = replace(profile, version="v3.1.3")
    with pytest.raises(EvaluatorTrustError):
        oci.authenticate_manifest(
            (manifest, config, bundle), expected_digest=expected, platform=PLATFORM, profile=profile
        )


@pytest.mark.parametrize("fault", ["oversize", "symlink", "fifo"])
def test_capture_refuses_unsafe_inputs(tmp_path: Path, fault: str) -> None:
    manifest, config, bundle, expected = inputs(tmp_path)
    limits = TrustLimits()
    if fault == "oversize":
        limits = TrustLimits(max_bundle_bytes=4)
    elif fault == "symlink":
        other = tmp_path / "original.json"
        manifest.rename(other)
        manifest.symlink_to(other)
    else:
        manifest.unlink()
        os.mkfifo(manifest)
    with pytest.raises(EvaluatorTrustError):
        oci.authenticate_manifest(
            (manifest, config, bundle),
            expected_digest=expected,
            platform=PLATFORM,
            profile=fake_profile(tmp_path),
            limits=limits,
        )


def test_shared_snapshot_preserves_legacy_wheel_command_and_version_floor(tmp_path: Path) -> None:
    profile = fake_profile(tmp_path, "v3.1.3")
    artifact = b"wheel fixture"
    policy = CosignKeyWheelPolicy(
        digest(artifact), "urn:unit:wheel", profile.public_key_sha256, "key_only_no_tlog"
    )
    assert (
        cosign.verify_snapshot(
            ("example.whl", artifact), digest(artifact).encode(), policy, profile, TrustLimits()
        )
        == b"legacyunit fixture verified"
    )


def test_raw_blob_command_does_not_admit_signing_or_registry_operations(tmp_path: Path) -> None:
    from robotics_acceptance_harness.evaluator_trust import _run_tool

    for command in ("sign-blob", "verify", "download", "save"):
        with pytest.raises(EvaluatorTrustError, match="snapshot verifier commands"):
            _run_tool(
                [str(tmp_path / "cosign"), command], tmp_path, TrustLimits(), tool_name="cosign"
            )


@pytest.mark.parametrize("role", ["manifest", "config"])
def test_oci_documents_require_json_before_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    import yaml

    manifest, config, bundle, _ = inputs(tmp_path)
    target = manifest if role == "manifest" else config
    target.write_bytes(yaml.safe_dump(json.loads(target.read_bytes())).encode())
    if role == "config":
        document = json.loads(manifest.read_bytes())
        document["config"]["digest"] = "sha256:" + digest(config.read_bytes())
        document["config"]["size"] = config.stat().st_size
        manifest.write_bytes(json.dumps(document).encode())

    def forbidden(*args: Any, **kwargs: Any) -> bytes:
        pytest.fail("non-JSON OCI input reached verifier")

    monkeypatch.setattr(oci, "verify_blob_snapshot", forbidden)
    with pytest.raises(EvaluatorTrustError, match="invalid OCI"):
        oci.authenticate_manifest(
            (manifest, config, bundle),
            expected_digest="sha256:" + digest(manifest.read_bytes()),
            platform=PLATFORM,
            profile=fake_profile(tmp_path),
        )


def test_docker_schema2_preserves_original_manifest_and_config_bytes(tmp_path: Path) -> None:
    manifest, config, bundle, _ = inputs(tmp_path)
    original_config = b" \r\n" + config.read_bytes() + b"\n "
    config.write_bytes(original_config)
    document = json.loads(manifest.read_bytes())
    document["mediaType"] = "application/vnd.docker.distribution.manifest.v2+json"
    document["config"] = {
        "mediaType": "application/vnd.docker.container.image.v1+json",
        "digest": "sha256:" + digest(original_config),
        "size": len(original_config),
    }
    original_manifest = b"\r\n" + json.dumps(document, indent=2).encode() + b" \n"
    manifest.write_bytes(original_manifest)
    bundle.write_bytes(digest(original_manifest).encode())
    observed = oci.authenticate_manifest(
        (manifest, config, bundle),
        expected_digest="sha256:" + digest(original_manifest),
        platform=PLATFORM,
        profile=fake_profile(tmp_path),
    )
    assert observed == (original_manifest, original_config, b"unit fixture verified")


@pytest.mark.parametrize(
    ("manifest_type", "config_type"),
    [
        (MANIFEST_TYPE, "application/vnd.docker.container.image.v1+json"),
        ("application/vnd.docker.distribution.manifest.v2+json", CONFIG_TYPE),
        ("application/vnd.docker.distribution.manifest.list.v2+json", CONFIG_TYPE),
        ("application/vnd.oci.image.index.v1+json", CONFIG_TYPE),
        ([MANIFEST_TYPE], CONFIG_TYPE),
        ({"type": MANIFEST_TYPE}, CONFIG_TYPE),
    ],
)
def test_media_pair_refusal_is_closed_and_type_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    manifest_type: object,
    config_type: str,
) -> None:
    manifest, config, bundle, _ = inputs(tmp_path)
    document = json.loads(manifest.read_bytes())
    document["mediaType"] = manifest_type
    document["config"]["mediaType"] = config_type
    manifest.write_bytes(json.dumps(document).encode())

    def forbidden(*args: Any, **kwargs: Any) -> bytes:
        pytest.fail("unsupported image media pair reached verifier")

    monkeypatch.setattr(oci, "verify_blob_snapshot", forbidden)
    with pytest.raises(EvaluatorTrustError):
        oci.authenticate_manifest(
            (manifest, config, bundle),
            expected_digest="sha256:" + digest(manifest.read_bytes()),
            platform=PLATFORM,
            profile=fake_profile(tmp_path),
        )
