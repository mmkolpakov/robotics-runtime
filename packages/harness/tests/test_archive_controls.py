from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from robotics_acceptance_harness.archive import load_assessment_controls
from robotics_acceptance_harness.documents import BundleValidationError
from robotics_acceptance_harness.evidence import EvidenceValidationError


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
