from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from robotics_runtime_contracts import load_mapping, validate_document
from robotics_runtime_contracts.extensions import ExtensionValidationError

from robotics_acceptance_harness.documents import BundleValidationError
from robotics_acceptance_harness.receipts import (
    ReceiptInventory,
    ReceiptValidationError,
    VerifiedReceiptSet,
    load_verified_receipts,
)
from tests.support import write_verified_receipt

NAMESPACE = "org.example.receipt"
SCHEMA_URI = "https://example.org/schemas/receipt-extension.v1.json"
SCHEMA = json.dumps(
    {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_URI,
        "type": "object",
        "properties": {"batch": {"type": "string", "minLength": 1}},
        "required": ["batch"],
        "additionalProperties": False,
    }
).encode("utf-8")


@dataclass(frozen=True)
class ReceiptChain:
    receipt: Path
    verification: Path
    dependencies: tuple[Path, ...]
    inventory: Path

    def load(
        self,
        *,
        inventory: bool,
        extension_schemas: Mapping[str, bytes | str] | None = None,
    ) -> VerifiedReceiptSet:
        if inventory:
            return load_verified_receipts(
                receipt_paths=ReceiptInventory(self.inventory),
                extension_schemas=extension_schemas,
            )
        return load_verified_receipts(
            receipt_paths=[self.receipt],
            verification_paths=[self.verification],
            dependency_paths=self.dependencies,
            extension_schemas=extension_schemas,
        )


def write_document(path: Path, document: Mapping[str, Any]) -> str:
    path.write_bytes(json.dumps(document, sort_keys=True).encode("utf-8") + b"\n")
    return sha256(path.read_bytes()).hexdigest()


def receipt_chain(directory: Path, extended: tuple[str, ...]) -> ReceiptChain:
    chain = write_verified_receipt(
        directory,
        {
            "uri": "s3://fixture-bucket/output.json",
            "sha256": "a" * 64,
            "size_bytes": 2048,
            "media_type": "application/json",
            "immutable_revision": "version-1",
        },
    )
    # Rewrite verification first so the receipt binds its extended original bytes.
    for name in ("verification", "receipt"):
        path = chain[name]
        document = load_mapping(path)
        if name in extended:
            document["extensions"] = {NAMESPACE: {"batch": "batch-1"}}
            document["extension_schemas"] = [
                {
                    "namespace": NAMESPACE,
                    "schema_uri": SCHEMA_URI,
                    "sha256": sha256(SCHEMA).hexdigest(),
                }
            ]
        if name == "receipt":
            document["verification_sha256"] = sha256(chain["verification"].read_bytes()).hexdigest()
        validate_document(document, extension_schemas={SCHEMA_URI: SCHEMA})
        write_document(path, document)
    inventory = directory / "inventory.json"
    write_document(
        inventory,
        {
            "receipts": [chain["receipt"].name],
            "verifications": [chain["verification"].name],
            "dependencies": [path.name for path in chain["dependencies"]],
        },
    )
    return ReceiptChain(chain["receipt"], chain["verification"], chain["dependencies"], inventory)


@pytest.mark.parametrize("inventory", [False, True], ids=["explicit", "inventory"])
@pytest.mark.parametrize("schema", [SCHEMA, SCHEMA.decode("utf-8")], ids=["bytes", "str"])
def test_registered_receipt_extensions_preserve_payloads_and_original_digests(
    tmp_path: Path, inventory: bool, schema: bytes | str
) -> None:
    chain = receipt_chain(tmp_path, ("receipt", "verification"))
    originals = {
        path: path.read_bytes()
        for path in (chain.receipt, chain.verification, chain.inventory, *chain.dependencies)
    }
    verified = chain.load(inventory=inventory, extension_schemas={SCHEMA_URI: schema})
    receipt_sha256 = sha256(originals[chain.receipt]).hexdigest()
    assert set(verified.by_digest) == {receipt_sha256}
    result = verified.by_digest[receipt_sha256]
    assert result.receipt.sha256 == receipt_sha256
    assert result.verification.sha256 == sha256(originals[chain.verification]).hexdigest()
    for document in (result.receipt, result.verification):
        assert document.data["extensions"][NAMESPACE]["batch"] == "batch-1"
    assert all(path.read_bytes() == raw for path, raw in originals.items())


@pytest.mark.parametrize("inventory", [False, True], ids=["explicit", "inventory"])
@pytest.mark.parametrize("role", ["receipt", "verification"])
@pytest.mark.parametrize(
    ("registry", "error_path"),
    [
        (None, "$.extension_schemas"),
        ({}, "$.extension_schemas[0].schema_uri"),
        ({SCHEMA_URI: SCHEMA + b" "}, "$.extension_schemas[0].sha256"),
    ],
    ids=["omitted", "missing", "tampered"],
)
def test_each_receipt_role_requires_its_exact_extension_schema(
    tmp_path: Path,
    inventory: bool,
    role: str,
    registry: Mapping[str, bytes | str] | None,
    error_path: str,
) -> None:
    chain = receipt_chain(tmp_path, (role,))
    with pytest.raises((BundleValidationError, ReceiptValidationError)) as raised:
        chain.load(inventory=inventory, extension_schemas=registry)
    cause: BaseException = raised.value
    while cause.__cause__ is not None:
        cause = cause.__cause__
    assert isinstance(cause, ExtensionValidationError)
    assert cause.error_id == "extension.validation_failed"
    assert cause.schema_name == f"artifact-{role}.v1"
    assert cause.json_path == error_path


@pytest.mark.parametrize("inventory", [False, True], ids=["explicit", "inventory"])
@pytest.mark.parametrize("role", ["receipt", "verification"])
def test_supplied_schema_still_rejects_invalid_extension_payloads(
    tmp_path: Path, inventory: bool, role: str
) -> None:
    chain = receipt_chain(tmp_path, (role,))
    path = chain.receipt if role == "receipt" else chain.verification
    document = load_mapping(path)
    document["extensions"][NAMESPACE]["batch"] = ""
    digest = write_document(path, document)
    if role == "verification":
        receipt = load_mapping(chain.receipt)
        receipt["verification_sha256"] = digest
        write_document(chain.receipt, receipt)
    with pytest.raises((BundleValidationError, ReceiptValidationError)) as raised:
        chain.load(inventory=inventory, extension_schemas={SCHEMA_URI: SCHEMA})
    cause: BaseException = raised.value
    while cause.__cause__ is not None:
        cause = cause.__cause__
    assert isinstance(cause, ExtensionValidationError)
    assert cause.schema_name == f"artifact-{role}.v1"
    assert cause.json_path == f'$.extensions["{NAMESPACE}"].batch'


@pytest.mark.parametrize("inventory", [False, True], ids=["explicit", "inventory"])
def test_registered_extensions_do_not_weaken_provenance_digest_checks(
    tmp_path: Path, inventory: bool
) -> None:
    chain = receipt_chain(tmp_path, ("receipt", "verification"))
    chain.dependencies[0].write_bytes(b"tampered statement")
    with pytest.raises(ReceiptValidationError, match="dependencies are missing:.*statement"):
        chain.load(inventory=inventory, extension_schemas={SCHEMA_URI: SCHEMA})


@pytest.mark.parametrize("inventory", [False, True], ids=["explicit", "inventory"])
def test_receipts_without_extensions_still_load_without_a_registry(
    tmp_path: Path, inventory: bool
) -> None:
    chain = receipt_chain(tmp_path, ())
    if inventory:
        verified = load_verified_receipts(receipt_paths=ReceiptInventory(chain.inventory))
    else:
        verified = load_verified_receipts(
            receipt_paths=[chain.receipt],
            verification_paths=[chain.verification],
            dependency_paths=chain.dependencies,
        )
    assert set(verified.by_digest) == {sha256(chain.receipt.read_bytes()).hexdigest()}
