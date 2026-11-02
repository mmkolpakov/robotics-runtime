"""Private admission of signed OCI manifest/config bytes, without image execution."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from robotics_runtime_contracts import ContractError, loads_mapping

from robotics_acceptance_harness._cosign_key_verifier import verify_blob_snapshot
from robotics_acceptance_harness.evaluator_trust import (
    DEFAULT_TRUST_LIMITS,
    CosignKeyVerifierProfile,
    EvaluatorTrustError,
    TrustLimits,
    _sha256,
    read_once,
)

_MANIFEST_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"
_CONFIG_MEDIA_TYPE = "application/vnd.oci.image.config.v1+json"


def _platform(value: Mapping[str, str]) -> dict[str, str]:
    if (
        not isinstance(value, Mapping)
        or not {"os", "architecture"} <= set(value) <= {"os", "architecture", "variant"}
        or any(not isinstance(item, str) or not item or len(item) > 128 for item in value.values())
    ):
        raise EvaluatorTrustError("OCI platform requires os/architecture and optional variant")
    return dict(value)


def _mapping(raw: bytes, label: str) -> dict[str, Any]:
    try:
        return loads_mapping(raw, source_name=f"{label}.json")
    except ContractError as failure:
        raise EvaluatorTrustError(f"invalid OCI {label}: {failure}") from failure


def _validate_identity(
    manifest: bytes, config: bytes, expected_digest: str, platform: Mapping[str, str]
) -> None:
    if not isinstance(expected_digest, str) or not expected_digest.startswith("sha256:"):
        raise EvaluatorTrustError("OCI subject requires an exact sha256 digest")
    _sha256(expected_digest[7:])
    if "sha256:" + hashlib.sha256(manifest).hexdigest() != expected_digest:
        raise EvaluatorTrustError("OCI manifest differs from its externally expected digest")
    expected_platform = _platform(platform)
    document = _mapping(manifest, "manifest")
    if (
        type(document.get("schemaVersion")) is not int
        or document["schemaVersion"] != 2
        or document.get("mediaType") != _MANIFEST_MEDIA_TYPE
    ):
        raise EvaluatorTrustError("OCI subject must be a platform image manifest, not an index")
    descriptor = document.get("config")
    if (
        not isinstance(descriptor, dict)
        or descriptor.get("mediaType") != _CONFIG_MEDIA_TYPE
        or descriptor.get("digest") != "sha256:" + hashlib.sha256(config).hexdigest()
        or type(descriptor.get("size")) is not int
        or descriptor["size"] != len(config)
    ):
        raise EvaluatorTrustError("OCI manifest config media type, digest or size differs")
    image_config = _mapping(config, "config")
    if any(
        image_config.get(name, "") != expected_platform.get(name, "")
        for name in ("os", "architecture", "variant")
    ):
        raise EvaluatorTrustError("OCI config platform differs from the operator expectation")


def authenticate_manifest(
    paths: tuple[Path, Path, Path],
    *,
    expected_digest: str,
    platform: Mapping[str, str],
    profile: CosignKeyVerifierProfile,
    limits: TrustLimits = DEFAULT_TRUST_LIMITS,
) -> tuple[bytes, bytes, bytes]:
    """Capture manifest/config/bundle paths; return manifest/config/audit, not CID proof."""
    manifest_path, config_path, bundle_path = paths
    manifest = read_once(manifest_path, limits.max_bundle_bytes)
    config = read_once(config_path, limits.max_bundle_bytes)
    bundle = read_once(bundle_path, limits.max_bundle_bytes)
    _validate_identity(manifest, config, expected_digest, platform)
    audit = verify_blob_snapshot(manifest, bundle, profile, limits)
    return manifest, config, audit
