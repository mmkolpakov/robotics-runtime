from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from os import fstat
from os import name as os_name
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import unquote, urlsplit

from robotics_runtime_contracts.serialization import MAX_DOCUMENT_BYTES

from robotics_acceptance_harness._evidence_files import EvidenceReadError, open_evidence
from robotics_acceptance_harness.documents import (
    BundleValidationError,
    LoadedDocument,
    load_document,
    load_document_bytes,
)
from robotics_acceptance_harness.receipts import (
    ReceiptValidationError,
    VerifiedReceiptSet,
    load_verified_receipts,
)


class EvidenceValidationError(ValueError):
    """Raised when finalized evidence cannot be independently verified."""

    def __init__(self, json_path: str, message: str) -> None:
        self.json_path = json_path
        self.validation_message = message
        super().__init__(f"{json_path}: {message}")


@dataclass(frozen=True, slots=True)
class VerifiedEvidence:
    index: LoadedDocument
    links: tuple[Mapping[str, Any], ...]
    local_files: Mapping[Path, Mapping[str, Any]]
    recording_summaries: tuple[LoadedDocument, ...] = ()
    receipts: tuple[LoadedDocument, ...] = ()


def _local_path(value: str) -> Path:
    decoded = unquote(value)
    if os_name == "nt" and decoded.startswith("/") and decoded[2:3] == ":":
        decoded = decoded[1:]
    return Path(decoded)


def _verified_payload(
    path: Path,
    reference: Mapping[str, Any],
    root: Path,
    *,
    capture: bool = False,
) -> bytes:
    expected_size = int(reference["size_bytes"])
    if capture and expected_size > MAX_DOCUMENT_BYTES:
        raise EvidenceReadError(
            "summary exceeds the contract document byte limit", field="size_bytes"
        )
    payload = bytearray()
    digest, size = sha256(), 0
    with open_evidence(path, root) as stream:
        before = fstat(stream.fileno())
        if before.st_size != expected_size:
            raise EvidenceReadError(
                f"expected {expected_size}; observed {before.st_size}",
                field="size_bytes",
            )
        while chunk := stream.read(min(1024 * 1024, expected_size - size + 1)):
            size += len(chunk)
            if size > expected_size:
                raise EvidenceReadError("evidence grew while being read", field="size_bytes")
            digest.update(chunk)
            if capture:
                payload.extend(chunk)
        after = fstat(stream.fileno())
    if size != expected_size or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise EvidenceReadError("evidence changed while being read")
    if digest.hexdigest() != reference["sha256"]:
        raise EvidenceReadError(
            f"expected {reference['sha256']}; observed {digest.hexdigest()}",
            field="sha256",
        )
    return bytes(payload)


def _read_local(
    path: Path,
    reference: Mapping[str, Any],
    root: Path,
    json_path: str,
    *,
    capture: bool = False,
) -> bytes:
    try:
        return _verified_payload(path, reference, root, capture=capture)
    except FileNotFoundError as error:
        raise EvidenceValidationError(json_path, f"file does not exist: {path}") from error
    except EvidenceReadError as error:
        location = f"{json_path}.{error.field}" if error.field else json_path
        raise EvidenceValidationError(location, str(error)) from error
    except OSError as error:
        raise EvidenceValidationError(json_path, str(error)) from error


def _local_link(
    artifact: Mapping[str, Any],
    index: int,
    root: Path,
) -> tuple[Path, Mapping[str, Any]]:
    path = _local_path(str(artifact["local_path"]))
    json_path = f"$.artifacts[{index}]"
    uri = urlsplit(str(artifact["uri"]))
    if uri.scheme != "file" or uri.netloc not in {"", "localhost"}:
        raise EvidenceValidationError(
            f"{json_path}.uri",
            "local evidence requires a local file URI",
        )
    uri_path = _local_path(uri.path)
    if uri_path.resolve() != path.resolve():
        raise EvidenceValidationError(
            f"{json_path}.local_path",
            f"does not identify file URI {artifact['uri']}",
        )
    _read_local(path, artifact, root, json_path)
    return path.resolve(), _result_link(artifact)


def _remote_link(
    artifact: Mapping[str, Any],
    index: int,
    receipts: VerifiedReceiptSet,
    run_id: str,
) -> Mapping[str, Any]:
    json_path = f"$.artifacts[{index}]"
    expected = {
        field: artifact[field]
        for field in ("uri", "sha256", "size_bytes", "media_type", "immutable_revision")
    }
    try:
        receipts.verify_artifact(
            str(artifact["receipt_sha256"]),
            expected,
            run_id=run_id,
        )
    except ValueError as error:
        raise EvidenceValidationError(json_path, str(error)) from error
    return _result_link(artifact)


def _result_link(artifact: Mapping[str, Any]) -> Mapping[str, Any]:
    fields = (
        "artifact_id",
        "kind",
        "uri",
        "immutable_revision",
        "receipt_sha256",
        "media_type",
        "sha256",
        "size_bytes",
        "retention_class",
        "segment_index",
    )
    return MappingProxyType({field: artifact[field] for field in fields if field in artifact})


def _local_summary(
    artifact: Mapping[str, Any],
    index: int,
    root: Path,
) -> LoadedDocument:
    reference = artifact["recording_summary"]
    json_path = f"$.artifacts[{index}].recording_summary"
    uri = urlsplit(str(reference["uri"]))
    if uri.scheme != "file" or uri.netloc not in {"", "localhost"}:
        raise EvidenceValidationError(
            f"{json_path}.uri",
            "acceptance verification requires a local recording summary",
        )
    path = _local_path(uri.path).absolute()
    raw = _read_local(path, reference, root, json_path, capture=True)
    try:
        summary = load_document_bytes(raw, source=path, expected_role="recording_summary")
    except BundleValidationError as error:
        raise EvidenceValidationError(error.json_path, error.validation_message) from error
    if summary.data["source_sha256"] != artifact["sha256"]:
        raise EvidenceValidationError(
            f"{json_path}.source_sha256",
            "summary does not identify its recording artifact",
        )
    return summary


def load_evidence_index(
    path: str | Path,
    *,
    expected_run_id: str | None = None,
    receipt_paths: Sequence[str | Path] = (),
    verification_paths: Sequence[str | Path] = (),
    receipt_dependency_paths: Sequence[str | Path] = (),
) -> VerifiedEvidence:
    """Validate a finalized index and verify every reusable evidence link."""

    try:
        document = load_document(
            path,
            expected_role="evidence_index",
        )
    except BundleValidationError as error:
        raise EvidenceValidationError(error.json_path, error.validation_message) from error
    if expected_run_id is not None and document.data["run_id"] != expected_run_id:
        raise EvidenceValidationError(
            "$.run_id",
            f"expected {expected_run_id!r}; received {document.data['run_id']!r}",
        )

    links: list[Mapping[str, Any]] = []
    local_files: dict[Path, Mapping[str, Any]] = {}
    summaries: list[LoadedDocument] = []
    try:
        receipts = load_verified_receipts(
            receipt_paths=receipt_paths,
            verification_paths=verification_paths,
            dependency_paths=receipt_dependency_paths,
        )
    except ReceiptValidationError as error:
        raise EvidenceValidationError(error.json_path, error.validation_message) from error
    used_receipts: set[str] = set()
    run_id = str(document.data["run_id"])
    for index, artifact in enumerate(document.data["artifacts"]):
        if artifact["storage_state"] == "local":
            local_path, link = _local_link(artifact, index, document.path.parent)
            local_files[local_path] = link
            links.append(link)
        else:
            links.append(_remote_link(artifact, index, receipts, run_id))
            used_receipts.add(str(artifact["receipt_sha256"]))
        if artifact["kind"] == "recording":
            summaries.append(_local_summary(artifact, index, document.path.parent))
    if used_receipts != set(receipts.by_digest):
        raise EvidenceValidationError("$.receipts", "unreferenced artifact receipt")
    return VerifiedEvidence(
        document,
        tuple(links),
        MappingProxyType(local_files),
        tuple(summaries),
        tuple(item.receipt for item in receipts.by_digest.values()),
    )
