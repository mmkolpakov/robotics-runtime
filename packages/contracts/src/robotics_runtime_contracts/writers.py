"""Validated document producers using the project's deterministic JSON profile."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.parse import urlsplit
from urllib.request import url2pathname

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import best_match

from robotics_runtime_contracts import (
    ContractValidationError,
    dumps_canonical,
    ensure_finite_numbers,
    load_schema,
    loads_mapping,
    schema_registry,
    validate_document,
    validate_role,
)
from robotics_runtime_contracts.errors import ContractError
from robotics_runtime_contracts.extensions import validate_extensions
from robotics_runtime_contracts.receipts import validate_artifact_receipt
from robotics_runtime_contracts.semantics import validate_semantics
from robotics_runtime_contracts.serialization import read_document_bytes

_DRAFT = "evidence-index-draft.v1"


class WriterError(ContractError):
    """Raised when a producer cannot bind the supplied facts to an artifact."""

    error_id = "writer.invalid_input"


def write_document(
    document: Mapping[str, Any],
    output: str | Path,
    *,
    schema: str | None = None,
    extension_schemas: Mapping[str, bytes | str] | None = None,
) -> Path:
    """Validate and atomically replace a document; leave existing output on failure."""
    validate_document(document, schema, extension_schemas=extension_schemas)
    return _write_bytes(dumps_canonical(dict(document)), output)


def _write_bytes(content: bytes, output: str | Path) -> Path:
    destination = Path(output).expanduser().absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def protect_inputs(output: str | Path, inputs: Sequence[str | Path]) -> None:
    """Reject an output alias of a file whose original bytes must be retained."""
    destination = Path(output).expanduser().resolve()
    for source in inputs:
        path = Path(source).expanduser().resolve()
        if path == destination or (destination.exists() and path.samefile(destination)):
            raise WriterError(f"output must not replace input: {path}")


def create_runtime_manifest(
    template: Mapping[str, Any],
    *,
    extension_schemas: Mapping[str, bytes | str] | None = None,
) -> dict[str, Any]:
    """Build from explicitly supplied runtime facts; infer no observed fields."""
    document = deepcopy(dict(template))
    document.setdefault("schema_version", "runtime-manifest.v1")
    validate_role(document, "runtime_manifest", extension_schemas=extension_schemas)
    return document


def _validate_draft(
    draft: Mapping[str, Any],
    extension_schemas: Mapping[str, bytes | str] | None,
) -> dict[str, Any]:
    if set(draft) != {"writer_state", "index"} or draft.get("writer_state") != _DRAFT:
        raise WriterError("expected an evidence-index writer draft")
    index = draft["index"]
    if not isinstance(index, dict):
        raise WriterError("draft index must be an object")
    ensure_finite_numbers(index)
    # Only writer state/cardinality differ from the published finalized contract.
    schema = load_schema("evidence-index.v1")
    schema["properties"]["finalized"] = {"const": False}
    schema["properties"]["artifacts"]["minItems"] = 0
    validator = Draft202012Validator(
        schema, registry=schema_registry(), format_checker=FormatChecker()
    )
    error = best_match(validator.iter_errors(index))
    if error is not None:
        raise ContractValidationError(_DRAFT, error)
    validate_semantics("evidence-index.v1", index)
    validate_extensions("evidence-index.v1", index, extension_schemas)
    return deepcopy(index)


def create_evidence_index(
    template: Mapping[str, Any],
    *,
    extension_schemas: Mapping[str, bytes | str] | None = None,
) -> dict[str, Any]:
    """Start a writer draft from explicit run, timestamp and policy observations."""
    index = deepcopy(dict(template))
    if "artifacts" in index or "finalized" in index:
        raise WriterError("init template must omit artifacts and finalized")
    index.setdefault("schema_version", "evidence-index.v1")
    index.update(finalized=False, artifacts=[])
    draft = {"writer_state": _DRAFT, "index": index}
    _validate_draft(draft, extension_schemas)
    return draft


def write_evidence_draft(
    draft: Mapping[str, Any],
    output: str | Path,
    *,
    extension_schemas: Mapping[str, bytes | str] | None = None,
) -> Path:
    index = _validate_draft(draft, extension_schemas)
    protect_inputs(output, evidence_sources(index))
    return _write_bytes(dumps_canonical({"writer_state": _DRAFT, "index": index}), output)


def _file_facts(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _bind(artifact: dict[str, Any], field: str, value: Any) -> None:
    if field in artifact and dumps_canonical(artifact[field]) != dumps_canonical(value):
        raise WriterError(
            f"supplied {field} does not match the source file", json_path=f"$.{field}"
        )
    artifact[field] = value


def _summary_reference(path: Path, source_digest: str) -> dict[str, Any]:
    raw = read_document_bytes(path)
    summary = loads_mapping(raw, source_name=str(path))
    validate_role(summary, "recording_summary")
    if summary["source_sha256"] != source_digest:
        raise WriterError("recording summary is bound to different file bytes")
    return {"uri": path.as_uri(), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def add_evidence_artifact(
    draft: Mapping[str, Any],
    source: str | Path,
    metadata: Mapping[str, Any],
    *,
    recording_summary: str | Path | None = None,
    extension_schemas: Mapping[str, bytes | str] | None = None,
) -> dict[str, Any]:
    """Bind caller-supplied artifact metadata to the bytes of a local source file."""
    index = _validate_draft(draft, extension_schemas)
    path = Path(source).expanduser().resolve()
    digest, size = _file_facts(path)
    artifact = deepcopy(dict(metadata))
    for field, value in (("sha256", digest), ("size_bytes", size), ("local_path", str(path))):
        _bind(artifact, field, value)
    if artifact.get("storage_state") == "local":
        _bind(artifact, "uri", path.as_uri())
    if recording_summary is not None:
        reference = _summary_reference(Path(recording_summary).expanduser().resolve(), digest)
        _bind(artifact, "recording_summary", reference)
    elif "recording_summary" in artifact:
        raise WriterError("supply the recording summary file, not an unchecked reference")
    index["artifacts"].append(artifact)
    updated = {"writer_state": _DRAFT, "index": index}
    _validate_draft(updated, extension_schemas)
    return updated


def _summary_path(reference: Mapping[str, Any]) -> Path:
    parts = urlsplit(reference["uri"])
    if parts.scheme != "file" or parts.query or parts.fragment:
        raise WriterError("writer draft recording summaries must use local file URIs")
    return Path(url2pathname(f"//{parts.netloc}{parts.path}" if parts.netloc else parts.path))


def evidence_sources(index: Mapping[str, Any]) -> list[Path]:
    sources: list[Path] = []
    for artifact in index["artifacts"]:
        if "local_path" not in artifact:
            raise WriterError("writer finalization requires every original local source")
        sources.append(Path(artifact["local_path"]))
        if "recording_summary" in artifact:
            sources.append(_summary_path(artifact["recording_summary"]))
    return sources


def finalize_evidence_index(
    draft: Mapping[str, Any],
    *,
    extension_schemas: Mapping[str, bytes | str] | None = None,
) -> dict[str, Any]:
    """Recheck retained source bytes and publish a nonempty, finalized contract."""
    index = _validate_draft(draft, extension_schemas)
    evidence_sources(index)
    for artifact in index["artifacts"]:
        path = Path(artifact["local_path"]).expanduser().resolve()
        digest, size = _file_facts(path)
        _bind(artifact, "local_path", str(path))
        _bind(artifact, "sha256", digest)
        _bind(artifact, "size_bytes", size)
        if artifact["storage_state"] == "local":
            _bind(artifact, "uri", path.as_uri())
        if "recording_summary" in artifact:
            reference = _summary_reference(_summary_path(artifact["recording_summary"]), digest)
            _bind(artifact, "recording_summary", reference)
    index["finalized"] = True
    validate_role(index, "evidence_index", extension_schemas=extension_schemas)
    return index


def create_artifact_receipt(
    template: Mapping[str, Any],
    source: str | Path,
    verification: str | Path,
    dependencies: Sequence[str | Path],
) -> dict[str, Any]:
    """Bind a receipt to source bytes and an externally produced verification.

    This producer checks consistency; signature verification belongs to the
    external verifier that supplies the verification document and its evidence.
    """
    verification_path = Path(verification).expanduser().resolve()
    raw = read_document_bytes(verification_path)
    verified = loads_mapping(raw, source_name=str(verification_path))
    validate_role(verified, "artifact_verification")
    document = deepcopy(dict(template))
    document.setdefault("schema_version", "artifact-receipt.v1")
    for field, value in (
        ("artifact", verified["artifact"]),
        (
            "producer",
            {
                "identity": verified["producer_identity"],
                "implementation": verified["producer_implementation"],
            },
        ),
        ("statement_sha256", verified["statement_sha256"]),
        ("verification_sha256", hashlib.sha256(raw).hexdigest()),
    ):
        _bind(document, field, deepcopy(value))
    digest, size = _file_facts(Path(source).expanduser().resolve())
    _bind(document["artifact"], "sha256", digest)
    _bind(document["artifact"], "size_bytes", size)
    validate_role(document, "artifact_receipt")
    dependency_digests = [
        _file_facts(Path(path).expanduser().resolve())[0] for path in dependencies
    ]
    if len(set(dependency_digests)) != len(dependency_digests):
        raise WriterError("duplicate provenance dependency bytes")
    used = validate_artifact_receipt(document, verified, dependency_digests)
    if used != set(dependency_digests):
        raise WriterError("unreferenced provenance dependency")
    return document


__all__ = [
    "WriterError",
    "add_evidence_artifact",
    "create_artifact_receipt",
    "create_evidence_index",
    "create_runtime_manifest",
    "finalize_evidence_index",
    "write_document",
    "write_evidence_draft",
]
