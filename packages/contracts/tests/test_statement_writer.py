from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from robotics_runtime_contracts import (
    ContractError,
    dumps_canonical,
    file_sha256,
    load_mapping,
    validate_document,
)
from robotics_runtime_contracts.cli import main
from robotics_runtime_contracts.statements import (
    create_qualification_statement,
    write_qualification_statement,
)
from robotics_runtime_contracts.writers import WriterError
from tests.support import qualification_specifications


@pytest.mark.parametrize("case", ["transport", "inference", "physical"])
def test_statement_validates_every_subject_and_is_order_independent(
    case: str, tmp_path: Path
) -> None:
    specifications = qualification_specifications(case)
    statement = create_qualification_statement(specifications)
    validate_document(statement, schema="qualification-bundle.v1")
    assert statement["_type"] == "https://in-toto.io/Statement/v1"
    assert set(statement) == {"_type", "subject", "predicateType", "predicate"}
    subjects = {item["name"]: item["digest"]["sha256"] for item in statement["subject"]}
    kinds = {item["subject_name"]: item["kind"] for item in statement["predicate"]["artifacts"]}
    for specification in specifications:
        kind, _, value = specification.partition(":")
        subject, _, path = value.partition("=")
        assert subjects[subject] == file_sha256(path)
        assert kinds[subject] == kind
    reversed_statement = create_qualification_statement(list(reversed(specifications)))
    assert dumps_canonical(statement) == dumps_canonical(reversed_statement)
    output = write_qualification_statement(specifications, tmp_path / "statement.json")
    assert output.read_bytes() == dumps_canonical(statement)


def test_statement_hashes_noncanonical_source_bytes_not_json_content(tmp_path: Path) -> None:
    source = tmp_path / "observation.json"
    source.write_bytes(b'{ "observed": 7 }\r\n')
    specifications = qualification_specifications("transport")
    specifications.append(f"other_evidence:evidence/formatting.json={source}")
    statement = create_qualification_statement(specifications)
    subject = next(
        item for item in statement["subject"] if item["name"] == "evidence/formatting.json"
    )
    assert subject["digest"]["sha256"] == file_sha256(source)
    content_hash = hashlib.sha256(dumps_canonical(load_mapping(source))).hexdigest()
    assert subject["digest"]["sha256"] != content_hash


def test_same_value_changed_bytes_break_existing_qualification_links(tmp_path: Path) -> None:
    specifications = qualification_specifications("transport")
    scenario_spec = next(item for item in specifications if item.startswith("scenario:"))
    label, _, path = scenario_spec.partition("=")
    changed = tmp_path / "scenario.json"
    changed.write_bytes(Path(path).read_bytes() + b"\n")
    assert load_mapping(changed) == load_mapping(path)
    specifications[specifications.index(scenario_spec)] = f"{label}={changed}"
    destination = tmp_path / "statement.json"
    destination.write_bytes(b"previous signed input")
    with pytest.raises(ContractError, match="scenario"):
        write_qualification_statement(specifications, destination)
    assert destination.read_bytes() == b"previous signed input"


def test_invalid_or_duplicate_artifact_set_never_produces_a_statement(tmp_path: Path) -> None:
    specifications = qualification_specifications("transport")
    destination = tmp_path / "statement.json"
    with pytest.raises(ContractError, match="unique"):
        write_qualification_statement([*specifications, specifications[0]], destination)
    assert not destination.exists()
    without_scenario = [item for item in specifications if not item.startswith("scenario:")]
    with pytest.raises(ContractError, match="scenario"):
        write_qualification_statement(without_scenario, destination)
    assert not destination.exists()


def test_output_cannot_replace_a_validated_subject(tmp_path: Path) -> None:
    source = tmp_path / "extra.json"
    source.write_bytes(b'{ "extra": true }\n')
    original = source.read_bytes()
    specifications = [
        *qualification_specifications("transport"),
        f"other_evidence:evidence/extra.json={source}",
    ]
    with pytest.raises(WriterError, match="must not replace input"):
        write_qualification_statement(specifications, source)
    assert source.read_bytes() == original


def test_cli_emits_standard_statement_and_preserves_output_on_bad_inputs(tmp_path: Path) -> None:
    destination = tmp_path / "statement.json"
    arguments = ["qualification", "statement", "--output", str(destination)]
    for item in qualification_specifications("physical"):
        arguments.extend(("--artifact", item))
    assert main(arguments) == 0
    statement = load_mapping(destination)
    validate_document(statement, schema="qualification-bundle.v1")
    original = destination.read_bytes()
    assert main(arguments) == 0
    assert destination.read_bytes() == original
    assert (
        main(["qualification", "statement", "--artifact", "invalid", "--output", str(destination)])
        == 2
    )
    assert destination.read_bytes() == original
    assert main(["qualification", "statement", "--output", str(destination)]) == 2
