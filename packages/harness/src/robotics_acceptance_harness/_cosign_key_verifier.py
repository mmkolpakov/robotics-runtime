"""The closed Cosign key-only verifier; cryptography stays in stock Cosign."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from packaging.version import Version

from robotics_acceptance_harness.evaluator_trust import (
    CosignKeyVerifierProfile,
    CosignKeyWheelPolicy,
    EvaluatorTrustError,
    TrustLimits,
    _pinned_snapshot,
    _run_tool,
)


@contextmanager
def _verifier_snapshot(
    profile: CosignKeyVerifierProfile, limits: TrustLimits, *, deadline: float | None = None
) -> Iterator[tuple[Path, Path, Path, Path]]:
    tool = _pinned_snapshot(profile.executable, profile.executable_sha256, limits.max_tool_bytes)
    key = _pinned_snapshot(profile.public_key, profile.public_key_sha256, limits.max_root_bytes)
    root = _pinned_snapshot(
        profile.trusted_root, profile.trusted_root_sha256, limits.max_root_bytes
    )
    with TemporaryDirectory(prefix="evaluator-key-verification-") as temporary:
        directory = Path(temporary)
        executable = directory / ("cosign.exe" if os.name == "nt" else "cosign")
        executable.write_bytes(tool)
        executable.chmod(0o500)
        key_path, root_path = directory / "publisher.pub", directory / "root.json"
        for path, payload in ((key_path, key), (root_path, root)):
            path.write_bytes(payload)
            path.chmod(0o400)
        version = json.loads(
            _run_tool(
                [str(executable), "version", "--json"],
                directory,
                limits,
                tool_name="cosign",
                deadline=deadline,
            )
        )
        if not isinstance(version, dict) or version.get("gitVersion") != profile.version:
            raise EvaluatorTrustError("Cosign version differs from its admitted operator profile")
        yield directory, executable, key_path, root_path


def _input_snapshots(
    directory: Path, artifact: tuple[str, bytes], bundle: bytes
) -> tuple[Path, Path]:
    artifact_path, bundle_path = directory / artifact[0], directory / "bundle.sigstore.json"
    for path, payload in ((artifact_path, artifact[1]), (bundle_path, bundle)):
        path.write_bytes(payload)
        path.chmod(0o400)
    return artifact_path, bundle_path


def verify_snapshot(
    artifact: tuple[str, bytes],
    bundle: bytes,
    policy: CosignKeyWheelPolicy,
    profile: CosignKeyVerifierProfile,
    limits: TrustLimits,
) -> bytes:
    with _verifier_snapshot(profile, limits) as (directory, executable, key_path, root_path):
        wheel_path, bundle_path = _input_snapshots(directory, artifact, bundle)
        return _run_tool(
            [
                str(executable),
                "verify-blob-attestation",
                "--check-claims=true",
                "--type",
                policy.predicate_type,
                "--bundle",
                str(bundle_path),
                "--key",
                str(key_path),
                "--trusted-root",
                str(root_path),
                "--insecure-ignore-tlog",
                str(wheel_path),
            ],
            directory,
            limits,
            tool_name="cosign",
        )


def verify_blob_snapshot(
    artifact: bytes,
    bundle: bytes,
    profile: CosignKeyVerifierProfile,
    limits: TrustLimits,
    *,
    deadline: float | None = None,
) -> bytes:
    if Version(profile.version) < Version("3.1.4"):
        raise EvaluatorTrustError("OCI blob verification requires an admitted Cosign >=3.1.4")
    with _verifier_snapshot(profile, limits, deadline=deadline) as (
        directory,
        executable,
        key_path,
        root_path,
    ):
        artifact_path, bundle_path = _input_snapshots(
            directory, ("manifest.json", artifact), bundle
        )
        return _run_tool(
            [
                str(executable),
                "verify-blob",
                "--bundle",
                str(bundle_path),
                "--key",
                str(key_path),
                "--trusted-root",
                str(root_path),
                "--insecure-ignore-tlog",
                str(artifact_path),
            ],
            directory,
            limits,
            tool_name="cosign",
            deadline=deadline,
        )
