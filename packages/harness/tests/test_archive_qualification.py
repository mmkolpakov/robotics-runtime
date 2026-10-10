from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from robotics_runtime_contracts import ContractError, qualification
from robotics_runtime_contracts._qualification_archive import validate_archive_documents
from robotics_runtime_contracts._qualification_files import load_artifact
from robotics_runtime_contracts.statements import (
    create_qualification_statement,
    validate_qualification_statement,
    write_qualification_statement,
)

from robotics_acceptance_harness.aggregate import aggregate_results
from tests.test_neutral_qualification import (
    T6,
    _archive,
    _digest,
    _document,
    _reference,
    _write,
)

V2 = "qualification-bundle.v2"
RULE = "exact_assertion_outcome"


def _archive_pair(tmp_path: Path, domains: tuple[str, ...] = ("primary",)) -> list[str]:
    """Artifact linkage fixture; real CLI computation is tested separately."""
    specs = _archive(tmp_path, domains)
    specs = [
        item.replace("domain_result:results/", "domain_result:original-results/").replace(
            "acceptance_aggregate:acceptance-aggregate.json=",
            "acceptance_aggregate:original-aggregate.json=",
        )
        for item in specs
    ]
    controls = _document(tmp_path / "method.json")
    controls["calibration"] = {
        "state": "not_applicable",
        "reason": "this linkage fixture has no calibrated values",
    }
    method = _write(tmp_path / "new-method.json", controls)
    specs.append(f"other_evidence:contexts/new-method.json={method}")
    new_results = []
    for domain in domains:
        original = tmp_path / f"result-{domain}.json"
        result = _document(original)
        result["result_id"] = f"result-{uuid4()}"
        result["original_execution"]["original_result_sha256"] = _digest(original)
        result["evaluation"]["method"]["configuration"] = _reference(method)
        result["evaluation"]["started_at"] = T6
        result["evaluation"]["finished_at"] = T6
        result["evaluation"]["calibration"] = controls["calibration"]
        result["evaluation"]["coverage"] = {"covered_assertions": [], "uncovered_assertions": []}
        path = _write(tmp_path / f"new-result-{domain}.json", result)
        new_results.append(path)
        specs.append(f"domain_result:results/{domain}.json={path}")
    aggregate = aggregate_results(
        scenario_path=tmp_path / "scenario.json",
        run_context_path=tmp_path / "run.json",
        result_paths=new_results,
        output_path=tmp_path / "new-aggregate.json",
        generated_at=datetime.fromisoformat("2026-10-10T12:00:07+00:00"),
    )
    specs.append(f"acceptance_aggregate:acceptance-aggregate.json={aggregate}")
    return specs


def _qualify(specs: list[str]) -> dict[str, Any]:
    return qualification.validate_qualification_artifacts(
        specs, schema_version=V2, comparison_rule=RULE
    )


def _refresh(tmp_path: Path) -> None:
    path = tmp_path / "new-aggregate.json"
    aggregate = _document(path)
    for entry in aggregate["per_domain_results"]:
        result_path = tmp_path / f"new-result-{entry['domain_id']}.json"
        result = _document(result_path)
        entry.update(
            result_id=result["result_id"],
            result_sha256=_digest(result_path),
            status=result["status"],
        )
    _write(path, aggregate)


def test_archive_reads_each_file_once_and_preserves_unknown_historical_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    specs = _archive_pair(tmp_path)
    before = {path: path.read_bytes() for path in tmp_path.iterdir() if path.is_file()}
    actual_loader = load_artifact
    seen: list[str] = []

    def capture(specification: str, *args: Any, **kwargs: Any) -> Any:
        seen.append(specification)
        return actual_loader(specification, *args, **kwargs)

    monkeypatch.setattr(qualification, "load_artifact", capture)
    metadata = _qualify(list(reversed(specs)))
    assert sorted(seen) == sorted(specs)
    original = metadata["original_execution"]["domains"][0]["evaluation"]
    assert "calibration" not in original and "coverage" not in original
    assert metadata["comparison"]["per_domain"][0] == {
        "domain_id": "primary",
        "original_result": "original-results/primary.json",
        "assessment_result": "results/primary.json",
        "status": "not_comparable",
        "compared_assertions": [],
        "excluded_assertions": [],
        "reasons": [
            "calibration_unobserved",
            "coverage_unobserved",
            "method_changed",
            "no_covered_assertions",
        ],
    }
    assert {path: path.read_bytes() for path in before} == before


def test_archive_statement_matches_full_captured_chain_and_original_bytes(tmp_path: Path) -> None:
    specs = _archive_pair(tmp_path, ("second", "first"))
    expected = _qualify(specs)
    output = write_qualification_statement(
        specs, tmp_path / "statement.json", schema_version=V2, comparison_rule=RULE
    )
    assert validate_qualification_statement(output, list(reversed(specs))) == expected
    assert [item["domain_id"] for item in expected["assessments"]] == ["first", "second"]
    assert _document(output)["predicate"]["original_execution"] == expected["original_execution"]
    assert create_qualification_statement(
        list(reversed(specs)), schema_version=V2, comparison_rule=RULE
    ) == _document(output)


@pytest.mark.parametrize(
    "change",
    [
        "baseline",
        "same-id",
        "source",
        "profile",
        "early-time",
        "missing-calibration",
        "missing-coverage",
        "false-coverage",
        "missing-control",
    ],
)
def test_archive_refuses_substituted_sources_and_false_comparison_claims(
    tmp_path: Path, change: str
) -> None:
    specs = _archive_pair(tmp_path)
    path = tmp_path / "new-result-primary.json"
    result = _document(path)
    if change == "baseline":
        result["original_execution"]["original_result_sha256"] = "f" * 64
    elif change == "same-id":
        result["result_id"] = _document(tmp_path / "result-primary.json")["result_id"]
    elif change == "source":
        result["original_execution"]["observation_sha256"] = "f" * 64
    elif change == "profile":
        result["profile"]["profile_id"] = "org.example.foreign"
    elif change == "early-time":
        result["evaluation"]["started_at"] = "2026-10-10T12:00:04Z"
    elif change.startswith("missing-") and change != "missing-control":
        del result["evaluation"][change.removeprefix("missing-")]
    elif change == "false-coverage":
        result["evaluation"]["coverage"]["covered_assertions"] = [
            {
                "assertion_id": "invented",
                "evidence_sha256": [_digest(tmp_path / "native-state.json")],
            }
        ]
    else:
        specs = [item for item in specs if "contexts/new-method.json=" not in item]
    _write(path, result)
    _refresh(tmp_path)
    with pytest.raises(ContractError):
        _qualify(specs)


def test_archive_requires_actual_captured_control_bytes_for_descriptor_inspection(
    tmp_path: Path,
) -> None:
    specs = _archive_pair(tmp_path)
    artifacts, diagnostics = qualification._capture_artifacts(specs)
    assert not diagnostics
    missing = [
        replace(item, native_metadata_bytes=None)
        if item.subject_name == "evaluation/environment.json"
        else item
        for item in artifacts
    ]
    with pytest.raises(ContractError, match="captured method, environment"):
        validate_archive_documents(missing)


def test_archive_rejects_unused_results_and_duplicate_subjects(tmp_path: Path) -> None:
    specs = _archive_pair(tmp_path)
    extra = next(item for item in specs if item.startswith("domain_result:results/"))
    with pytest.raises(ContractError, match="unique"):
        _qualify([*specs, extra])
    with pytest.raises(ContractError, match="uniquely"):
        _qualify([*specs, extra.replace("results/primary.json=", "extra-result.json=")])


def test_archive_rejects_schema_valid_mixed_result_versions_without_traceback(
    tmp_path: Path,
) -> None:
    specs = _archive_pair(tmp_path)
    fixture = (
        Path(__file__).parents[2] / "contracts/tests/fixtures/qualification/inference/result.json"
    )
    specs = [
        item.partition("=")[0] + "=" + str(fixture)
        if item.startswith("domain_result:original-results/")
        else item
        for item in specs
    ]
    with pytest.raises(ContractError, match="all use acceptance-result.v2"):
        _qualify(specs)


def _native_specifications(
    inputs: dict[str, Any], original: Path, assessment: Path, tmp_path: Path
) -> list[str]:
    result = _document(original / "acceptance-result.json")
    domain = result["domain_id"]
    index = _document(Path(inputs["evidence_index"]))
    observation = next(
        item["local_path"]
        for item in index["artifacts"]
        if item["kind"] == "acceptance_observation"
    )
    specs = [
        f"scenario:scenario.json={inputs['scenario']}",
        f"acceptance_run:acceptance-run.json={inputs['run_context']}",
        f"runtime_manifest:runtime-manifests/{domain}.json={inputs['runtime']}",
        f"acceptance_observation:observations/{domain}.json={observation}",
        f"evidence_index:evidence-indexes/{domain}.json={inputs['evidence_index']}",
        f"domain_result:original-results/{domain}.json={original / 'acceptance-result.json'}",
        f"domain_result:results/{domain}.json={assessment / 'acceptance-result.json'}",
    ]
    seen: set[tuple[str, int]] = set()

    def raw(name: str, kind: str, path: Path) -> None:
        identity = (_digest(path), path.stat().st_size)
        if identity not in seen:
            specs.append(f"{kind}:{name}={path}")
            seen.add(identity)

    for item in index["artifacts"]:
        if item["kind"] == "acceptance_observation":
            continue
        kind = "metrics" if item["kind"] == "metrics" else "other_evidence"
        raw("evidence/" + item["artifact_id"] + ".bin", kind, Path(item["local_path"]))
    for label, output in (("original", original), ("assessment", assessment)):
        for name in ("method", "environment"):
            raw(
                f"contexts/{label}-{name}.json",
                "other_evidence",
                output / f"evaluation-{name}.json",
            )
        aggregate = aggregate_results(
            scenario_path=inputs["scenario"],
            run_context_path=inputs["run_context"],
            result_paths=[output / "acceptance-result.json"],
            output_path=tmp_path / f"{label}-aggregate.json",
        )
        subject = "original-aggregate.json" if label == "original" else "acceptance-aggregate.json"
        specs.append(f"acceptance_aggregate:{subject}={aggregate}")
    return specs


@pytest.mark.parametrize("changed_method", [False, True])
def test_actual_counter_archive_reassessment_uses_public_cli_without_rerunning_source(
    tmp_path: Path, changed_method: bool
) -> None:
    from tests.test_native import evaluate, produce

    inputs = produce(tmp_path / "archive", "--error", "7")
    scenario = _document(Path(inputs["scenario"]))
    controls = {
        key: scenario[key]
        for key in ("metric_definitions", "assertions", "evaluator_requirements", "evidence_policy")
    }
    controls["calibration"] = {
        "state": "not_applicable",
        "reason": "raw software count has no calibration",
    }
    initial_controls = _write(tmp_path / "initial-controls.json", controls)
    original_output = tmp_path / "original"
    original = evaluate({**inputs, "assessment_controls": initial_controls}, original_output)
    assert original.returncode == 1, original.stderr
    original_result = original_output / "acceptance-result.json"
    before = {
        path: path.read_bytes()
        for directory in (tmp_path / "archive", original_output)
        for path in directory.iterdir()
        if path.is_file()
    }
    if changed_method:
        criterion = next(
            item for item in controls["assertions"] if item["assertion_id"] == "counter-error"
        )
        criterion.update(operator="lte", threshold=10)
    new_controls = _write(tmp_path / "new-controls.json", controls)
    assessment_output = tmp_path / "assessment"
    completed = evaluate(
        {
            **inputs,
            "assessment_controls": new_controls,
            "original_result": original_result,
        },
        assessment_output,
    )
    assert completed.returncode == (0 if changed_method else 1), completed.stderr
    specs = _native_specifications(inputs, original_output, assessment_output, tmp_path)
    metadata = _qualify(specs)
    assert metadata["original_execution"]["domains"][0]["status"] == "failed"
    assert metadata["assessments"][0]["status"] == ("passed" if changed_method else "failed")
    comparison = metadata["comparison"]["per_domain"][0]
    assert comparison["status"] == ("not_comparable" if changed_method else "matched")
    assert comparison["reasons"] == (["method_changed"] if changed_method else [])
    assert comparison["compared_assertions"] == (
        [] if changed_method else ["counter-accepted", "counter-error", "counter-finished"]
    )
    statement = write_qualification_statement(
        specs, tmp_path / "qualification.json", schema_version=V2, comparison_rule=RULE
    )
    assert validate_qualification_statement(statement, list(reversed(specs))) == metadata
    assert {path: path.read_bytes() for path in before} == before


def test_public_contract_cli_selects_archive_protocol_and_matches_statement(tmp_path: Path) -> None:
    from robotics_runtime_contracts.cli import main

    specs = _archive_pair(tmp_path)
    artifacts = [value for item in specs for value in ("--artifact", item)]
    statement = tmp_path / "statement.json"
    assert (
        main(
            [
                "qualification",
                "statement",
                "--schema-version",
                V2,
                "--comparison-rule",
                RULE,
                "--output",
                str(statement),
                *artifacts,
            ]
        )
        == 0
    )
    metadata = tmp_path / "metadata.json"
    assert (
        main(
            [
                "validate-qualification",
                "--schema-version",
                V2,
                "--comparison-rule",
                RULE,
                "--quiet",
                "--output",
                str(metadata),
                *artifacts,
            ]
        )
        == 0
    )
    expected = _qualify(specs)
    assert _document(metadata) == expected
    assert (
        main(
            [
                "validate-qualification",
                "--statement",
                str(statement),
                "--quiet",
                "--output",
                str(metadata),
                *artifacts,
            ]
        )
        == 0
    )
    before = metadata.read_bytes()
    assert (
        main(
            [
                "validate-qualification",
                "--statement",
                str(statement),
                "--schema-version",
                V2,
                "--quiet",
                "--output",
                str(metadata),
                *artifacts,
            ]
        )
        == 2
    )
    assert metadata.read_bytes() == before
