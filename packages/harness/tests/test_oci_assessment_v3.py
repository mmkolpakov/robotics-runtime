from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from robotics_runtime_contracts import ContractError, qualification, validate_document

from robotics_acceptance_harness.archive import load_assessment_controls
from robotics_acceptance_harness.evaluation import EvaluationError, evaluator_inventory
from robotics_acceptance_harness.native import evaluate_native
from tests.test_archive_controls import controls
from tests.test_archive_qualification import _archive_pair, _refresh
from tests.test_native import produce
from tests.test_neutral_qualification import _archive, _document, _reference, _write

DIGEST = "a" * 64
OCI: dict[str, Any] = {
    "kind": "oci",
    "namespace": "org.example.check",
    "execution_subject": {
        "kind": "oci_image",
        "locator": "oci://example.invalid/evaluator@sha256:" + DIGEST,
        "digest": "sha256:" + DIGEST,
    },
    "expected_assertion_ids": ["org.example.check.first"],
}


def _pair(tmp_path: Path, *, oci: bool, result_version: str, marked: bool) -> list[str]:
    specs = _archive_pair(tmp_path)
    method_path = tmp_path / "new-method.json"
    method = _document(method_path)
    if marked:
        method["schema_version"] = "assessment-controls.v1"
    if oci:
        method["evaluator_requirements"] = [deepcopy(OCI)]
    _write(method_path, method)
    result_path = tmp_path / "new-result-primary.json"
    result = _document(result_path)
    result["schema_version"] = result_version
    result["evaluation"]["method"]["configuration"] = _reference(method_path)
    if oci:
        result["evaluators"] = [deepcopy(OCI)]
        result["evaluation"]["coverage"] = {
            "covered_assertions": [],
            "uncovered_assertions": [
                {"assertion_id": OCI["expected_assertion_ids"][0], "reason": "unavailable"}
            ],
        }
        result["unevaluated"].append("$.assertions." + OCI["expected_assertion_ids"][0])
        result["status"] = "incomplete"
    _write(result_path, result)
    _refresh(tmp_path)
    return specs


def _qualify(specs: list[str]) -> dict[str, Any]:
    return qualification.validate_qualification_artifacts(
        specs, schema_version="qualification-bundle.v2", comparison_rule="exact_assertion_outcome"
    )


def test_v3_result_complete_and_incomplete_coverage(tmp_path: Path) -> None:
    _archive(tmp_path)
    result = _document(tmp_path / "result-primary.json")
    result["schema_version"] = "acceptance-result.v3"
    result["evaluators"] = [deepcopy(OCI)]
    result["evaluation"]["coverage"] = {
        "covered_assertions": [],
        "uncovered_assertions": [
            {"assertion_id": OCI["expected_assertion_ids"][0], "reason": "unavailable"}
        ],
    }
    result["unevaluated"].append("$.assertions." + OCI["expected_assertion_ids"][0])
    validate_document(result)
    bad = deepcopy(result)
    bad["status"] = "passed"
    with pytest.raises(ContractError):
        validate_document(bad)
    bad = deepcopy(result)
    bad["evaluation"]["coverage"]["uncovered_assertions"].clear()
    with pytest.raises(ContractError):
        validate_document(bad)
    bad = deepcopy(result)
    bad["evaluators"][0]["expected_assertion_ids"] = ["other.check.first"]
    with pytest.raises(ContractError):
        validate_document(bad)

    evidence = result["evidence"][0]["sha256"]
    result["assertion_results"].append(
        {
            "assertion_id": OCI["expected_assertion_ids"][0],
            "source": "product",
            "namespace": OCI["namespace"],
            "status": "passed",
            "observed_value": 1,
            "unit": "1",
            "evidence_sha256": [evidence],
        }
    )
    result["evaluation"]["coverage"] = {
        "covered_assertions": [
            {"assertion_id": OCI["expected_assertion_ids"][0], "evidence_sha256": [evidence]}
        ],
        "uncovered_assertions": [],
    }
    result["unevaluated"] = []
    result["status"] = "passed"
    validate_document(result)
    bad = deepcopy(result)
    bad["assertion_results"][-1]["assertion_id"] = "org.example.check.extra"
    with pytest.raises(ContractError):
        validate_document(bad)


def test_v3_pair_reuses_original_v2_and_rejects_crossed_controls(tmp_path: Path) -> None:
    good = tmp_path / "good"
    good.mkdir()
    specs = _pair(good, oci=False, result_version="acceptance-result.v3", marked=True)
    _qualify(specs)
    assert _document(good / "result-primary.json")["schema_version"] == "acceptance-result.v2"

    for result_version, marked in (("acceptance-result.v2", True), ("acceptance-result.v3", False)):
        case = tmp_path / ("marked" if marked else "unmarked")
        case.mkdir()
        specs = _pair(case, oci=False, result_version=result_version, marked=marked)
        with pytest.raises(ContractError, match="result and assessment controls versions differ"):
            _qualify(specs)


def test_public_qualification_cli_refuses_oci_without_claiming_admission(tmp_path: Path) -> None:
    specs = _pair(tmp_path, oci=True, result_version="acceptance-result.v3", marked=True)
    result = _document(tmp_path / "new-result-primary.json")
    validate_document(result)
    command = [
        sys.executable,
        "-c",
        "import sys; from robotics_runtime_contracts.cli import main; sys.exit(main())",
        "validate-qualification",
        "--schema-version",
        "qualification-bundle.v2",
        "--comparison-rule",
        "exact_assertion_outcome",
    ]
    command.extend(value for specification in specs for value in ("--artifact", specification))
    completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=30)
    assert completed.returncode != 0
    assert "OCI evaluator qualification is not supported" in completed.stdout + completed.stderr
    assert "KeyError" not in completed.stdout + completed.stderr


@pytest.mark.parametrize("requirements", [[], [OCI]])
def test_harness_refuses_versioned_controls_before_execution(
    tmp_path: Path, requirements: list[dict[str, Any]]
) -> None:
    method = controls()
    method["schema_version"] = "assessment-controls.v1"
    method["evaluator_requirements"] = deepcopy(requirements)
    path = tmp_path / "method.json"
    path.write_text(json.dumps(method))
    selected = load_assessment_controls(path)
    context: Any = SimpleNamespace(method_controls=selected.data)
    with pytest.raises(
        EvaluationError, match="versioned assessment controls execution is not supported"
    ):
        evaluate_native(context, cast(Any, None), tmp_path / "result", None)
    assert not (tmp_path / "result").exists()


def test_default_wheel_inventory_refuses_oci() -> None:
    with pytest.raises(EvaluationError, match="OCI evaluator execution is not supported"):
        evaluator_inventory([OCI])


def test_harness_cli_refuses_versioned_controls_before_loading_wheel_profile(
    tmp_path: Path,
) -> None:
    inputs = produce(tmp_path / "source")
    method = controls()
    method["schema_version"] = "assessment-controls.v1"
    method["evaluator_requirements"] = [deepcopy(OCI)]
    controls_path = tmp_path / "method.json"
    controls_path.write_text(json.dumps(method))
    destination = tmp_path / "assessment"
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment["PATH"]
    arguments = ["robotics-acceptance", "evaluate"]
    arguments.extend(
        value
        for name, item in inputs.items()
        for value in ("--" + name.replace("_", "-"), str(item))
    )
    arguments.extend(
        [
            "--output",
            str(destination),
            "--assessment-controls",
            str(controls_path),
            "--evaluator-trust-profile",
            str(tmp_path / "missing-profile.json"),
        ]
    )
    completed = subprocess.run(
        arguments, check=False, capture_output=True, text=True, env=environment, timeout=60
    )
    assert completed.returncode != 0
    assert (
        "versioned assessment controls execution is not supported"
        in completed.stdout + completed.stderr
    )
    assert not destination.exists()


def test_trusted_embedding_callback_still_works() -> None:
    from robotics_acceptance_harness.evaluation import evaluate_acceptance
    from robotics_acceptance_harness.metrics import AssertionEvaluation
    from tests.test_evaluation import EVIDENCE_DIGEST, context

    row = AssertionEvaluation(
        "org.example.check.first",
        "passed",
        1,
        "1",
        source="product",
        namespace="org.example.check",
        evidence_sha256=(EVIDENCE_DIGEST,),
    )
    outcome = evaluate_acceptance(
        context(), evaluators=(("org.example.check", lambda _context: (row,)),)
    )
    assert outcome[-1] == row


def test_public_v1_qualification_refuses_v3_result(tmp_path: Path) -> None:
    specs = _archive(tmp_path)
    result_path = tmp_path / "result-primary.json"
    result = _document(result_path)
    result["schema_version"] = "acceptance-result.v3"
    validate_document(result)
    _write(result_path, result)
    command = [
        sys.executable,
        "-c",
        "import sys; from robotics_runtime_contracts.cli import main; sys.exit(main())",
        "validate-qualification",
        "--schema-version",
        "qualification-bundle.v1",
    ]
    command.extend(value for specification in specs for value in ("--artifact", specification))
    completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=30)
    assert completed.returncode != 0
    assert (
        "requires qualification-bundle.v2 archive reassessment"
        in completed.stdout + completed.stderr
    )
    assert "KeyError" not in completed.stdout + completed.stderr


def test_why_cli_reads_v3_incomplete_without_execution(tmp_path: Path) -> None:
    from robotics_acceptance_harness.diagnostics import why_report

    _pair(tmp_path, oci=True, result_version="acceptance-result.v3", marked=True)
    path = tmp_path / "new-result-primary.json"
    before = path.read_bytes()
    report = why_report(path)
    assert report["status"] == "incomplete"
    assert "$.assertions.org.example.check.first" in report["unevaluated"]
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment["PATH"]
    completed = subprocess.run(
        ["robotics-acceptance", "why", str(path)],
        capture_output=True,
        text=True,
        env=environment,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == report
    assert path.read_bytes() == before
