from __future__ import annotations

import json
from pathlib import Path

import pytest
from robotics_runtime_contracts import ContractError

from robotics_acceptance_harness import HarnessError, HarnessInputError
from robotics_acceptance_harness._evidence_files import EvidenceReadError
from robotics_acceptance_harness.cli import main
from robotics_acceptance_harness.documents import BundleValidationError
from robotics_acceptance_harness.errors import command_error_boundary
from robotics_acceptance_harness.evidence import EvidenceValidationError
from robotics_acceptance_harness.readiness import GraphReadinessTimeout, ReadinessIssue
from robotics_acceptance_harness.receipts import ReceiptValidationError
from robotics_acceptance_harness.timing import evaluate_timing


@pytest.mark.parametrize("error", [KeyError("foreign domain"), AttributeError("missing API")])
def test_unexpected_command_errors_are_diagnostic_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    def fail(**_kwargs: object) -> None:
        raise error

    monkeypatch.setattr("robotics_acceptance_harness.cli.doctor_report", fail)
    diagnostic = tmp_path / "diagnostic.json"

    assert main(["doctor", "--diagnostic-output", str(diagnostic)]) == 2

    output = capsys.readouterr()
    assert output.out == ""
    assert str(error) in output.err
    assert "internal.error" in output.err
    assert "Traceback" not in output.err
    assert json.loads(diagnostic.read_text(encoding="utf-8")) == {
        "command": "doctor",
        "status": "error",
        "error_id": "internal.error",
        "exception_type": type(error).__name__,
        "message": str(error),
    }


def test_diagnostic_write_failure_preserves_original_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(**_kwargs: object) -> None:
        raise KeyError("original failure")

    monkeypatch.setattr("robotics_acceptance_harness.cli.doctor_report", fail)

    assert main(["doctor", "--diagnostic-output", str(tmp_path)]) == 2

    output = capsys.readouterr()
    assert output.out == ""
    assert "original failure" in output.err
    assert "cannot write diagnostic" in output.err
    assert "Traceback" not in output.err


def test_malformed_otlp_can_write_a_diagnostic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "bad.otlp.jsonl"
    source.write_text('{"unknownField": true}\n', encoding="utf-8")
    diagnostic = tmp_path / "diagnostic.json"

    assert (
        main(
            [
                "otel-summary",
                "--otel-metrics",
                str(source),
                "--diagnostic-output",
                str(diagnostic),
            ]
        )
        == 2
    )

    report = json.loads(diagnostic.read_text(encoding="utf-8"))
    assert report["error_id"] == "MetricInputError.failed"
    assert "bad.otlp.jsonl:1:" in report["message"]
    assert "Traceback" not in capsys.readouterr().err


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(7)])
def test_process_control_exceptions_propagate(
    monkeypatch: pytest.MonkeyPatch, error: BaseException
) -> None:
    def fail(**_kwargs: object) -> None:
        raise error

    monkeypatch.setattr("robotics_acceptance_harness.cli.doctor_report", fail)

    with pytest.raises(type(error)) as caught:
        main(["doctor"])
    assert caught.value is error


@pytest.mark.parametrize(
    ("error", "error_id", "issues"),
    [
        (
            BundleValidationError(
                "$.execution.time_mode",
                "mode differs",
                related=(("$.provider_bindings", "missing controller"),),
            ),
            "BundleValidationError.failed",
            [
                {"json_path": "$.execution.time_mode", "message": "mode differs"},
                {"json_path": "$.provider_bindings", "message": "missing controller"},
            ],
        ),
        (
            GraphReadinessTimeout(
                (ReadinessIssue("$.expected_ros_graph.topics[0]", "no publisher"),)
            ),
            "GraphReadinessTimeout.failed",
            [{"json_path": "$.expected_ros_graph.topics[0]", "message": "no publisher"}],
        ),
        (
            EvidenceReadError("file escaped root", field="$.artifacts[0].path"),
            "EvidenceReadError.failed",
            [{"json_path": "$.artifacts[0].path", "message": "file escaped root"}],
        ),
        (
            ContractError("unknown role", error_id="role.invalid", json_path="$.role"),
            "role.invalid",
            [{"json_path": "$.role", "message": "unknown role"}],
        ),
        (HarnessInputError("invalid window"), "input.invalid", []),
        (ValueError("invalid dependency value"), "input.invalid", []),
        (OSError("unreadable evidence"), "input.io_error", []),
        (RuntimeError("dependency crashed"), "internal.error", []),
        (
            ReceiptValidationError("$.run_id", "receipt belongs to another run"),
            "ReceiptValidationError.failed",
            [{"json_path": "$.run_id", "message": "receipt belongs to another run"}],
        ),
        (
            EvidenceValidationError("$.artifacts[0].sha256", "digest mismatch"),
            "EvidenceValidationError.failed",
            [{"json_path": "$.artifacts[0].sha256", "message": "digest mismatch"}],
        ),
    ],
)
def test_command_diagnostics_preserve_failure_identity_and_issue_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    error_id: str,
    issues: list[dict[str, str]],
) -> None:
    def fail(**_kwargs: object) -> None:
        raise error

    monkeypatch.setattr("robotics_acceptance_harness.cli.doctor_report", fail)
    diagnostic = tmp_path / "diagnostic.json"

    assert main(["doctor", "--diagnostic-output", str(diagnostic)]) == 2

    report = json.loads(diagnostic.read_text(encoding="utf-8"))
    assert report["error_id"] == error_id
    assert report["exception_type"] == type(error).__name__
    assert report["message"] == str(error)
    assert report.get("issues", []) == issues


def test_dependency_translation_preserves_cause_for_library_callers() -> None:
    original = ContractError("invalid hash", error_id="digest.invalid", json_path="$.sha256")

    with pytest.raises(HarnessError) as caught, command_error_boundary():
        raise original

    assert caught.value.__cause__ is original
    assert caught.value.diagnostic_exception is original
    assert caught.value.error_id == "digest.invalid"
    assert caught.value.diagnostic_issues == (("$.sha256", "invalid hash"),)


def test_missing_clock_diagnostic_retains_timing_issues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(**_kwargs: object) -> None:
        evaluate_timing({"time_mode": "simulation_stepped"}, {}, ())

    monkeypatch.setattr("robotics_acceptance_harness.cli.doctor_report", fail)
    diagnostic = tmp_path / "diagnostic.json"

    assert main(["doctor", "--diagnostic-output", str(diagnostic)]) == 2

    report = json.loads(diagnostic.read_text(encoding="utf-8"))
    assert report["exception_type"] == "TimingValidationError"
    assert report["error_id"] == "TimingValidationError.failed"
    assert report["issues"] == [{"json_path": "$.time_policy", "message": "no clock samples"}]


def test_modeled_timeout_remains_catchable_with_legacy_and_common_bases() -> None:
    original = GraphReadinessTimeout((ReadinessIssue("$.graph", "not ready"),))

    with pytest.raises(TimeoutError) as caught, command_error_boundary():
        raise original

    assert caught.value is original
    assert isinstance(caught.value, HarnessError)
    assert caught.value.__cause__ is None
