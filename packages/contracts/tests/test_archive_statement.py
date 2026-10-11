from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from robotics_runtime_contracts import ContractError, dumps_canonical, statements, validate_document
from robotics_runtime_contracts.writers import WriterError
from tests.extension_support import NAMESPACE, SCHEMAS, with_extension

V2 = "qualification-bundle.v2"
RULE = "exact_assertion_outcome"


def _metadata() -> dict[str, Any]:
    """Schema fixture for the writer; archive validation has separate source tests."""
    kinds = {
        "acceptance-aggregate.json": "acceptance_aggregate",
        "acceptance-run.json": "acceptance_run",
        "contexts/environment.json": "other_evidence",
        "contexts/new-method.json": "other_evidence",
        "contexts/original-method.json": "other_evidence",
        "evidence-indexes/native.json": "evidence_index",
        "evidence/native-state.json": "other_evidence",
        "observations/native.json": "acceptance_observation",
        "original-aggregate.json": "acceptance_aggregate",
        "original-results/native.json": "domain_result",
        "results/native.json": "domain_result",
        "runtime-manifests/native.json": "runtime_manifest",
        "scenario.json": "scenario",
    }
    artifacts = [
        {"kind": kinds[name], "subject_name": name, "sha256": f"{index:064x}"}
        for index, name in enumerate(sorted(kinds), 1)
    ]
    digests = {item["subject_name"]: item["sha256"] for item in artifacts}

    def reference(name: str) -> dict[str, Any]:
        return {
            "uri": "https://example.org/archive/" + name,
            "sha256": digests[name],
            "size_bytes": 128,
            "media_type": "application/json",
        }

    def evaluation(name: str, timestamp: str) -> dict[str, Any]:
        return {
            "method": {
                "implementation": "robotics_acceptance_harness.evaluate_acceptance",
                "version": "0.21.0",
                "configuration": reference(name),
            },
            "environment": reference("contexts/environment.json"),
            "started_at": timestamp,
            "finished_at": timestamp,
            "calibration": {
                "state": "not_applicable",
                "reason": "raw software count has no calibration",
            },
            "coverage": {
                "covered_assertions": [
                    {
                        "assertion_id": "counter-error",
                        "evidence_sha256": [digests["evidence/native-state.json"]],
                    }
                ],
                "uncovered_assertions": [],
            },
        }

    original = {
        "domain_id": "native",
        "runtime_manifest": "runtime-manifests/native.json",
        "acceptance_observation": "observations/native.json",
        "evidence_index": "evidence-indexes/native.json",
        "acceptance_result": "original-results/native.json",
        "result_id": "result-00000000-0000-4000-8000-000000000001",
        "status": "failed",
        "evaluation": evaluation("contexts/original-method.json", "2026-10-11T10:00:01Z"),
    }
    assessment = {
        "domain_id": "native",
        "acceptance_result": "results/native.json",
        "result_id": "result-00000000-0000-4000-8000-000000000002",
        "status": "passed",
        "evaluation": evaluation("contexts/new-method.json", "2026-10-11T10:05:00Z"),
    }
    return {
        "schema_version": V2,
        "run_id": "run-00000000-0000-4000-8000-000000000001",
        "generated_at": "2026-10-11T10:05:01.123456789Z",
        "artifacts": artifacts,
        "original_execution": {
            "scenario": "scenario.json",
            "acceptance_run": "acceptance-run.json",
            "acceptance_aggregate": "original-aggregate.json",
            "domains": [original],
        },
        "acceptance_aggregate": "acceptance-aggregate.json",
        "assessments": [assessment],
        "comparison": {
            "rule": RULE,
            "per_domain": [
                {
                    "domain_id": "native",
                    "original_result": "original-results/native.json",
                    "assessment_result": "results/native.json",
                    "status": "not_comparable",
                    "compared_assertions": [],
                    "excluded_assertions": ["counter-error"],
                    "reasons": ["method_changed"],
                }
            ],
        },
    }


@pytest.fixture
def archive_loader(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def load(specifications: Any, extension_schemas: Any = None, **options: Any) -> dict[str, Any]:
        calls.append(
            {
                "specifications": specifications,
                "extension_schemas": extension_schemas,
                **options,
            }
        )
        return deepcopy(_metadata())

    monkeypatch.setattr(statements, "validate_qualification_artifacts", load)
    return calls


def _statement() -> dict[str, Any]:
    return statements.create_qualification_statement([], schema_version=V2, comparison_rule=RULE)


def test_archive_writer_binds_both_outcomes_from_one_validated_capture(
    archive_loader: list[dict[str, Any]],
) -> None:
    document = _statement()
    assert archive_loader == [
        {
            "specifications": [],
            "extension_schemas": None,
            "schema_version": V2,
            "comparison_rule": RULE,
        }
    ]
    predicate = document["predicate"]
    assert predicate["original_execution"]["domains"][0]["status"] == "failed"
    assert predicate["assessments"][0]["status"] == "passed"
    assert predicate["comparison"]["per_domain"][0]["status"] == "not_comparable"
    assert predicate["generated_at"] == _metadata()["generated_at"]
    assert document["subject"] == [
        {"name": item["subject_name"], "digest": {"sha256": item["sha256"]}}
        for item in _metadata()["artifacts"]
    ]
    assert "status" not in predicate
    assert "assessment_id" not in predicate
    assert "sha256" not in predicate["artifacts"][0]


@pytest.mark.parametrize(
    ("version", "rule"),
    [
        ("qualification-bundle.v1", RULE),
        (V2, None),
        (V2, "compare_whole_verdict"),
        ("qualification-bundle.v3", RULE),
    ],
)
def test_invalid_archive_options_refuse_before_artifact_reads_and_preserve_output(
    version: str,
    rule: str | None,
    tmp_path: Path,
    archive_loader: list[dict[str, Any]],
) -> None:
    output = tmp_path / "statement.json"
    output.write_bytes(b"previous statement")
    with pytest.raises(ContractError):
        statements.write_qualification_statement(
            ["not read"], output, schema_version=version, comparison_rule=rule
        )
    assert not archive_loader
    assert output.read_bytes() == b"previous statement"


def test_archive_matching_preserves_signed_bytes_and_dispatches_explicit_rule(
    tmp_path: Path,
    archive_loader: list[dict[str, Any]],
) -> None:
    document = _statement()
    archive_loader.clear()
    source = tmp_path / "statement.json"
    raw = (json.dumps(dict(reversed(document.items())), indent=3) + "\r\n").encode()
    source.write_bytes(raw)
    metadata = statements.validate_qualification_statement(source, [])
    assert metadata == _metadata()
    assert len(archive_loader) == 1
    assert archive_loader[0]["schema_version"] == V2
    assert archive_loader[0]["comparison_rule"] == RULE
    assert source.read_bytes() == raw


@pytest.mark.parametrize("predicate", [None, [], {}, {"schema_version": "bundle.v9"}])
def test_unknown_statement_profile_refuses_before_artifact_reads(
    predicate: Any,
    tmp_path: Path,
    archive_loader: list[dict[str, Any]],
) -> None:
    source = tmp_path / "statement.json"
    source.write_text(json.dumps({"predicate": predicate}))
    with pytest.raises(ContractError) as raised:
        statements.validate_qualification_statement(source, [])
    assert raised.value.error_id == "qualification.schema_unsupported"
    assert not archive_loader


def test_predicate_type_cannot_select_a_different_protocol(
    tmp_path: Path,
    archive_loader: list[dict[str, Any]],
) -> None:
    document = _statement()
    archive_loader.clear()
    document["predicateType"] = document["predicateType"].removesuffix("2") + "1"
    source = tmp_path / "statement.json"
    source.write_text(json.dumps(document))
    with pytest.raises(ContractError):
        statements.validate_qualification_statement(source, [])
    assert not archive_loader


@pytest.mark.parametrize("field", ["calibration", "coverage"])
def test_historical_absence_stays_absent_but_new_assessment_requires_observations(
    field: str, archive_loader: list[dict[str, Any]]
) -> None:
    document = _statement()
    del document["predicate"]["original_execution"]["domains"][0]["evaluation"][field]
    validate_document(document, schema=V2)
    del document["predicate"]["assessments"][0]["evaluation"][field]
    with pytest.raises(ContractError):
        validate_document(document, schema=V2)


@pytest.mark.parametrize(
    ("status", "compared", "reasons", "valid"),
    [
        ("matched", ["counter-error"], [], True),
        ("matched", [], [], False),
        ("matched", ["counter-error"], ["method_changed"], False),
        ("different", ["counter-error"], ["assertion_outcome_changed"], True),
        ("different", [], ["assertion_outcome_changed"], False),
        ("different", ["counter-error"], ["method_changed"], False),
        ("not_comparable", [], ["calibration_unobserved"], True),
        ("not_comparable", [], [], False),
        ("not_comparable", ["counter-error"], ["method_changed"], False),
        ("not_comparable", [], ["assertion_outcome_changed"], False),
    ],
)
def test_comparison_schema_cannot_misrepresent_unobserved_or_uncompared_assertions(
    status: str,
    compared: list[str],
    reasons: list[str],
    valid: bool,
    archive_loader: list[dict[str, Any]],
) -> None:
    document = _statement()
    comparison = document["predicate"]["comparison"]["per_domain"][0]
    comparison.update(status=status, compared_assertions=compared, reasons=reasons)
    if valid:
        validate_document(document, schema=V2)
    else:
        with pytest.raises(ContractError):
            validate_document(document, schema=V2)


@pytest.mark.parametrize(
    "change",
    [
        "digest",
        "original_status",
        "assessment_result",
        "method",
        "calibration",
        "coverage",
        "comparison",
    ],
)
def test_schema_valid_archive_claim_tampering_fails_exact_metadata_match(
    change: str,
    tmp_path: Path,
    archive_loader: list[dict[str, Any]],
) -> None:
    document = _statement()
    predicate = document["predicate"]
    evaluation = predicate["assessments"][0]["evaluation"]
    if change == "digest":
        document["subject"][0]["digest"]["sha256"] = "f" * 64
    elif change == "original_status":
        predicate["original_execution"]["domains"][0]["status"] = "passed"
    elif change == "assessment_result":
        predicate["assessments"][0]["result_id"] = "result-00000000-0000-4000-8000-000000000099"
    elif change == "method":
        evaluation["method"]["version"] = "0.21.1"
    elif change == "calibration":
        evaluation["calibration"]["reason"] = "a substituted reason"
    elif change == "coverage":
        evaluation["coverage"]["covered_assertions"][0]["evidence_sha256"] = ["e" * 64]
    else:
        predicate["comparison"]["per_domain"][0]["reasons"] = ["environment_changed"]
    validate_document(document, schema=V2)
    source = tmp_path / "statement.json"
    source.write_bytes(dumps_canonical(document))
    with pytest.raises(ContractError) as raised:
        statements.validate_qualification_statement(source, [])
    assert raised.value.error_id == "qualification.statement_mismatch"


def test_archive_writer_is_deterministic_and_cannot_overwrite_an_input_alias(
    tmp_path: Path, archive_loader: list[dict[str, Any]]
) -> None:
    source = tmp_path / "original.json"
    source.write_bytes(b"unchanged captured source")
    alias = tmp_path / "alias.json"
    alias.hardlink_to(source)
    specifications = [f"other_evidence:original.json={source}"]
    with pytest.raises(WriterError):
        statements.write_qualification_statement(
            specifications, alias, schema_version=V2, comparison_rule=RULE
        )
    assert source.read_bytes() == alias.read_bytes() == b"unchanged captured source"
    output = tmp_path / "statement.json"
    statements.write_qualification_statement([], output, schema_version=V2, comparison_rule=RULE)
    before = output.read_bytes()
    statements.write_qualification_statement([], output, schema_version=V2, comparison_rule=RULE)
    assert before == output.read_bytes() == dumps_canonical(_statement())


@pytest.mark.parametrize("change", ["duplicate-subject", "duplicate-classification", "missing"])
def test_archive_document_reuses_subject_inventory_semantics(
    change: str, archive_loader: list[dict[str, Any]]
) -> None:
    document = _statement()
    if change == "duplicate-subject":
        document["subject"].append(deepcopy(document["subject"][0]))
    elif change == "duplicate-classification":
        document["predicate"]["artifacts"].append(deepcopy(document["predicate"]["artifacts"][0]))
    else:
        document["predicate"]["artifacts"].pop()
    with pytest.raises(ContractError):
        validate_document(document, schema=V2)


def test_archive_extensions_are_validated_inside_predicate_before_subject_reads(
    tmp_path: Path, archive_loader: list[dict[str, Any]]
) -> None:
    document = _statement()
    document["predicate"] = with_extension(document["predicate"])
    source = tmp_path / "statement.json"
    source.write_bytes(dumps_canonical(document))
    metadata = statements.validate_qualification_statement(source, [], extension_schemas=SCHEMAS)
    assert metadata == _metadata()
    archive_loader.clear()
    document["predicate"]["extensions"][NAMESPACE]["mission_id"] = ""
    source.write_bytes(dumps_canonical(document))
    with pytest.raises(ContractError):
        statements.validate_qualification_statement(source, [], extension_schemas=SCHEMAS)
    assert not archive_loader
    with pytest.raises(ContractError, match="extension"):
        validate_document(document, schema=V2)
