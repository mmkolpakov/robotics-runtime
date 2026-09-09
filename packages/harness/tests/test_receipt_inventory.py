from __future__ import annotations

import json
from pathlib import Path

import pytest
from robotics_runtime_contracts.serialization import MAX_DOCUMENT_BYTES

from robotics_acceptance_harness.application import VerificationError, _wait_for_evidence
from robotics_acceptance_harness.evidence import EvidenceValidationError, load_evidence_index
from robotics_acceptance_harness.receipts import (
    ReceiptInventory,
    ReceiptValidationError,
    load_verified_receipts,
)
from tests.support import write_evidence_index, write_verified_receipt
from tests.test_evidence_files import _directory_link

RUN_ID = "run-01234567-89ab-4def-8123-456789abcdef"


@pytest.fixture
def retained_inputs(tmp_path: Path) -> tuple[Path, Path]:
    artifact = {
        "artifact_id": "observation",
        "kind": "observation",
        "uri": "s3://fixture-bucket/run.json",
        "media_type": "application/json",
        "sha256": "a" * 64,
        "size_bytes": 2048,
        "retention_class": "regression-30d",
        "storage_state": "retained",
        "immutable_revision": "version-1",
    }
    directory = tmp_path / "retained files"
    directory.mkdir()
    chain = write_verified_receipt(directory, artifact, run_id=RUN_ID)
    index = write_evidence_index(
        tmp_path / "index.json",
        run_id=RUN_ID,
        artifacts=[{**artifact, "receipt_sha256": chain["receipt_sha256"]}],
        upload_mode="closed_segments_during_run",
    )
    inventory = tmp_path / "receipt-inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "receipts": [chain["receipt"].relative_to(tmp_path).as_posix()],
                "verifications": [chain["verification"].relative_to(tmp_path).as_posix()],
                "dependencies": [
                    path.relative_to(tmp_path).as_posix() for path in chain["dependencies"]
                ],
            }
        ),
        encoding="utf-8",
    )
    return index, inventory


def test_inventory_loads_the_same_verified_receipt_links(
    retained_inputs: tuple[Path, Path],
) -> None:
    index, inventory = retained_inputs
    verified = load_evidence_index(
        index, expected_run_id=RUN_ID, receipt_paths=ReceiptInventory(inventory)
    )
    assert verified.links[0]["uri"] == "s3://fixture-bucket/run.json"
    assert verified.links[0]["immutable_revision"] == "version-1"
    assert len(verified.receipts) == 1


def test_inventory_can_be_published_after_measurement_starts(
    retained_inputs: tuple[Path, Path],
) -> None:
    index, inventory = retained_inputs
    pending = inventory.with_suffix(".pending")
    inventory.rename(pending)
    source = ReceiptInventory(inventory)
    elapsed_ns = 0

    def publish(seconds: float) -> None:
        nonlocal elapsed_ns
        elapsed_ns += round(seconds * 1_000_000_000)
        pending.rename(inventory)

    verified = _wait_for_evidence(
        index,
        run_id=RUN_ID,
        receipt_paths=source,
        verification_paths=(),
        receipt_dependency_paths=(),
        timeout_sec=1,
        poll_interval_sec=0.05,
        now_ns=lambda: elapsed_ns,
        sleep_fn=publish,
    )
    assert elapsed_ns == 50_000_000
    assert len(verified.receipts) == 1


def test_missing_inventory_preserves_the_evidence_deadline(
    retained_inputs: tuple[Path, Path],
) -> None:
    index, inventory = retained_inputs
    inventory.unlink()
    with pytest.raises(VerificationError, match="not ready before deadline.*receipt_inventory"):
        _wait_for_evidence(
            index,
            run_id=RUN_ID,
            receipt_paths=ReceiptInventory(inventory),
            verification_paths=(),
            receipt_dependency_paths=(),
            timeout_sec=0,
            poll_interval_sec=0.05,
            now_ns=lambda: 0,
            sleep_fn=lambda _: pytest.fail("zero timeout cannot sleep"),
        )


@pytest.mark.parametrize(
    "name",
    [
        "../outside.json",
        "/outside.json",
        "C:/outside.json",
        "a\\b.json",
        "file:///a",
        "./a",
        "a//b",
        "",
    ],
)
def test_inventory_rejects_paths_outside_its_portable_relative_format(
    retained_inputs: tuple[Path, Path], name: str
) -> None:
    index, inventory = retained_inputs
    data = json.loads(inventory.read_bytes())
    data["receipts"] = [name]
    inventory.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EvidenceValidationError, match="relative.*file path"):
        load_evidence_index(index, receipt_paths=ReceiptInventory(inventory))


def test_inventory_does_not_follow_a_directory_link_outside_its_root(
    retained_inputs: tuple[Path, Path],
) -> None:
    index, inventory = retained_inputs
    directory = inventory.parent / "retained files"
    outside = inventory.parent.parent / f"{inventory.parent.name}-outside"
    directory.rename(outside)
    _directory_link(directory, outside)
    with pytest.raises(EvidenceValidationError, match="receipt_inventory"):
        load_evidence_index(index, receipt_paths=ReceiptInventory(inventory))


@pytest.mark.parametrize("group", ["receipts", "verifications", "dependencies"])
def test_inventory_rejects_duplicate_paths(retained_inputs: tuple[Path, Path], group: str) -> None:
    index, inventory = retained_inputs
    data = json.loads(inventory.read_bytes())
    data[group].append(data[group][0])
    inventory.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EvidenceValidationError, match="duplicate inventory file path"):
        load_evidence_index(index, receipt_paths=ReceiptInventory(inventory))


def test_inventory_still_binds_original_dependency_bytes(
    retained_inputs: tuple[Path, Path],
) -> None:
    index, inventory = retained_inputs
    data = json.loads(inventory.read_bytes())
    dependency = inventory.parent / data["dependencies"][0]
    dependency.write_bytes(b"changed statement bytes")
    with pytest.raises(EvidenceValidationError, match="dependencies are missing.*statement"):
        load_evidence_index(index, receipt_paths=ReceiptInventory(inventory))


def test_inventory_still_rejects_documents_in_another_role(
    retained_inputs: tuple[Path, Path],
) -> None:
    index, inventory = retained_inputs
    data = json.loads(inventory.read_bytes())
    data["receipts"], data["verifications"] = data["verifications"], data["receipts"]
    inventory.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EvidenceValidationError, match="artifact.receipt"):
        load_evidence_index(index, receipt_paths=ReceiptInventory(inventory))


def test_inventory_rejects_unknown_fields(retained_inputs: tuple[Path, Path]) -> None:
    index, inventory = retained_inputs
    data = json.loads(inventory.read_bytes())
    data["glob"] = "**/*"
    inventory.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(
        EvidenceValidationError, match="expected receipts, verifications and dependencies"
    ):
        load_evidence_index(index, receipt_paths=ReceiptInventory(inventory))


def test_inventory_cannot_hide_unused_provenance(retained_inputs: tuple[Path, Path]) -> None:
    index, inventory = retained_inputs
    data = json.loads(inventory.read_bytes())
    (inventory.parent / "unused.bin").write_bytes(b"unreferenced dependency")
    data["dependencies"].append("unused.bin")
    inventory.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EvidenceValidationError, match="unreferenced provenance dependency"):
        load_evidence_index(index, receipt_paths=ReceiptInventory(inventory))


def test_inventory_cannot_be_mixed_with_explicit_inputs(retained_inputs: tuple[Path, Path]) -> None:
    _, inventory = retained_inputs
    with pytest.raises(ReceiptValidationError, match="cannot be combined"):
        load_verified_receipts(
            receipt_paths=ReceiptInventory(inventory), verification_paths=["other.json"]
        )


@pytest.mark.parametrize("values", [True, "receipt.json", [False], ["x"] * 4097])
def test_inventory_bounds_and_types_are_checked_before_loading_files(
    retained_inputs: tuple[Path, Path], values: object
) -> None:
    index, inventory = retained_inputs
    data = json.loads(inventory.read_bytes())
    data["receipts"] = values
    inventory.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EvidenceValidationError, match="receipt_inventory.*expected"):
        load_evidence_index(index, receipt_paths=ReceiptInventory(inventory))


def test_inventory_uses_the_bounded_contract_parser(retained_inputs: tuple[Path, Path]) -> None:
    index, inventory = retained_inputs
    inventory.write_bytes(b" " * (MAX_DOCUMENT_BYTES + 1))
    with pytest.raises(EvidenceValidationError, match="receipt_inventory.*exceeds"):
        load_evidence_index(index, receipt_paths=ReceiptInventory(inventory))
