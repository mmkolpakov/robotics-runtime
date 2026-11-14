from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from os import fstat
from pathlib import Path
from types import MappingProxyType
from typing import Any, BinaryIO
from urllib.parse import SplitResult, quote, unquote, urlsplit
from urllib.request import url2pathname

from robotics_runtime_contracts.serialization import MAX_DOCUMENT_BYTES

from robotics_acceptance_harness._evidence_files import EvidenceReadError, open_evidence
from robotics_acceptance_harness.documents import (
    BundleValidationError,
    LoadedDocument,
    load_document,
    load_document_bytes,
)
from robotics_acceptance_harness.errors import HarnessError
from robotics_acceptance_harness.receipts import (
    ReceiptSource,
    ReceiptValidationError,
    VerifiedReceiptSet,
    load_verified_receipts,
)


class EvidenceValidationError(HarnessError, ValueError):
    """Raised when finalized evidence cannot be independently verified."""

    error_id = "EvidenceValidationError.failed"

    def __init__(self, json_path: str, message: str) -> None:
        self.json_path = json_path
        self.validation_message = message
        super().__init__(f"{json_path}: {message}")

    @property
    def diagnostic_issues(self) -> tuple[tuple[str, str], ...]:
        return ((self.json_path, self.validation_message),)


@dataclass(frozen=True, slots=True)
class VerifiedEvidence:
    index: LoadedDocument
    links: tuple[Mapping[str, Any], ...]
    local_files: Mapping[Path, Mapping[str, Any]]
    recording_summaries: tuple[LoadedDocument, ...] = ()
    receipts: tuple[LoadedDocument, ...] = ()
    evidence_origin_root: Path | None = None

    def read_local(self, path: str | Path, *, max_raw_evidence_bytes: int | None = None) -> bytes:
        """Capture an indexed local artifact from the same read that verifies its bytes."""
        if max_raw_evidence_bytes is not None and (
            isinstance(max_raw_evidence_bytes, bool)
            or not isinstance(max_raw_evidence_bytes, int)
            or max_raw_evidence_bytes <= 0
        ):
            raise EvidenceValidationError(
                "$.artifacts", "raw evidence byte budget must be a positive integer"
            )
        source = (
            Path(path).expanduser().absolute()
            if self.evidence_origin_root is not None
            else Path(path).expanduser().resolve()
        )
        reference = self.local_files.get(source)
        if reference is None:
            raise EvidenceValidationError(
                "$.artifacts", f"source is not verified local evidence: {source}"
            )
        if (
            max_raw_evidence_bytes is not None
            and int(reference["size_bytes"]) > max_raw_evidence_bytes
        ):
            raise EvidenceValidationError(
                "$.artifacts.size_bytes", "source exceeds the raw evidence byte budget"
            )
        return _read_local(
            source,
            reference,
            self.index.path.parent,
            "$.artifacts",
            capture_limit=(
                MAX_DOCUMENT_BYTES if max_raw_evidence_bytes is None else max_raw_evidence_bytes
            ),
        )


def _verified_payload(
    path: Path,
    reference: Mapping[str, Any],
    root: Path,
    *,
    sink: BinaryIO | None = None,
    capture_limit: int | None = None,
) -> bytes:
    expected_size = int(reference["size_bytes"])
    if capture_limit is not None and expected_size > capture_limit:
        raise EvidenceReadError(
            "captured evidence exceeds the contract document byte limit", field="size_bytes"
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
            if capture_limit is not None:
                payload.extend(chunk)
            if sink is not None and sink.write(chunk) != len(chunk):
                raise EvidenceReadError("snapshot sink did not write the complete chunk")
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
    capture_limit: int | None = None,
) -> bytes:
    try:
        return _verified_payload(path, reference, root, capture_limit=capture_limit)
    except FileNotFoundError as error:
        raise EvidenceValidationError(json_path, f"file does not exist: {path}") from error
    except EvidenceReadError as error:
        location = f"{json_path}.{error.field}" if error.field else json_path
        raise EvidenceValidationError(location, str(error)) from error
    except OSError as error:
        raise EvidenceValidationError(json_path, str(error)) from error


def _mapped_uri_path(uri: SplitResult, json_path: str) -> Path:
    if uri.query or uri.fragment or re.search(r"%(?![0-9a-fA-F]{2})|%2[fF]|%00", uri.path):
        raise EvidenceValidationError(json_path, "invalid local evidence URI")
    try:
        decoded = unquote(uri.path, errors="strict")
    except UnicodeDecodeError as error:
        raise EvidenceValidationError(json_path, "invalid local evidence URI encoding") from error
    path = Path(decoded)
    if str(path) != decoded:
        raise EvidenceValidationError(json_path, "expected a canonical local evidence path")
    return path


def _relocated_path(path: Path, root: Path, origin: Path) -> Path:
    if not path.is_absolute() or ".." in path.parts or "\x00" in str(path):
        raise EvidenceValidationError("$.artifacts", "expected an absolute original evidence path")
    try:
        relative = path.relative_to(origin)
    except ValueError as error:
        raise EvidenceValidationError(
            "$.artifacts", "original file is outside the evidence origin root"
        ) from error
    if not relative.parts:
        raise EvidenceValidationError("$.artifacts", "evidence must identify a file below its root")
    return root / relative


def _local_link(
    artifact: Mapping[str, Any],
    index: int,
    root: Path,
    origin: Path | None = None,
) -> tuple[Path, Mapping[str, Any]]:
    # Preserve the legacy /C:/ spelling used by Windows fixtures. Quote
    # literal percent signs before conversion so filenames are not URI-decoded.
    path = Path(url2pathname(quote(str(artifact["local_path"]), safe="/:")))
    json_path = f"$.artifacts[{index}]"
    uri = urlsplit(str(artifact["uri"]))
    if uri.scheme != "file" or uri.netloc not in {"", "localhost"}:
        raise EvidenceValidationError(
            f"{json_path}.uri",
            "local evidence requires a local file URI",
        )
    uri_path = (
        _mapped_uri_path(uri, f"{json_path}.uri")
        if origin is not None
        else Path(url2pathname(uri.path))
    )
    if origin is not None and str(path) != artifact["local_path"]:
        raise EvidenceValidationError(json_path, "expected a canonical local evidence path")
    same_path = uri_path == path if origin is not None else uri_path.resolve() == path.resolve()
    if not same_path:
        raise EvidenceValidationError(
            f"{json_path}.local_path",
            f"does not identify file URI {artifact['uri']}",
        )
    if origin is not None:
        path = _relocated_path(path, root, origin)
    _read_local(path, artifact, root, json_path)
    return (path if origin is not None else path.resolve()), _result_link(artifact)


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
    origin: Path | None = None,
) -> LoadedDocument:
    reference = artifact["recording_summary"]
    json_path = f"$.artifacts[{index}].recording_summary"
    uri = urlsplit(str(reference["uri"]))
    if uri.scheme != "file" or uri.netloc not in {"", "localhost"}:
        raise EvidenceValidationError(
            f"{json_path}.uri",
            "acceptance verification requires a local recording summary",
        )
    path = (
        _relocated_path(_mapped_uri_path(uri, json_path), root, origin)
        if origin is not None
        else Path(url2pathname(uri.path)).absolute()
    )
    raw = _read_local(path, reference, root, json_path, capture_limit=MAX_DOCUMENT_BYTES)
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


def _origin_root(value: str | Path | None) -> Path | None:
    origin = None
    if value is not None:
        normalized = str(value).rstrip("/") or "/"
        origin = Path(normalized)
        if (
            not origin.is_absolute()
            or ".." in origin.parts
            or "\x00" in str(origin)
            or str(origin) != normalized
        ):
            raise EvidenceValidationError(
                "$.artifacts", "evidence origin root must be an absolute path without traversal"
            )
    return origin


def load_evidence_index(
    path: str | Path,
    *,
    expected_run_id: str | None = None,
    receipt_paths: ReceiptSource = (),
    verification_paths: Sequence[str | Path] = (),
    receipt_dependency_paths: Sequence[str | Path] = (),
    evidence_origin_root: str | Path | None = None,
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

    origin = _origin_root(evidence_origin_root)
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
            local_path, link = _local_link(artifact, index, document.path.parent, origin)
            if origin is not None and local_path in local_files:
                raise EvidenceValidationError("$.artifacts", "duplicate relocated evidence path")
            local_files[local_path] = link
            links.append(link)
        else:
            links.append(_remote_link(artifact, index, receipts, run_id))
            used_receipts.add(str(artifact["receipt_sha256"]))
        if artifact["kind"] == "recording":
            summaries.append(_local_summary(artifact, index, document.path.parent, origin))
    if used_receipts != set(receipts.by_digest):
        raise EvidenceValidationError("$.receipts", "unreferenced artifact receipt")
    return VerifiedEvidence(
        document,
        tuple(links),
        MappingProxyType(local_files),
        tuple(summaries),
        tuple(item.receipt for item in receipts.by_digest.values()),
        origin,
    )
