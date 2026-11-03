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


def test_public_qualification_cli_validates_oci_document_relationships(tmp_path: Path) -> None:
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
    assert completed.returncode == 0, completed.stderr
    assert "valid: qualification artifact set" in completed.stdout


@pytest.mark.parametrize("requirements", [[], [OCI]])
def test_harness_requires_original_result_for_versioned_controls(
    tmp_path: Path, requirements: list[dict[str, Any]]
) -> None:
    method = controls()
    method["schema_version"] = "assessment-controls.v1"
    method["evaluator_requirements"] = deepcopy(requirements)
    path = tmp_path / "method.json"
    path.write_text(json.dumps(method))
    selected = load_assessment_controls(path)
    context: Any = SimpleNamespace(method_controls=selected.data, original_result=None)
    with pytest.raises(EvaluationError, match="require an original v2 result"):
        evaluate_native(context, cast(Any, None), tmp_path / "result", None)
    assert not (tmp_path / "result").exists()


def test_default_wheel_inventory_refuses_oci() -> None:
    with pytest.raises(EvaluationError, match="OCI evaluator execution is not supported"):
        evaluator_inventory([OCI])


def test_harness_cli_refuses_missing_oci_profile_without_loading_wheels(
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
    assert "invalid OCI operator profile" in completed.stderr
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


def _request_context_and_profile(tmp_path: Path) -> tuple[Any, Any, Any]:
    from robotics_acceptance_harness._oci_operator import load_oci_profile
    from tests.test_oci_operator import fixture, write
    from tests.test_oci_request import setup_request

    source = tmp_path / "source"
    source.mkdir()
    context, documents, _ = setup_request(source)
    from dataclasses import replace

    assert context.assessment_controls is not None
    selected_path = source / "selected-controls.json"
    selected = context.assessment_controls.as_dict()
    selected["evaluator_requirements"][0]["expected_assertion_ids"].append(
        "org.example.check.second"
    )
    calibration_path = source / "calibration.json"
    calibration_path.write_bytes(b'{"offset":7}')
    selected["calibration"]["artifacts"] = [_reference(calibration_path)]
    _write(selected_path, selected)
    context = replace(context, assessment_controls=load_assessment_controls(selected_path))
    operator_dir = tmp_path / "operator"
    operator_dir.mkdir()
    profile_path, data, _ = fixture(operator_dir)
    binding = data["evaluators"][0]
    binding["namespace"] = OCI["namespace"]
    binding["manifest_sha256"] = DIGEST
    binding["image_ref"] = "localhost/evaluator@sha256:" + DIGEST
    write(profile_path, data)
    assert context.assessment_controls is not None
    profile = load_oci_profile(
        profile_path,
        context.assessment_controls.data["evaluator_requirements"],
        evidence_root=source,
    )
    return context, documents, profile


def test_oci_parent_uses_connected_owner_and_decodes_verified_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hashlib import sha256

    from robotics_runtime_contracts import dumps_canonical

    from robotics_acceptance_harness import native
    from robotics_acceptance_harness.archive import _assess_oci_archive

    context, documents, profile = _request_context_and_profile(tmp_path)
    observed: list[str] = []

    def owner(policy: Any, namespace: str, packet: bytes, inputs: Path, attempt: Path) -> bytes:
        assert policy is profile and namespace == OCI["namespace"]
        assert inputs == attempt / "inputs"
        assert (inputs / "request.json").read_bytes() == packet
        request = json.loads(packet)
        assert (
            request["method"]["implementation"] == "robotics_acceptance_harness.evaluate_acceptance"
        )
        assert request["method"]["configuration"]["sha256"] == context.assessment_controls.sha256
        digest = str(context.evidence.links[0]["sha256"])
        calibration = str(context.assessment_controls.data["calibration"]["artifacts"][0]["sha256"])
        (attempt / "config.json").write_bytes(
            Path(policy.evaluators[namespace]["config"]).read_bytes()
        )
        (attempt / "manifest.json").write_bytes(
            Path(policy.evaluators[namespace]["manifest"]).read_bytes()
        )
        (attempt / "signature-audit.bin").write_bytes(b"synthetic audit")
        (attempt / "journal.json").write_bytes(b'{"phase":"settled"}')
        observed.append(namespace)
        response = dumps_canonical(
            {
                "schema_version": "evaluator-response.v1",
                "request_sha256": sha256(packet).hexdigest(),
                "assertion_results": [
                    {
                        "assertion_id": identifier,
                        "source": "product",
                        "namespace": namespace,
                        "status": "passed",
                        "observed_value": 1,
                        "unit": "1",
                        "evidence_sha256": [digest, calibration],
                    }
                    for identifier in request["expected_assertion_ids"]
                ],
            }
        )
        (attempt / "response.bin").write_bytes(response)
        return response

    monkeypatch.setattr(native, "run_oci_evaluator", owner)
    outputs = _assess_oci_archive(
        context, documents["acceptance_run"], tmp_path / "out", None, profile
    )
    assert observed == [OCI["namespace"]]
    assert outputs.result["schema_version"] == "acceptance-result.v3"
    assert outputs.result["status"] == "failed"
    product = [item for item in outputs.result["assertion_results"] if item["source"] == "product"]
    assert len(product) == 2 and all(item["status"] == "passed" for item in product)
    assert (
        outputs.result["original_execution"]["original_result_sha256"]
        == context.original_result.sha256
    )
    assert outputs.result_path.is_file() and outputs.junit_path.is_file()
    environment = json.loads((tmp_path / "out" / "evaluation-environment.json").read_bytes())
    binding = environment["oci"]["evaluators"][0]
    config_path = Path(profile.evaluators[OCI["namespace"]]["config"])
    assert binding["config_sha256"] == sha256(config_path.read_bytes()).hexdigest()
    assert environment["oci"]["trusted_root_sha256"] == profile.verifier.trusted_root_sha256
    assert (
        environment["oci"]["containers_conf_sha256"] == profile.engine["containers_conf"]["sha256"]
    )
    assert environment["oci"]["storage_conf_sha256"] == profile.engine["storage_conf"]["sha256"]
    assert "cid" not in environment["oci"] and "cid" not in binding
    _qualify_connected_fixture(tmp_path, outputs)


@pytest.mark.parametrize(
    "failure",
    ["owner", "wrong-digest", "empty-response", "partial", "cal-only", "config-only", "raw-only"],
)
def test_oci_parent_never_writes_verdict_after_owner_or_response_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    from hashlib import sha256

    from robotics_runtime_contracts import dumps_canonical

    from robotics_acceptance_harness import native
    from robotics_acceptance_harness.archive import _assess_oci_archive
    from robotics_acceptance_harness.evaluator_trust import EvaluatorTrustError

    context, documents, profile = _request_context_and_profile(tmp_path)

    def owner(_policy: Any, _namespace: str, packet: bytes, _inputs: Path, _attempt: Path) -> bytes:
        (_attempt / "journal.json").write_bytes(b'{"phase":"unknown"}')
        if failure == "owner":
            raise EvaluatorTrustError("fixture admission refusal")
        (_attempt / "config.json").write_bytes(
            Path(_policy.evaluators[_namespace]["config"]).read_bytes()
        )
        request = json.loads(packet)
        raw_digest = str(context.evidence.links[0]["sha256"])
        calibration_digest = str(
            context.assessment_controls.data["calibration"]["artifacts"][0]["sha256"]
        )
        selected_digest = {
            "cal-only": calibration_digest,
            "config-only": context.assessment_controls.sha256,
            "raw-only": raw_digest,
        }.get(failure, raw_digest)
        identifiers = request["expected_assertion_ids"]
        if failure in {"wrong-digest", "empty-response"}:
            identifiers = []
        elif failure == "partial":
            identifiers = identifiers[:1]
        return dumps_canonical(
            {
                "schema_version": "evaluator-response.v1",
                "request_sha256": (
                    "0" * 64 if failure == "wrong-digest" else sha256(packet).hexdigest()
                ),
                "assertion_results": [
                    {
                        "assertion_id": identifier,
                        "source": "product",
                        "namespace": _namespace,
                        "status": "passed",
                        "observed_value": 1,
                        "unit": "1",
                        "evidence_sha256": [selected_digest],
                    }
                    for identifier in identifiers
                ],
            }
        )

    monkeypatch.setattr(native, "run_oci_evaluator", owner)
    destination = tmp_path / "out"
    with pytest.raises(EvaluationError):
        _assess_oci_archive(context, documents["acceptance_run"], destination, None, profile)
    assert not (destination / "acceptance-result.json").exists()
    assert not (destination / "junit.xml").exists()
    attempts = list(destination.glob("oci-attempt-*"))
    assert len(attempts) == 1 and (attempts[0] / "journal.json").is_file()


def test_versioned_builtin_method_remains_engine_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    from robotics_acceptance_harness import native
    from tests.test_oci_request import setup_request

    context, documents, _ = setup_request(tmp_path)
    method = controls()
    method["schema_version"] = "assessment-controls.v1"
    method_path = tmp_path / "builtin-controls.json"
    method_path.write_text(json.dumps(method))
    context = replace(context, assessment_controls=load_assessment_controls(method_path))

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("builtin-only method must not use the OCI owner")

    monkeypatch.setattr(native, "run_oci_evaluator", forbidden)
    events: list[str] = []
    original_environment = native._evaluation_environment
    native_module: Any = native
    original_evaluate = native_module.evaluate_acceptance

    def capture_environment(*args: Any, **kwargs: Any) -> Any:
        events.append("environment")
        return original_environment(*args, **kwargs)

    def capture_evaluation(*args: Any, **kwargs: Any) -> Any:
        events.append("evaluation")
        return original_evaluate(*args, **kwargs)

    monkeypatch.setattr(native, "_evaluation_environment", capture_environment)
    monkeypatch.setattr(native, "evaluate_acceptance", capture_evaluation)
    result = evaluate_native(context, documents["acceptance_run"], tmp_path / "out", None)
    assert events == ["environment", "evaluation"]
    assert result["schema_version"] == "acceptance-result.v3"
    assert result["evaluators"] == []


def test_missing_oci_rows_preserve_uncovered_without_weakening_calibration(tmp_path: Path) -> None:
    from types import SimpleNamespace

    from robotics_acceptance_harness.evaluation import _validate_calibration_bindings
    from robotics_acceptance_harness.native import _criterion_coverage
    from tests.test_oci_request import setup_request

    context, _, _ = setup_request(tmp_path)
    _validate_calibration_bindings(context, ())
    coverage = _criterion_coverage(context, ())
    assert coverage["covered_assertions"] == []
    assert [item["assertion_id"] for item in coverage["uncovered_assertions"]] == OCI[
        "expected_assertion_ids"
    ]
    invalid: Any = SimpleNamespace(
        assessment_controls=object(),
        method_controls={
            "schema_version": "assessment-controls.v1",
            "calibration": {"state": "selected", "artifacts": [{"sha256": "a" * 64}]},
            "evaluator_requirements": [],
        },
    )
    with pytest.raises(EvaluationError, match="selected calibration has no product"):
        _validate_calibration_bindings(invalid, ())
    invalid.method_controls.pop("schema_version")
    invalid.method_controls["evaluator_requirements"] = [{"namespace": "legacy"}]
    with pytest.raises(EvaluationError, match="selected calibration has no product"):
        _validate_calibration_bindings(invalid, ())


def _qualify_connected_fixture(tmp_path: Path, outputs: Any) -> None:
    from robotics_runtime_contracts.statements import (
        create_qualification_statement,
        validate_qualification_statement,
    )

    from robotics_acceptance_harness.aggregate import aggregate_results

    source = tmp_path / "source"
    out = tmp_path / "out"
    aggregate = aggregate_results(
        scenario_path=source / "scenario.json",
        run_context_path=source / "run.json",
        result_paths=[outputs.result_path],
        output_path=out / "aggregate.json",
    )
    specs = [
        f"scenario:scenario.json={source / 'scenario.json'}",
        f"acceptance_run:acceptance-run.json={source / 'run.json'}",
        f"runtime_manifest:runtime-manifests/primary.json={source / 'runtime-primary.json'}",
        f"acceptance_observation:observations/primary.json={source / 'observation-primary.json'}",
        f"evidence_index:evidence-indexes/primary.json={source / 'index-primary.json'}",
        f"other_evidence:evidence/native-state.json={source / 'native-state.json'}",
        f"other_evidence:assessment/calibration.json={source / 'calibration.json'}",
        f"other_evidence:original/method.json={source / 'method.json'}",
        f"other_evidence:original/environment.json={source / 'environment.json'}",
        f"other_evidence:assessment/method.json={out / 'evaluation-method.json'}",
        f"other_evidence:assessment/environment.json={out / 'evaluation-environment.json'}",
        f"domain_result:original-results/primary.json={source / 'result-primary.json'}",
        f"domain_result:results/primary.json={outputs.result_path}",
        f"acceptance_aggregate:original-aggregate.json={source / 'aggregate.json'}",
        f"acceptance_aggregate:acceptance-aggregate.json={aggregate}",
    ]
    attempt = next(out.glob("oci-attempt-*"))
    for name in (
        "manifest.json",
        "config.json",
        "signature-audit.bin",
        "journal.json",
        "response.bin",
    ):
        specs.append(f"other_evidence:attempt/{name}={attempt / name}")
    statement = create_qualification_statement(
        specs, schema_version="qualification-bundle.v2", comparison_rule="exact_assertion_outcome"
    )
    statement_path = _write(tmp_path / "qualification.json", statement)
    validate_qualification_statement(statement_path, specs)
    assert {
        "attempt/manifest.json",
        "attempt/config.json",
        "attempt/signature-audit.bin",
        "attempt/journal.json",
        "attempt/response.bin",
    } <= {item["name"] for item in statement["subject"]}
    with pytest.raises(ContractError):
        validate_qualification_statement(statement_path, specs[:-1])


def _request_context_with_provenance(
    tmp_path: Path, *, wrong_size: bool = False
) -> tuple[Any, Any, Any, Any]:
    from dataclasses import replace

    from robotics_acceptance_harness.receipts import load_verified_receipts
    from tests.test_archive_qualification import _oci_archive_with_provenance

    context, documents, profile = _request_context_and_profile(tmp_path)
    provenance = tmp_path / "provenance"
    provenance.mkdir()
    _oci_archive_with_provenance(provenance, wrong_size=wrong_size)
    subject = _document(provenance / "new-method.json")["evaluator_requirements"][0][
        "execution_subject"
    ]
    assert context.assessment_controls is not None
    controls_path = context.assessment_controls.path
    method = context.assessment_controls.as_dict()
    method["evaluator_requirements"][0]["execution_subject"] = subject
    _write(controls_path, method)
    context = replace(context, assessment_controls=load_assessment_controls(controls_path))
    binding = dict(profile.evaluators[OCI["namespace"]])
    binding["manifest"] = provenance / "oci-manifest.json"
    binding["manifest_sha256"] = subject["digest"].removeprefix("sha256:")
    profile = replace(profile, evaluators={OCI["namespace"]: binding})
    fixture = (
        Path(__file__).resolve().parents[2] / "contracts/tests/fixtures/qualification/inference"
    )
    receipts = load_verified_receipts(
        receipt_paths=[provenance / "oci-receipt.json"],
        verification_paths=[provenance / "oci-verification.json"],
        dependency_paths=[
            provenance / "oci-statement.json",
            fixture / "evaluator-trust.json",
            fixture / "evaluator-verification.bundle",
        ],
    )
    return context, documents, profile, receipts


def test_oci_provenance_precheck_binds_receipt_to_manifest(tmp_path: Path) -> None:
    from robotics_acceptance_harness.native import _verify_oci_provenance

    context, _, profile, receipts = _request_context_with_provenance(tmp_path)
    _verify_oci_provenance(context.method_controls["evaluator_requirements"], profile, receipts)


@pytest.mark.parametrize("failure", ["missing", "size", "manifest", "extra"])
def test_oci_provenance_refuses_before_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    from robotics_acceptance_harness import native
    from robotics_acceptance_harness.archive import _assess_oci_archive
    from robotics_acceptance_harness.errors import HarnessError

    context, documents, profile, receipts = _request_context_with_provenance(
        tmp_path, wrong_size=failure == "size"
    )
    if failure == "manifest":
        Path(profile.evaluators[OCI["namespace"]]["manifest"]).write_bytes(b"replacement")
    if failure == "missing":
        receipts = None
    if failure == "extra":
        from robotics_acceptance_harness.receipts import VerifiedReceiptSet

        extra = _unreferenced_wheel_receipts()
        receipts = VerifiedReceiptSet({**receipts.by_digest, **extra.by_digest})

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("invalid provenance reached the owner")

    monkeypatch.setattr(native, "run_oci_evaluator", forbidden)
    destination = tmp_path / "output"
    with pytest.raises(HarnessError):
        _assess_oci_archive(context, documents["acceptance_run"], destination, receipts, profile)
    assert not destination.exists()


def test_oci_parent_accepts_valid_documentary_provenance_with_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hashlib import sha256

    from robotics_runtime_contracts import dumps_canonical

    from robotics_acceptance_harness import native
    from robotics_acceptance_harness.archive import _assess_oci_archive

    context, documents, profile, receipts = _request_context_with_provenance(tmp_path)
    seen: list[str] = []

    def owner(policy: Any, namespace: str, packet: bytes, _inputs: Path, attempt: Path) -> bytes:
        seen.append(namespace)
        (attempt / "config.json").write_bytes(
            Path(policy.evaluators[namespace]["config"]).read_bytes()
        )
        request = json.loads(packet)
        original = str(context.evidence.links[0]["sha256"])
        calibration = str(context.assessment_controls.data["calibration"]["artifacts"][0]["sha256"])
        return dumps_canonical(
            {
                "schema_version": "evaluator-response.v1",
                "request_sha256": sha256(packet).hexdigest(),
                "assertion_results": [
                    {
                        "assertion_id": identifier,
                        "source": "product",
                        "namespace": namespace,
                        "status": "passed",
                        "observed_value": 1,
                        "unit": "1",
                        "evidence_sha256": [original, calibration],
                    }
                    for identifier in request["expected_assertion_ids"]
                ],
            }
        )

    monkeypatch.setattr(native, "run_oci_evaluator", owner)
    outputs = _assess_oci_archive(
        context, documents["acceptance_run"], tmp_path / "output", receipts, profile
    )
    assert seen == [OCI["namespace"]]
    assert outputs.result["schema_version"] == "acceptance-result.v3"
    assert outputs.result_path.is_file()


def _unreferenced_wheel_receipts() -> Any:
    from robotics_acceptance_harness.receipts import load_verified_receipts

    fixture = (
        Path(__file__).resolve().parents[2] / "contracts/tests/fixtures/qualification/inference"
    )
    return load_verified_receipts(
        receipt_paths=[fixture / "evaluator-receipt.json"],
        verification_paths=[fixture / "evaluator-verification.json"],
        dependency_paths=[
            fixture / "evaluator-statement.json",
            fixture / "evaluator-trust.json",
            fixture / "evaluator-verification.bundle",
        ],
    )


def test_versioned_builtin_refuses_unreferenced_evaluator_receipt(tmp_path: Path) -> None:
    from dataclasses import replace

    from tests.test_oci_request import setup_request

    context, documents, _ = setup_request(tmp_path)
    method = controls()
    method["schema_version"] = "assessment-controls.v1"
    method_path = tmp_path / "builtin-controls.json"
    method_path.write_text(json.dumps(method))
    context = replace(context, assessment_controls=load_assessment_controls(method_path))
    destination = tmp_path / "out"
    with pytest.raises(EvaluationError, match="receipts must match"):
        evaluate_native(
            context, documents["acceptance_run"], destination, _unreferenced_wheel_receipts()
        )
    assert not destination.exists()


@pytest.mark.parametrize("failure", ["digest", "namespaces"])
def test_oci_parent_refuses_profile_mismatch_without_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    from dataclasses import replace

    from robotics_acceptance_harness import native
    from robotics_acceptance_harness.archive import _assess_oci_archive
    from robotics_acceptance_harness.errors import HarnessError

    context, documents, profile = _request_context_and_profile(tmp_path)
    binding = dict(profile.evaluators[OCI["namespace"]])
    binding["manifest_sha256"] = "f" * 64
    evaluators = {OCI["namespace"]: binding} if failure == "digest" else {}
    profile = replace(profile, evaluators=evaluators)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("mismatched profile reached the owner")

    monkeypatch.setattr(native, "run_oci_evaluator", forbidden)
    destination = tmp_path / "output"
    with pytest.raises(HarnessError, match="manifest differs|evaluator namespaces"):
        _assess_oci_archive(context, documents["acceptance_run"], destination, None, profile)
    assert not destination.exists()
