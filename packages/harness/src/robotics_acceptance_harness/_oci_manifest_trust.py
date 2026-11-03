"""Private admission of signed OCI manifest/config bytes, without image execution."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
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

_MANIFEST_CONFIG_TYPES = {
    "application/vnd.oci.image.manifest.v1+json": "application/vnd.oci.image.config.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json": (
        "application/vnd.docker.container.image.v1+json"
    ),
}


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
    media_type = document.get("mediaType")
    if (
        type(document.get("schemaVersion")) is not int
        or document["schemaVersion"] != 2
        or not isinstance(media_type, str)
        or media_type not in _MANIFEST_CONFIG_TYPES
    ):
        raise EvaluatorTrustError("OCI subject must be a platform image manifest, not an index")
    descriptor = document.get("config")
    if (
        not isinstance(descriptor, dict)
        or descriptor.get("mediaType") != _MANIFEST_CONFIG_TYPES[media_type]
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
    binding: Mapping[str, Any],
    *,
    profile: CosignKeyVerifierProfile,
    limits: TrustLimits = DEFAULT_TRUST_LIMITS,
    deadline: float | None = None,
) -> tuple[bytes, bytes, bytes]:
    """Capture manifest/config/bundle paths; return manifest/config/audit, not CID proof."""
    manifest = read_once(binding["manifest"], limits.max_bundle_bytes)
    config = read_once(binding["config"], limits.max_bundle_bytes)
    bundle = read_once(binding["bundle"], limits.max_bundle_bytes)
    _validate_identity(
        manifest, config, "sha256:" + binding["manifest_sha256"], binding["platform"]
    )
    audit = verify_blob_snapshot(manifest, bundle, profile, limits, deadline=deadline)
    return manifest, config, audit
