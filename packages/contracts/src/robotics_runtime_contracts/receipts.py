from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from robotics_runtime_contracts._timestamps import parse_timestamp
from robotics_runtime_contracts.errors import ContractError


class ArtifactReceiptValidationError(ContractError):
    """Raised when an artifact receipt contradicts its external verification."""

    error_id = "receipt.validation_failed"


def validate_artifact_receipt(
    receipt: Mapping[str, Any],
    verification: Mapping[str, Any],
    dependency_digests: Collection[str],
) -> frozenset[str]:
    """Validate one typed receipt chain and return the dependency digests it uses."""

    comparisons = (
        ("statement", receipt["statement_sha256"], verification["statement_sha256"]),
        ("artifact descriptor", receipt["artifact"], verification["artifact"]),
        ("producer", receipt["producer"]["identity"], verification["producer_identity"]),
        (
            "producer implementation",
            receipt["producer"]["implementation"],
            verification["producer_implementation"],
        ),
    )
    for label, expected, observed in comparisons:
        if observed != expected:
            raise ArtifactReceiptValidationError(f"{label} does not match the receipt")
    if parse_timestamp(verification["verified_at"], json_path="$.verified_at") > parse_timestamp(
        receipt["created_at"], json_path="$.created_at"
    ):
        raise ArtifactReceiptValidationError("receipt was created before its verification")

    dependencies = {
        str(receipt["statement_sha256"]): "statement",
        str(verification["trust_policy_sha256"]): "trust policy",
        str(verification["verification_evidence_sha256"]): "verification evidence",
    }
    content_manifest = verification.get("content_manifest_sha256")
    if content_manifest is not None:
        dependencies[str(content_manifest)] = "content manifest"
    required = set(dependencies)
    missing = required - set(dependency_digests)
    if missing:
        details = [f"{dependencies[digest]} {digest}" for digest in sorted(missing)]
        raise ArtifactReceiptValidationError(
            f"receipt provenance dependencies are missing: {details}"
        )
    return frozenset(required)


__all__ = ["ArtifactReceiptValidationError", "validate_artifact_receipt"]
