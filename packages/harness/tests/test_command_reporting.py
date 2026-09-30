from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import pytest

from robotics_acceptance_harness.cli import main
from robotics_acceptance_harness.command_reporting import command_reporting, configure_command
from robotics_acceptance_harness.diagnostics import write_command_diagnostic
from robotics_acceptance_harness.errors import HarnessError

_OBSERVATION = [
    "--scenario",
    "MISSING",
    "--runtime",
    "MISSING",
    "--run-id",
    "run-fixture",
    "--domain-id",
    "primary",
    "--run-context",
    "MISSING",
    "--evidence-index",
    "MISSING",
    "--otel-metrics",
    "MISSING",
    "--output",
    "OUTPUT",
]
_ERROR_COMMANDS = [
    (
        "create-run",
        [
            "--scenario",
            "MISSING",
            "--output",
            "OUTPUT",
            "--domain",
            "primary=observer",
            "--time-authority",
            "sim_clock",
            "--time-source",
            "clock",
        ],
    ),
    ("explain", ["--scenario", "MISSING", "--runtime", "MISSING"]),
    ("verify", [*_OBSERVATION, "--measurement-complete", "OUTPUT"]),
    ("evaluate", [*_OBSERVATION, "--window-start-ns", "0", "--window-end-ns", "1"]),
    (
        "aggregate",
        [
            "--scenario",
            "MISSING",
            "--run-context",
            "MISSING",
            "--result",
            "MISSING",
            "--output",
            "OUTPUT",
        ],
    ),
    (
        "transport-evaluate",
        [
            "--run-id",
            "run-fixture",
            "--scenario",
            "MISSING",
            "--causal-chain",
            "MISSING",
            "--channel-contract",
            "MISSING",
            "--trace",
            "primary=MISSING",
            "--evidence-index",
            "primary=MISSING",
            "--observation-output",
            "OUTPUT",
            "--output",
            "OUTPUT",
        ],
    ),
    (
        "campaign",
        [
            "--scenario",
            "MISSING",
            "--run-context",
            "MISSING",
            "--aggregate",
            "MISSING",
            "--minimum-passed-runs",
            "1",
            "--output",
            "OUTPUT",
        ],
    ),
    ("doctor", ["--scenario", "MISSING"]),
    ("why", ["MISSING"]),
    (
        "timing-check",
        [
            "--scenario",
            "MISSING",
            "--run-context",
            "MISSING",
            "--run-id",
            "run-fixture",
            "--domain-id",
            "primary",
            "--evidence-index",
            "MISSING",
            "--otel-metrics",
            "MISSING",
        ],
    ),
    ("otel-summary", ["--otel-metrics", "MISSING"]),
]


@pytest.mark.parametrize(("command", "arguments"), _ERROR_COMMANDS)
def test_every_command_writes_input_error_diagnostics(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], command: str, arguments: list[str]
) -> None:
    diagnostic = tmp_path / "diagnostic.json"
    args = [
        value.replace("MISSING", str(tmp_path / "missing.json")).replace(
            "OUTPUT", str(tmp_path / "output")
        )
        for value in arguments
    ]
    assert main([command, *args, "--diagnostic-output", str(diagnostic)]) == 2
    report = json.loads(diagnostic.read_text(encoding="utf-8"))
    assert report["command"] == command and report["status"] == "error"
    assert report["error_id"] and report["exception_type"] and report["message"]
    streams = capsys.readouterr()
    assert streams.out == "" and "Traceback" not in streams.err


@pytest.mark.parametrize("passed", [True, False])
def test_completion_report_preserves_the_command_exit_code(tmp_path: Path, passed: bool) -> None:
    diagnostic = tmp_path / "diagnostic.json"
    args = ["doctor"] if passed else ["doctor", "--evidence-dir", str(tmp_path / "absent")]
    assert main([*args, "--diagnostic-output", str(diagnostic)]) == (0 if passed else 1)
    assert json.loads(diagnostic.read_text(encoding="utf-8")) == {
        "command": "doctor",
        "status": "completed",
        "exit_code": 0 if passed else 1,
    }


@pytest.mark.parametrize("log_level", ["WARNING", "ERROR"])
def test_warning_capture_is_bounded_and_independent_of_console_level(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    log_level: str,
) -> None:
    logger = logging.getLogger("robotics_acceptance_harness.test")

    def report(**_kwargs: object) -> dict[str, Any]:
        for _ in range(3):
            logger.warning("same warning", extra={"diagnostic_id": "test.repeated"})
        for index in range(105):
            logger.warning("different warning %d", index, extra={"diagnostic_id": "test.distinct"})
        return {"status": "passed", "checks": []}

    monkeypatch.setattr("robotics_acceptance_harness.cli.doctor_report", report)
    diagnostic = tmp_path / "diagnostic.json"
    assert main(["doctor", "--diagnostic-output", str(diagnostic), "--log-level", log_level]) == 0
    payload = json.loads(diagnostic.read_text(encoding="utf-8"))
    assert len(payload["warnings"]) == 100 and payload["omitted_warnings"] == 6
    assert payload["warnings"][0]["occurrences"] == 3
    streams = capsys.readouterr()
    assert json.loads(streams.out)["status"] == "passed"
    assert streams.err.count("same warning") == (1 if log_level == "WARNING" else 0)


def test_warning_context_survives_a_later_command_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def report(**_kwargs: object) -> None:
        logging.getLogger("robotics_acceptance_harness.test").warning(
            "discarded unsupported attribute",
            extra={
                "diagnostic_id": "otlp.unsupported_attribute",
                "source_path": "metrics.jsonl",
                "line_number": 3,
                "attribute_key": "tags",
                "otlp_type": "array_value",
                "unrelated": "not included",
            },
        )
        raise ValueError("invalid later sample")

    monkeypatch.setattr("robotics_acceptance_harness.cli.doctor_report", report)
    diagnostic = tmp_path / "diagnostic.json"
    assert main(["doctor", "--diagnostic-output", str(diagnostic)]) == 2
    payload = json.loads(diagnostic.read_text(encoding="utf-8"))
    assert payload["message"] == "invalid later sample" and payload["error_id"] == "input.invalid"
    (warning,) = payload["warnings"]
    assert warning["line_number"] == 3 and warning["source_path"] == "metrics.jsonl"
    assert warning["attribute_key"] == "tags" and warning["otlp_type"] == "array_value"
    assert "unrelated" not in warning


def test_logging_configuration_is_restored_after_success_and_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    logger = logging.getLogger("robotics_acceptance_harness")
    previous = (logger.level, logger.propagate, list(logger.handlers))
    assert main(["doctor", "--log-level", "INFO"]) == 0
    assert "command doctor started" in capsys.readouterr().err
    assert (logger.level, logger.propagate, logger.handlers) == previous

    def interrupted(**_kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("robotics_acceptance_harness.cli.doctor_report", interrupted)
    diagnostic = tmp_path / "interrupted.json"
    with pytest.raises(KeyboardInterrupt):
        main(["doctor", "--diagnostic-output", str(diagnostic)])
    assert not diagnostic.exists()
    assert (logger.level, logger.propagate, logger.handlers) == previous


def test_completed_command_reports_a_diagnostic_write_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["doctor", "--diagnostic-output", str(tmp_path)]) == 2
    streams = capsys.readouterr()
    assert json.loads(streams.out)["status"] == "passed"
    assert "cannot write diagnostic" in streams.err
    assert list(tmp_path.iterdir()) == []


def test_failed_atomic_report_replacement_preserves_the_previous_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "report.json"
    destination.write_bytes(b"previous report\n")

    def fail_replace(_source: object, _destination: object) -> None:
        raise OSError("replacement failed")

    monkeypatch.setattr("robotics_acceptance_harness.diagnostics.os.replace", fail_replace)
    with pytest.raises(OSError, match="replacement failed"):
        write_command_diagnostic(destination, {"status": "completed"})
    assert destination.read_bytes() == b"previous report\n"
    assert list(tmp_path.iterdir()) == [destination]


def test_existing_console_handlers_are_scoped_out_and_restored(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    logger = logging.getLogger("robotics_acceptance_harness")
    handler = logging.StreamHandler(sys.stdout)
    monkeypatch.setattr(logger, "handlers", [handler])
    monkeypatch.setattr(logger, "level", logging.ERROR)
    monkeypatch.setattr(logger, "propagate", True)
    monkeypatch.setattr(logger, "disabled", True)

    try:
        assert main(["doctor", "--log-level", "INFO"]) == 0
        streams = capsys.readouterr()
        assert json.loads(streams.out)["status"] == "passed"
        assert "command doctor started" in streams.err
        assert (logger.level, logger.propagate, logger.disabled, logger.handlers) == (
            logging.ERROR,
            True,
            True,
            [handler],
        )
    finally:
        handler.close()


def test_warning_console_text_is_bounded_without_tracebacks_or_mutating_the_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    original = logging.LogRecord(
        "robotics_acceptance_harness.test",
        logging.WARNING,
        __file__,
        1,
        "%s",
        ("x" * 10_000 + "private-tail",),
        None,
    )
    original.__dict__.update(
        diagnostic_id="test.bounded",
        attribute_key="k" * 10_000,
        exc_text="private-traceback",
        stack_info="private-stack",
        payload="private-extra",
    )

    def report(**_kwargs: object) -> dict[str, Any]:
        logging.getLogger(original.name).handle(original)
        return {"status": "passed", "checks": []}

    monkeypatch.setattr("robotics_acceptance_harness.cli.doctor_report", report)
    destination = tmp_path / "bounded.json"
    assert main(["doctor", "--diagnostic-output", str(destination)]) == 0
    streams = capsys.readouterr()
    assert json.loads(streams.out)["status"] == "passed"
    assert len(streams.err) < 4200 and "private-" not in streams.err
    warning = json.loads(destination.read_text(encoding="utf-8"))["warnings"][0]
    assert len(warning["message"]) == 4096 and len(warning["attribute_key"]) == 4096
    assert "private-" not in json.dumps(warning)
    assert original.args == ("x" * 10_000 + "private-tail",)
    assert original.exc_text == "private-traceback" and original.stack_info == "private-stack"


def test_nested_invocations_restore_the_outer_report_and_logger_context(tmp_path: Path) -> None:
    logger = logging.getLogger("robotics_acceptance_harness")
    previous = (logger.level, logger.propagate, logger.disabled, list(logger.handlers))
    outer_path, inner_path = tmp_path / "outer.json", tmp_path / "inner.json"

    @command_reporting
    def outer() -> int:
        configure_command("outer", str(outer_path), "WARNING")
        handlers = list(logger.handlers)
        logger.warning("outer before", extra={"diagnostic_id": "test.outer-before"})
        assert main(["doctor", "--diagnostic-output", str(inner_path)]) == 0
        assert logger.handlers == handlers
        logger.warning("outer after", extra={"diagnostic_id": "test.outer-after"})
        return 0

    assert outer() == 0
    assert [item["diagnostic_id"] for item in json.loads(outer_path.read_text())["warnings"]] == [
        "test.outer-before",
        "test.outer-after",
    ]
    assert "warnings" not in json.loads(inner_path.read_text())
    assert (logger.level, logger.propagate, logger.disabled, logger.handlers) == previous
    assert main(["doctor", "--diagnostic-output", str(inner_path)]) == 0
    assert "warnings" not in json.loads(inner_path.read_text())


@pytest.mark.parametrize("operation", ("fsync", "chmod", "replace"))
def test_atomic_report_io_failures_leave_previous_bytes_and_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    destination = tmp_path / "report.json"
    destination.write_bytes(b"previous\n")

    def fail(*_args: object) -> None:
        raise OSError(f"{operation} failed")

    monkeypatch.setattr(f"robotics_acceptance_harness.diagnostics.os.{operation}", fail)
    with pytest.raises(OSError, match=f"{operation} failed"):
        write_command_diagnostic(destination, {"status": "completed", "exit_code": 0})
    assert destination.read_bytes() == b"previous\n"
    assert list(tmp_path.iterdir()) == [destination]


def test_report_serialization_failure_preserves_existing_file(tmp_path: Path) -> None:
    destination = tmp_path / "report.json"
    destination.write_bytes(b"previous\n")
    with pytest.raises(ValueError):
        write_command_diagnostic(destination, {"invalid": float("nan")})
    assert destination.read_bytes() == b"previous\n"
    assert list(tmp_path.iterdir()) == [destination]


def test_atomic_report_replacement_exposes_only_complete_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    destination = tmp_path / "nested" / "report.json"
    destination.parent.mkdir()
    destination.write_bytes(b"previous\n")
    replace = os.replace
    expected = {"status": "completed", "exit_code": 0, "warnings": []}

    def inspect_then_replace(source: Path, target: Path) -> None:
        assert source.parent == destination.parent and target == destination
        assert destination.read_bytes() == b"previous\n"
        assert json.loads(source.read_text(encoding="utf-8")) == expected
        replace(source, target)

    monkeypatch.setattr("robotics_acceptance_harness.diagnostics.os.replace", inspect_then_replace)
    assert write_command_diagnostic(destination, expected) == destination
    assert json.loads(destination.read_text(encoding="utf-8")) == expected
    assert list(destination.parent.iterdir()) == [destination]


def test_diagnostic_write_failure_does_not_replace_a_primary_custom_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class CustomFailure(HarnessError):
        error_id = "test.failure"
        exit_code = 7

    def fail(**_kwargs: object) -> None:
        raise CustomFailure("primary")

    monkeypatch.setattr("robotics_acceptance_harness.cli.doctor_report", fail)
    assert main(["doctor", "--diagnostic-output", str(tmp_path)]) == 7


def test_diagnostic_write_failure_is_an_error_after_a_completed_failed_verdict(
    tmp_path: Path,
) -> None:
    assert (
        main(
            [
                "doctor",
                "--evidence-dir",
                str(tmp_path / "absent"),
                "--diagnostic-output",
                str(tmp_path),
            ]
        )
        == 2
    )
