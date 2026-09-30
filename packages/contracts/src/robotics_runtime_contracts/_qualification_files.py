"""Bounded document loading and streamed raw-artifact identity capture."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from pathlib import Path

from robotics_runtime_contracts import loads_mapping, validate_document
from robotics_runtime_contracts._qualification import (
    _CONTRACT_SCHEMAS,
    _RAW_ARTIFACT_KINDS,
    _SUBJECT_NAME,
)
from robotics_runtime_contracts._qualification_types import (
    QualificationArtifact,
    QualificationError,
)
from robotics_runtime_contracts.errors import CLIArgumentError, ContractError
from robotics_runtime_contracts.serialization import read_document_bytes


def _identity(kind: str, subject_name: str) -> None:
    if kind not in _CONTRACT_SCHEMAS and kind not in _RAW_ARTIFACT_KINDS:
        raise CLIArgumentError(f"unsupported qualification artifact kind: {kind}")
    if not _SUBJECT_NAME.fullmatch(subject_name) or ".." in subject_name or "//" in subject_name:
        raise CLIArgumentError(f"non-canonical qualification subject name: {subject_name}")


def _specification(specification: str) -> tuple[str, str, Path]:
    kind, kind_separator, remainder = specification.partition(":")
    name, path_separator, path_value = remainder.partition("=")
    if not kind_separator or not path_separator or not kind or not name or not path_value:
        raise CLIArgumentError("--artifact must use KIND:SUBJECT=PATH")
    _identity(kind, name)
    return kind, name, Path(path_value).expanduser()


def validate_descriptor(
    artifact: QualificationArtifact,
    extension_schemas: Mapping[str, bytes] | None,
) -> None:
    _identity(artifact.kind, artifact.subject_name)
    if not re.fullmatch(r"[0-9a-f]{64}", artifact.sha256):
        raise QualificationError("artifact sha256 must be 64 lowercase hexadecimal characters")
    if type(artifact.size_bytes) is not int or artifact.size_bytes < 0:
        raise QualificationError("artifact size_bytes must be a nonnegative integer")
    if artifact.kind in _RAW_ARTIFACT_KINDS:
        if artifact.document is not None:
            raise QualificationError(f"raw artifact {artifact.kind} must not carry a document")
        return
    document = artifact.document
    if document is None:
        raise QualificationError(f"{artifact.kind} requires a contract document")
    schema = document.get("schema_version")
    allowed = _CONTRACT_SCHEMAS[artifact.kind]
    if not isinstance(schema, str) or schema not in allowed:
        raise QualificationError(
            f"{artifact.subject_name}: unsupported {artifact.kind} schema_version {schema!r}; "
            f"expected one of {sorted(allowed)}"
        )
    validate_document(
        document,
        schema=schema,
        extension_schemas=extension_schemas,
    )


def _raw_identity(path: Path) -> tuple[str, int]:
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def load_artifact(
    specification: str,
    extension_schemas: Mapping[str, bytes] | None = None,
) -> QualificationArtifact:
    kind, name, path = _specification(specification)
    try:
        if kind in _RAW_ARTIFACT_KINDS:
            digest, size = _raw_identity(path)
            return QualificationArtifact(kind, name, digest, size, None)
        raw = read_document_bytes(path)
        document = loads_mapping(raw, source_name=str(path))
        artifact = QualificationArtifact(
            kind, name, hashlib.sha256(raw).hexdigest(), len(raw), document
        )
        validate_descriptor(artifact, extension_schemas)
        return artifact
    except ContractError as error:
        raise QualificationError(
            f"{path}: {error}",
            error_id=error.error_id,
            json_path=error.json_path,
        ) from error
    except OSError as error:
        raise QualificationError(str(error), error_id="input.io_error") from error
