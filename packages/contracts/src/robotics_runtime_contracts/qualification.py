"""Public qualification inspection, typed diagnostics, and file-bound validation.

Inspection accumulates independent failures. A failed prerequisite blocks dependent
checks, and each domain or binding check stops at its first failure. Only file-based
entry points verify digests against bytes; supplied descriptors do not attest to files.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any

from robotics_runtime_contracts._qualification import _ARTIFACT_ROLES, _RAW_ARTIFACT_KINDS
from robotics_runtime_contracts._qualification_checks import inspect_links
from robotics_runtime_contracts._qualification_files import load_artifact, validate_descriptor
from robotics_runtime_contracts._qualification_types import (
    QualificationArtifact,
    QualificationDiagnostic,
    QualificationError,
    QualificationReport,
)
from robotics_runtime_contracts.errors import ContractError

ARTIFACT_ROLES: Mapping[str, str] = MappingProxyType(_ARTIFACT_ROLES)
RAW_ARTIFACT_KINDS = _RAW_ARTIFACT_KINDS


def load_qualification_artifact(
    specification: str,
    extension_schemas: Mapping[str, bytes] | None = None,
) -> QualificationArtifact:
    """Load and validate one KIND:SUBJECT=PATH, hashing the exact bytes read once."""
    return load_artifact(specification, extension_schemas)


def inspect_qualification_documents(
    artifacts: Sequence[QualificationArtifact],
    extension_schemas: Mapping[str, bytes] | None = None,
) -> QualificationReport:
    """Validate supplied descriptors and links, without claiming to have read files."""
    diagnostics: list[QualificationDiagnostic] = []
    for artifact in artifacts:
        try:
            validate_descriptor(artifact, extension_schemas)
        except ContractError as error:
            diagnostics.append(
                QualificationDiagnostic(
                    error.error_id,
                    str(error),
                    "document",
                    artifact.subject_name,
                    error.json_path,
                )
            )
    if diagnostics:
        return QualificationReport(tuple(artifacts), tuple(diagnostics), blocked_checks=("links",))
    return inspect_links(artifacts)


def validate_qualification_documents(
    artifacts: Sequence[QualificationArtifact],
    extension_schemas: Mapping[str, bytes] | None = None,
) -> tuple[str, str]:
    """Raise on invalid supplied descriptors or links; return run ID and aggregate time."""
    report = inspect_qualification_documents(artifacts, extension_schemas)
    report.raise_for_errors()
    if report.run_id is None or report.generated_at is None:
        raise QualificationError("qualification has no validated run identity")
    return report.run_id, report.generated_at


def inspect_qualification_artifacts(
    specifications: Sequence[str],
    extension_schemas: Mapping[str, bytes] | None = None,
) -> QualificationReport:
    """Read every supplied file once, then inspect links if all files are valid."""
    artifacts: list[QualificationArtifact] = []
    diagnostics: list[QualificationDiagnostic] = []
    for specification in specifications:
        try:
            artifacts.append(load_artifact(specification, extension_schemas))
        except ContractError as error:
            # A malformed specification has no trustworthy subject name.
            diagnostics.append(
                QualificationDiagnostic(
                    error.error_id,
                    str(error),
                    "artifact.load",
                    json_path=error.json_path,
                )
            )
    if diagnostics:
        return QualificationReport(tuple(artifacts), tuple(diagnostics), blocked_checks=("links",))
    return inspect_links(artifacts)


def validate_qualification_artifacts(
    specifications: Sequence[str],
    extension_schemas: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    """Validate a complete artifact set and return metadata for the exact bytes read."""
    return inspect_qualification_artifacts(specifications, extension_schemas).metadata()


__all__ = [
    "ARTIFACT_ROLES",
    "RAW_ARTIFACT_KINDS",
    "QualificationArtifact",
    "QualificationDiagnostic",
    "QualificationError",
    "QualificationReport",
    "inspect_qualification_artifacts",
    "inspect_qualification_documents",
    "load_qualification_artifact",
    "validate_qualification_artifacts",
    "validate_qualification_documents",
]
