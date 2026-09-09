from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import file_digest
from io import BufferedReader
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, cast

from robotics_runtime_contracts import (
    ArtifactReceiptValidationError,
    loads_mapping,
    validate_artifact_receipt,
)
from robotics_runtime_contracts.serialization import read_document_stream

from robotics_acceptance_harness._evidence_files import open_evidence
from robotics_acceptance_harness.documents import (
    LoadedDocument,
    load_document,
    load_document_bytes,
)
from robotics_acceptance_harness.errors import HarnessError


class ReceiptValidationError(HarnessError, ValueError):
    """Raised when an artifact receipt lacks a verified provenance chain."""

    error_id = "ReceiptValidationError.failed"

    def __init__(self, json_path: str, message: str) -> None:
        self.json_path = json_path
        self.validation_message = message
        super().__init__(f"{json_path}: {message}")

    @property
    def diagnostic_issues(self) -> tuple[tuple[str, str], ...]:
        return ((self.json_path, self.validation_message),)


@dataclass(frozen=True, slots=True)
class ReceiptInventory:
    """A receipt input list read when evidence is ready, rather than at startup."""

    path: str | Path


ReceiptSource = Sequence[str | Path] | ReceiptInventory


@dataclass(frozen=True, slots=True)
class VerifiedReceipt:
    receipt: LoadedDocument
    verification: LoadedDocument


@dataclass(frozen=True, slots=True)
class VerifiedReceiptSet:
    by_digest: Mapping[str, VerifiedReceipt]

    def verify_artifact(
        self,
        receipt_sha256: str,
        expected: Mapping[str, Any],
        *,
        run_id: str | None = None,
    ) -> VerifiedReceipt:
        verified = self.by_digest.get(receipt_sha256)
        if verified is None:
            raise ReceiptValidationError("$.receipt_sha256", "verified receipt was not supplied")
        artifact = verified.receipt.data["artifact"]
        observed = {field: artifact.get(field) for field in expected}
        if observed != dict(expected):
            raise ReceiptValidationError(
                "$.artifact",
                f"receipt describes different bytes: expected {dict(expected)!r}",
            )
        if run_id is not None and verified.receipt.data.get("run_id") != run_id:
            raise ReceiptValidationError("$.run_id", "receipt belongs to another run")
        return verified


def _raw_digests(paths: Sequence[str | Path], *, root: Path | None = None) -> Mapping[str, Path]:
    artifacts: dict[str, Path] = {}
    for value in paths:
        path = Path(value).expanduser().absolute() if root else Path(value).expanduser().resolve()
        with open_evidence(path, root) if root else path.open("rb") as stream:
            # Both branches open buffered regular files; BinaryIO omits readinto.
            digest = file_digest(cast(BufferedReader, stream), "sha256").hexdigest()
        if digest in artifacts:
            raise ReceiptValidationError("$.dependencies", "duplicate dependency bytes")
        artifacts[digest] = path
    return MappingProxyType(artifacts)


def _documents(
    paths: Sequence[str | Path],
    role: str,
    *,
    root: Path | None = None,
    extension_schemas: Mapping[str, bytes | str] | None = None,
) -> Mapping[str, LoadedDocument]:
    documents: dict[str, LoadedDocument] = {}
    for path in paths:
        if root is None:
            document = load_document(path, expected_role=role, extension_schemas=extension_schemas)
        else:
            with open_evidence(Path(path), root) as stream:
                document = load_document_bytes(
                    read_document_stream(stream),
                    source=Path(path),
                    expected_role=role,
                    extension_schemas=extension_schemas,
                )
        if document.sha256 in documents:
            raise ReceiptValidationError(f"$.{role}", "duplicate document bytes")
        documents[document.sha256] = document
    return MappingProxyType(documents)


def _inventory_path(value: object, root: Path) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or "\x00" in value:
        raise ReceiptValidationError("$.receipt_inventory", "expected a relative POSIX file path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts or path.as_posix() != value:
        raise ReceiptValidationError(
            "$.receipt_inventory", "expected a canonical relative file path"
        )
    return root / value


def _inventory_paths(path: Path) -> tuple[Path, Mapping[str, tuple[Path, ...]]]:
    root = path.parent.resolve(strict=True)
    with open_evidence(root / path.name, root) as stream:
        data = loads_mapping(read_document_stream(stream), source_name=str(path))
    groups = ("receipts", "verifications", "dependencies")
    if set(data) != set(groups):
        raise ReceiptValidationError(
            "$.receipt_inventory", "expected receipts, verifications and dependencies"
        )
    paths: dict[str, tuple[Path, ...]] = {}
    seen: set[Path] = set()
    for group in groups:
        values = data[group]
        if not isinstance(values, list) or len(values) + len(seen) > 4096:
            raise ReceiptValidationError(
                f"$.receipt_inventory.{group}", "expected a file list; limit is 4096 files"
            )
        selected = tuple(_inventory_path(value, root) for value in values)
        if len(set(selected)) != len(selected) or seen.intersection(selected):
            raise ReceiptValidationError(
                f"$.receipt_inventory.{group}", "duplicate inventory file path"
            )
        seen.update(selected)
        paths[group] = selected
    return root, paths


def _load_inventory(
    inventory: ReceiptInventory,
    *,
    extension_schemas: Mapping[str, bytes | str] | None = None,
) -> VerifiedReceiptSet:
    try:
        root, paths = _inventory_paths(Path(inventory.path).expanduser().absolute())
        return _verify_documents(
            _documents(
                paths["receipts"],
                "artifact_receipt",
                root=root,
                extension_schemas=extension_schemas,
            ),
            _documents(
                paths["verifications"],
                "artifact_verification",
                root=root,
                extension_schemas=extension_schemas,
            ),
            _raw_digests(paths["dependencies"], root=root),
        )
    except ReceiptValidationError:
        raise
    except (OSError, ValueError) as error:
        raise ReceiptValidationError("$.receipt_inventory", str(error)) from error


def load_verified_receipts(
    *,
    receipt_paths: ReceiptSource = (),
    verification_paths: Sequence[str | Path] = (),
    dependency_paths: Sequence[str | Path] = (),
    extension_schemas: Mapping[str, bytes | str] | None = None,
) -> VerifiedReceiptSet:
    """Validate receipt extensions offline and bind externally verified provenance."""

    if isinstance(receipt_paths, ReceiptInventory):
        if verification_paths or dependency_paths:
            raise ReceiptValidationError(
                "$.receipt_inventory", "inventory cannot be combined with explicit receipt inputs"
            )
        return _load_inventory(receipt_paths, extension_schemas=extension_schemas)
    return _verify_documents(
        _documents(receipt_paths, "artifact_receipt", extension_schemas=extension_schemas),
        _documents(
            verification_paths, "artifact_verification", extension_schemas=extension_schemas
        ),
        _raw_digests(dependency_paths),
    )


def _verify_documents(
    receipts: Mapping[str, LoadedDocument],
    verifications: Mapping[str, LoadedDocument],
    dependencies: Mapping[str, Path],
) -> VerifiedReceiptSet:
    used_verifications: set[str] = set()
    used_dependencies: set[str] = set()
    verified: dict[str, VerifiedReceipt] = {}
    for receipt_sha256, receipt in receipts.items():
        verification_sha256 = str(receipt.data["verification_sha256"])
        verification = verifications.get(verification_sha256)
        if verification is None:
            raise ReceiptValidationError(
                "$.verification_sha256",
                "receipt verification document was not supplied",
            )
        used_verifications.add(verification_sha256)
        try:
            required_dependencies = validate_artifact_receipt(
                receipt.data,
                verification.data,
                dependencies,
            )
        except ArtifactReceiptValidationError as error:
            raise ReceiptValidationError("$.verification_sha256", str(error)) from error
        used_dependencies.update(required_dependencies)
        verified[receipt_sha256] = VerifiedReceipt(receipt, verification)

    if used_verifications != set(verifications):
        raise ReceiptValidationError("$.verifications", "unreferenced verification document")
    if used_dependencies != set(dependencies):
        raise ReceiptValidationError("$.dependencies", "unreferenced provenance dependency")
    return VerifiedReceiptSet(MappingProxyType(verified))


__all__ = [
    "ReceiptInventory",
    "ReceiptSource",
    "ReceiptValidationError",
    "VerifiedReceipt",
    "VerifiedReceiptSet",
    "load_verified_receipts",
]
