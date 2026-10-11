from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, cast

import pytest
from robotics_runtime_contracts.serialization import MAX_DOCUMENT_BYTES

from robotics_acceptance_harness import archive
from robotics_acceptance_harness.archive import AssessmentControls, load_assessment_controls
from robotics_acceptance_harness.documents import BundleValidationError
from robotics_acceptance_harness.evidence import EvidenceValidationError
from tests.test_native import evaluate, produce


def controls() -> dict[str, Any]:
    return {
        "metric_definitions": [],
        "assertions": [],
        "evaluator_requirements": [],
        "evidence_policy": {
            "max_artifact_size_bytes": 1024,
            "max_archive_size_bytes": 4096,
            "max_upload_lag_sec": 0,
            "upload_mode": "local_only",
            "retention_class": "qualification",
            "remote_sink_allowed": False,
        },
        "calibration": {"state": "not_applicable", "reason": "raw software count"},
    }


def selected(path: Path, payload: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    configuration = controls()
    reference = {
        "uri": payload.as_uri(),
        "sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
        "size_bytes": payload.stat().st_size,
        "media_type": "application/json",
    }
    configuration["calibration"] = {"state": "selected", "artifacts": [reference]}
    configuration["evaluator_requirements"] = [
        {
            "namespace": "org.example.calibrated",
            "entry_point": "org.example.calibrated",
            "distribution": "calibrated-example",
            "version": "1",
            "artifact_sha256": "a" * 64,
            "receipt_sha256": "b" * 64,
        }
    ]
    path.write_text(json.dumps(configuration), encoding="utf-8")
    return configuration, reference


def test_controls_and_declared_calibration_are_immutable_captures(tmp_path: Path) -> None:
    payload = tmp_path / "calibration.json"
    original = b'{"offset":7}\n'
    payload.write_bytes(original)
    path = tmp_path / "method.json"
    configuration, reference = selected(path, payload)
    captured = load_assessment_controls(path)
    original_controls = path.read_bytes()
    assert captured.sha256 == hashlib.sha256(original_controls).hexdigest()
    path.write_text("{}")
    payload.write_bytes(b'{"offset":9}\n')
    assert captured.raw == original_controls
    assert captured.as_dict() == configuration
    assert captured.read_input(reference) == original
    with pytest.raises(TypeError):
        captured.data["calibration"]["state"] = "not_applicable"
    path.write_bytes(original_controls)
    with pytest.raises(EvidenceValidationError, match="expected"):
        load_assessment_controls(path)


def test_new_method_controls_do_not_infer_calibration_from_absence(tmp_path: Path) -> None:
    configuration = controls()
    configuration.pop("calibration")
    path = tmp_path / "method.json"
    path.write_text(json.dumps(configuration))
    with pytest.raises(BundleValidationError, match="require a declaration"):
        load_assessment_controls(path)


def test_core_metric_method_cannot_claim_selected_calibration(tmp_path: Path) -> None:
    payload = tmp_path / "calibration.json"
    payload.write_bytes(b"{}")
    path = tmp_path / "method.json"
    configuration, _ = selected(path, payload)
    configuration["evaluator_requirements"] = []
    path.write_text(json.dumps(configuration))
    with pytest.raises(BundleValidationError, match="core metrics cannot apply"):
        load_assessment_controls(path)


def test_method_cannot_capture_an_undeclared_or_wrong_size_input(tmp_path: Path) -> None:
    payload = tmp_path / "calibration.json"
    payload.write_bytes(b"{}")
    path = tmp_path / "method.json"
    _, reference = selected(path, payload)
    captured = load_assessment_controls(path)
    with pytest.raises(BundleValidationError, match="not a captured"):
        captured.read_input({**reference, "sha256": "c" * 64})
    with pytest.raises(BundleValidationError, match="not a captured"):
        captured.read_input({**reference, "size_bytes": 9})


def test_calibration_path_cannot_escape_controls_directory(tmp_path: Path) -> None:
    root = tmp_path / "controls"
    root.mkdir()
    payload = tmp_path / "outside.json"
    payload.write_bytes(b"{}")
    path = root / "method.json"
    selected(path, payload)
    with pytest.raises(EvidenceValidationError, match="outside"):
        load_assessment_controls(path)


def test_explicit_new_method_executes_changed_criteria_without_rewriting_trial(
    tmp_path: Path,
) -> None:
    inputs = produce(tmp_path / "archive", "--error", "7")
    root = Path(inputs["evidence_index"]).parent
    original_bytes = {path: path.read_bytes() for path in root.iterdir() if path.is_file()}
    initial_output = tmp_path / "original"
    original = evaluate(inputs, initial_output)
    assert original.returncode == 1, original.stderr
    original_result = json.loads((initial_output / "acceptance-result.json").read_bytes())
    assert original_result["status"] == "failed"
    configuration = json.loads(Path(inputs["scenario"]).read_bytes())
    selected_controls = {
        key: configuration[key]
        for key in ("metric_definitions", "assertions", "evaluator_requirements", "evidence_policy")
    }
    selected_controls["calibration"] = {
        "state": "not_applicable",
        "reason": "raw software count has no calibration",
    }
    for assertion in selected_controls["assertions"]:
        if assertion["assertion_id"] == "counter-error":
            assertion["operator"] = "lte"
            assertion["threshold"] = 10
    method_path = tmp_path / "method.json"
    method_bytes = (json.dumps(selected_controls, indent=4) + "\n").encode()
    method_path.write_bytes(method_bytes)
    assessed_output = tmp_path / "new-method"
    baseline_path = initial_output / "acceptance-result.json"
    baseline_raw = baseline_path.read_bytes()
    completed = evaluate(
        {**inputs, "assessment_controls": method_path, "original_result": baseline_path},
        assessed_output,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads((assessed_output / "acceptance-result.json").read_bytes())
    assert result["status"] == "passed"
    assert result["result_id"] != original_result["result_id"]
    assert result["scenario_sha256"] == original_result["scenario_sha256"]
    assert result["original_execution"] == {
        **original_result["original_execution"],
        "original_result_sha256": hashlib.sha256(baseline_raw).hexdigest(),
    }
    assert baseline_path.read_bytes() == baseline_raw
    criterion = next(
        item for item in result["assertion_results"] if item["assertion_id"] == "counter-error"
    )
    assert criterion["observed_value"] == 7 and criterion["status"] == "passed"
    original_criterion = next(
        item
        for item in original_result["assertion_results"]
        if item["assertion_id"] == "counter-error"
    )
    assert original_criterion["observed_value"] == 7 and original_criterion["status"] == "failed"
    assert (
        result["evaluation"]["method"]["configuration"]["sha256"]
        == hashlib.sha256(method_bytes).hexdigest()
    )
    assert (assessed_output / "evaluation-method.json").read_bytes() == method_bytes
    coverage = result["evaluation"]["coverage"]["covered_assertions"]
    assert {item["assertion_id"] for item in coverage} == {
        "counter-error",
        "counter-accepted",
        "counter-finished",
    }
    metrics_digest = hashlib.sha256(Path(inputs["otel_metrics"]).read_bytes()).hexdigest()
    assert all(item["evidence_sha256"] == [metrics_digest] for item in coverage)
    assert {path: path.read_bytes() for path in original_bytes} == original_bytes

    forged = json.loads(baseline_raw)
    forged["original_execution"]["observation_sha256"] = "a" * 64
    forged_path = tmp_path / "foreign-original.json"
    forged_path.write_text(json.dumps(forged))
    refused = tmp_path / "refused-source"
    failure = evaluate(
        {**inputs, "assessment_controls": method_path, "original_result": forged_path},
        refused,
    )
    assert failure.returncode == 2
    assert "differs from original execution" in failure.stderr
    assert not (refused / "acceptance-result.json").exists()
    failure = evaluate({**inputs, "original_result": baseline_path}, tmp_path / "no-controls")
    assert failure.returncode == 2 and "requires --assessment-controls" in failure.stderr


@pytest.mark.parametrize("mutable", [bytearray, memoryview])
def test_constructor_refuses_mutable_control_buffers(tmp_path: Path, mutable: Any) -> None:
    raw = json.dumps(controls()).encode()
    with pytest.raises(BundleValidationError, match="immutable bytes"):
        AssessmentControls(tmp_path / "method.json", cast(bytes, mutable(raw)), {})


@pytest.mark.parametrize("mutable", [bytearray, memoryview])
def test_constructor_refuses_mutable_calibration_buffers(tmp_path: Path, mutable: Any) -> None:
    payload = tmp_path / "calibration.json"
    payload.write_bytes(b'{"offset":7}')
    path = tmp_path / "method.json"
    _, reference = selected(path, payload)
    with pytest.raises(BundleValidationError, match="immutable bytes"):
        AssessmentControls(
            path,
            path.read_bytes(),
            {reference["sha256"]: cast(bytes, mutable(payload.read_bytes()))},
        )


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="requires POSIX FIFO")
def test_controls_fifo_is_refused_without_waiting_for_a_writer(tmp_path: Path) -> None:
    path = tmp_path / "method.json"
    os.mkfifo(path)
    with pytest.raises(BundleValidationError, match="regular file"):
        load_assessment_controls(path)


@pytest.mark.parametrize("sizes", [[MAX_DOCUMENT_BYTES + 1], [MAX_DOCUMENT_BYTES // 2] * 2])
def test_declared_capture_caps_are_checked_before_input_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sizes: list[int]
) -> None:
    payload = tmp_path / "calibration.json"
    payload.write_bytes(b"{}")
    path = tmp_path / "method.json"
    configuration, reference = selected(path, payload)
    configuration["calibration"]["artifacts"] = [
        {**reference, "sha256": str(index) * 64, "size_bytes": size}
        for index, size in enumerate(sizes, 1)
    ]
    path.write_text(json.dumps(configuration))

    def unexpected_read(*args: Any, **kwargs: Any) -> bytes:
        raise AssertionError("capture began before the budget was refused")

    monkeypatch.setattr(archive, "_read_local", unexpected_read)
    with pytest.raises(BundleValidationError, match="byte limit"):
        load_assessment_controls(path)


def test_constructor_enforces_total_capture_limit(tmp_path: Path) -> None:
    payload = b"x" * (MAX_DOCUMENT_BYTES + 1)
    with pytest.raises(BundleValidationError, match="total byte limit"):
        AssessmentControls(
            tmp_path / "method.json", json.dumps(controls()).encode(), {"x": payload}
        )
