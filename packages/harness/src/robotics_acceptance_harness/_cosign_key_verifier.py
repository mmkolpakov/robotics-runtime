"""The closed Cosign key-only verifier; cryptography stays in stock Cosign."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from robotics_acceptance_harness.evaluator_trust import (
    CosignKeyVerifierProfile,
    CosignKeyWheelPolicy,
    EvaluatorTrustError,
    TrustLimits,
    _pinned_snapshot,
    _run_tool,
)


def verify_snapshot(
    artifact: tuple[str, bytes],
    bundle: bytes,
    policy: CosignKeyWheelPolicy,
    profile: CosignKeyVerifierProfile,
    limits: TrustLimits,
) -> bytes:
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
        wheel_path = directory / artifact[0]
        bundle_path, key_path, root_path = (
            directory / "bundle.sigstore.json",
            directory / "publisher.pub",
            directory / "root.json",
        )
        for path, payload in (
            (wheel_path, artifact[1]),
            (bundle_path, bundle),
            (key_path, key),
            (root_path, root),
        ):
            path.write_bytes(payload)
            path.chmod(0o400)
        version = json.loads(
            _run_tool([str(executable), "version", "--json"], directory, limits, tool_name="cosign")
        )
        if not isinstance(version, dict) or version.get("gitVersion") != profile.version:
            raise EvaluatorTrustError("Cosign version differs from its admitted operator profile")
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
