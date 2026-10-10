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
from robotics_runtime_contracts.serialization import MAX_DOCUMENT_BYTES, read_document_bytes


def _identity_problem(kind: str, subject_name: str) -> str | None:
    if kind not in _CONTRACT_SCHEMAS and kind not in _RAW_ARTIFACT_KINDS:
        return f"unsupported qualification artifact kind: {kind}"
    segments = subject_name.split("/")
    if (
        not _SUBJECT_NAME.fullmatch(subject_name)
        or not segments[0]
        or any(segment in {"", ".", ".."} for segment in segments)
    ):
        return f"non-canonical qualification subject name: {subject_name}"
    return None


def _specification(specification: str) -> tuple[str, str, Path]:
    kind, kind_separator, remainder = specification.partition(":")
    name, path_separator, path_value = remainder.partition("=")
    if not kind_separator or not path_separator or not kind or not name or not path_value:
        raise CLIArgumentError("--artifact must use KIND:SUBJECT=PATH")
    if (problem := _identity_problem(kind, name)) is not None:
        raise CLIArgumentError(problem)
    return kind, name, Path(path_value).expanduser()


def validate_descriptor(
    artifact: QualificationArtifact,
    extension_schemas: Mapping[str, bytes] | None,
) -> None:
    if (problem := _identity_problem(artifact.kind, artifact.subject_name)) is not None:
        # Descriptors come from API callers, not command-line arguments.
        raise QualificationError(problem)
    if not re.fullmatch(r"[0-9a-f]{64}", artifact.sha256):
        raise QualificationError("artifact sha256 must be 64 lowercase hexadecimal characters")
    if type(artifact.size_bytes) is not int or artifact.size_bytes < 0:
        raise QualificationError("artifact size_bytes must be a nonnegative integer")
    if artifact.kind in _RAW_ARTIFACT_KINDS:
        if artifact.document is not None:
            raise QualificationError(f"raw artifact {artifact.kind} must not carry a document")
        _validate_metadata_capture(artifact)
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


def _validate_metadata_capture(artifact: QualificationArtifact) -> None:
    if artifact.native_metadata_bytes is not None:
        raw = artifact.native_metadata_bytes
        if artifact.kind != "other_evidence" or not isinstance(raw, bytes):
            raise QualificationError(
                "native control metadata requires bounded raw other_evidence bytes"
            )
        if len(raw) > MAX_DOCUMENT_BYTES or (len(raw), hashlib.sha256(raw).hexdigest()) != (
            artifact.size_bytes,
            artifact.sha256,
        ):
            raise QualificationError("native metadata bytes do not match the supplied identity")


def _raw_identity(path: Path) -> tuple[str, int]:
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _capture_native_metadata(
    path: Path,
    kind: str,
    references: Mapping[str, int] | None,
) -> tuple[str, int, bytes | None] | None:
    if kind != "other_evidence" or not references:
        return None
    sizes = set(references.values())
    advertised_size = path.stat().st_size
    if advertised_size not in sizes:
        return None
    if advertised_size > MAX_DOCUMENT_BYTES:
        raise QualificationError("referenced control metadata exceeds the document byte limit")
    # A candidate is read once within the existing control-document bound.
    # Retain immutable bytes only for a referenced metadata identity.
    raw = read_document_bytes(path)
    digest, size = hashlib.sha256(raw).hexdigest(), len(raw)
    metadata = None
    if references.get(digest) == size:
        metadata = raw
    return digest, size, metadata


def load_artifact(
    specification: str,
    extension_schemas: Mapping[str, bytes] | None = None,
    *,
    native_metadata_references: Mapping[str, int] | None = None,
) -> QualificationArtifact:
    kind, name, path = _specification(specification)
    try:
        if kind in _RAW_ARTIFACT_KINDS:
            captured = _capture_native_metadata(path, kind, native_metadata_references)
            if captured is not None:
                digest, size, metadata = captured
                return QualificationArtifact(kind, name, digest, size, None, metadata)
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
