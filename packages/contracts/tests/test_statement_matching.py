from __future__ import annotations

import json
from pathlib import Path

import pytest

from robotics_runtime_contracts import ContractError, load_mapping, validate_document
from robotics_runtime_contracts.cli import main
from robotics_runtime_contracts.qualification import validate_qualification_artifacts
from robotics_runtime_contracts.statements import (
    create_qualification_statement,
    validate_qualification_statement,
    write_qualification_statement,
)
from tests.support import qualification_specifications


@pytest.mark.parametrize("case", ["transport", "inference", "physical"])
def test_matches_reformatted_payload_without_modifying_signed_bytes(
    case: str, tmp_path: Path
) -> None:
    specifications = qualification_specifications(case)
    document = create_qualification_statement(specifications)
    payload = tmp_path / "decoded.json"
    # Reverse object keys and use CRLF; arrays still follow the statement profile.
    payload.write_bytes((json.dumps(dict(reversed(document.items())), indent=3) + "\r\n").encode())
    original = payload.read_bytes()
    metadata = validate_qualification_statement(payload, list(reversed(specifications)))
    assert metadata == validate_qualification_artifacts(specifications)
    assert payload.read_bytes() == original


@pytest.mark.parametrize(
    "change", ["digest", "kind", "run", "timestamp", "missing", "extra", "order"]
)
def test_rejects_schema_valid_statement_with_a_different_inventory(
    change: str, tmp_path: Path
) -> None:
    specifications = qualification_specifications("transport")
    document = create_qualification_statement(specifications)
    if change == "digest":
        document["subject"][0]["digest"]["sha256"] = "0" * 64
    elif change == "kind":
        item = next(
            item for item in document["predicate"]["artifacts"] if item["kind"] == "other_evidence"
        )
        item["kind"] = "metrics"
    elif change == "run":
        document["predicate"]["run_id"] = "run-11111111-1111-4111-8111-111111111111"
    elif change == "timestamp":
        document["predicate"]["generated_at"] = "2026-09-08T12:00:00Z"
    elif change == "missing":
        document["subject"].pop()
        document["predicate"]["artifacts"].pop()
    elif change == "extra":
        document["subject"].append({"name": "extra.json", "digest": {"sha256": "0" * 64}})
        document["predicate"]["artifacts"].append(
            {"kind": "other_evidence", "subject_name": "extra.json"}
        )
    else:
        document["subject"].reverse()
    validate_document(document, schema="qualification-bundle.v1")
    payload = tmp_path / "decoded.json"
    payload.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ContractError) as raised:
        validate_qualification_statement(payload, specifications)
    assert raised.value.error_id == "qualification.statement_mismatch"
    assert raised.value.json_path == "$"


def test_same_aggregate_value_with_changed_file_bytes_no_longer_matches(tmp_path: Path) -> None:
    specifications = qualification_specifications("transport")
    payload = write_qualification_statement(specifications, tmp_path / "decoded.json")
    aggregate = next(item for item in specifications if item.startswith("acceptance_aggregate:"))
    name, _, source = aggregate.partition("=")
    changed = tmp_path / "aggregate.json"
    changed.write_bytes(Path(source).read_bytes() + b"\n")
    assert load_mapping(source) == load_mapping(changed)
    specifications[specifications.index(aggregate)] = f"{name}={changed}"
    with pytest.raises(ContractError) as raised:
        validate_qualification_statement(payload, specifications)
    assert raised.value.error_id == "qualification.statement_mismatch"


def test_matching_statement_does_not_skip_cross_document_validation(tmp_path: Path) -> None:
    specifications = qualification_specifications("transport")
    payload = write_qualification_statement(specifications, tmp_path / "decoded.json")
    scenario = next(item for item in specifications if item.startswith("scenario:"))
    name, _, source = scenario.partition("=")
    changed = tmp_path / "scenario.json"
    changed.write_bytes(Path(source).read_bytes() + b"\n")
    specifications[specifications.index(scenario)] = f"{name}={changed}"
    with pytest.raises(ContractError, match="scenario") as raised:
        validate_qualification_statement(payload, specifications)
    assert raised.value.error_id == "qualification.invalid"


def test_cli_writes_metadata_and_preserves_output_on_mismatch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    specifications = qualification_specifications("physical")
    payload = write_qualification_statement(specifications, tmp_path / "decoded.json")
    output = tmp_path / "metadata.json"
    arguments = [
        "--format",
        "json",
        "validate-qualification",
        "--statement",
        str(payload),
        "--output",
        str(output),
        "--quiet",
    ]
    for item in specifications:
        arguments.extend(("--artifact", item))
    assert main(arguments) == 0
    assert load_mapping(output) == validate_qualification_artifacts(specifications)
    original = output.read_bytes()
    document = dict(load_mapping(payload))
    document["subject"][0]["digest"]["sha256"] = "0" * 64
    payload.write_text(json.dumps(document), encoding="utf-8")
    assert main(arguments) == 1
    error = json.loads(capsys.readouterr().err)["error"]
    assert error["error_id"] == "qualification.statement_mismatch"
    assert error["path"] == "$"
    assert output.read_bytes() == original


def test_metadata_output_cannot_replace_the_signed_payload_through_an_alias(tmp_path: Path) -> None:
    specifications = qualification_specifications("physical")
    payload = write_qualification_statement(specifications, tmp_path / "decoded.json")
    alias = tmp_path / "output.json"
    alias.hardlink_to(payload)
    original = payload.read_bytes()
    arguments = ["validate-qualification", "--statement", str(payload), "--output", str(alias)]
    for item in specifications:
        arguments.extend(("--artifact", item))
    assert main(arguments) == 1
    assert payload.read_bytes() == alias.read_bytes() == original
