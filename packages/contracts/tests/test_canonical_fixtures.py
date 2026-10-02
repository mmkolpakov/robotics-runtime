from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from robotics_runtime_contracts import (
    dumps_canonical,
    file_sha256,
    load_mapping,
    validate_document,
)

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]
EXAMPLES = PACKAGE / "consumer-examples/minimal-simulation"
FIXTURE_ROOTS = (
    PACKAGE / "consumer-examples",
    PACKAGE / "tests/fixtures",
    ROOT / "packages/harness/tests/fixtures",
    ROOT / "packages/harness/tests/live/fixtures",
)
FIXTURES = sorted(
    path
    for directory in FIXTURE_ROOTS
    for path in directory.rglob("*")
    if path.suffix in {".json", ".yaml", ".yml"}
)


def fixture_document(path: Path) -> Any:
    if path.suffix == ".json":
        # The three artifacts.json inventories have array roots, not contracts.
        return json.loads(path.read_bytes())
    return load_mapping(path)


def assert_same_json_types(left: Any, right: Any) -> None:
    assert type(left) is type(right)
    if isinstance(left, dict):
        assert left.keys() == right.keys()
        for key in left:
            assert_same_json_types(left[key], right[key])
    elif isinstance(left, list):
        assert len(left) == len(right)
        for first, second in zip(left, right, strict=True):
            assert_same_json_types(first, second)
    else:
        assert left == right


def test_inventory_includes_the_96_existing_examples_and_fixtures() -> None:
    assert len(FIXTURES) >= 96  # Additions are covered automatically.
    assert all(directory.is_dir() for directory in FIXTURE_ROOTS)


@pytest.mark.parametrize("path", FIXTURES, ids=lambda path: str(path.relative_to(ROOT)))
def test_fixture_reserialization_preserves_types_and_original_byte_digests(path: Path) -> None:
    original = path.read_bytes()
    digest = sha256(original).hexdigest()
    document = fixture_document(path)
    before = deepcopy(document)
    serialized = dumps_canonical(document)
    assert_same_json_types(json.loads(serialized), before)
    assert_same_json_types(document, before)
    assert dumps_canonical(json.loads(serialized)) == serialized
    assert file_sha256(path) == digest
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "ns", [2**53 - 1, 2**53, 2**53 + 1, 2**63 - 1, 1785067200123456789, 1785067200123456790]
)
def test_schema_valid_result_copy_retains_large_ns(ns: int) -> None:
    document = load_mapping(EXAMPLES / "acceptance-result.yaml")
    document["observed_ros_graph"]["topics"][0]["first_message_at_ns"] = ns
    validate_document(document)
    decoded = json.loads(dumps_canonical(document))
    assert type(decoded["observed_ros_graph"]["topics"][0]["first_message_at_ns"]) is int
    assert decoded["observed_ros_graph"]["topics"][0]["first_message_at_ns"] == ns
    validate_document(decoded)


def test_schema_valid_dataset_preserves_signed_jump_and_adjacent_ns() -> None:
    document = load_mapping(PACKAGE / "tests/fixtures/dataset/valid/camera-mcap.yaml")
    ns = 1785067200123456789
    document["time"].update(
        start_ns=ns, end_ns=ns + 1, clock_jumps=[{"at_ns": ns, "delta_ns": -(2**63)}]
    )
    validate_document(document)
    decoded = json.loads(dumps_canonical(document))
    assert_same_json_types(decoded, document)
    validate_document(decoded)


def test_existing_run_and_evidence_links_still_hash_the_original_files() -> None:
    run = load_mapping(EXAMPLES / "acceptance-run.yaml")
    evidence = load_mapping(EXAMPLES / "evidence-index.yaml")
    for target, expected in (
        (EXAMPLES / "scenario.yaml", run["scenario_sha256"]),
        (EXAMPLES / "evidence/time-authority.json", evidence["artifacts"][0]["sha256"]),
    ):
        original = target.read_bytes()
        assert file_sha256(target) == expected
        canonical_copy = dumps_canonical(load_mapping(target))
        assert sha256(canonical_copy).hexdigest() != expected
        assert file_sha256(target) == expected
        assert target.read_bytes() == original


@pytest.mark.parametrize("prefix", ["evidence", "evaluator"])
def test_receipt_statement_and_verification_links_keep_original_hashes(prefix: str) -> None:
    directory = PACKAGE / "tests/fixtures/qualification/inference"
    receipt_path = directory / f"{prefix}-receipt.json"
    receipt_bytes = receipt_path.read_bytes()
    receipt = load_mapping(receipt_path)
    for suffix in ("statement", "verification"):
        target = directory / f"{prefix}-{suffix}.json"
        original = target.read_bytes()
        expected = receipt[f"{suffix}_sha256"]
        assert file_sha256(target) == expected
        dumps_canonical(load_mapping(target))
        assert file_sha256(target) == expected
        assert target.read_bytes() == original
    dumps_canonical(receipt)
    assert receipt_path.read_bytes() == receipt_bytes


def test_new_file_digest_is_of_the_exact_written_bytes(tmp_path: Path) -> None:
    path = tmp_path / "new.json"
    encoded = dumps_canonical({"ns": 1785067200123456789})
    path.write_bytes(encoded)
    assert file_sha256(path) == sha256(encoded).hexdigest()
    path.write_bytes(encoded + b"\n")
    assert file_sha256(path) != sha256(encoded).hexdigest()
