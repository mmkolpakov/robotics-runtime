from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, ArrayValue
from opentelemetry.proto.metrics.v1.metrics_pb2 import DataPointFlags

from robotics_acceptance_harness.cli import main

_SECRET = "private-OTLP-attribute-value"
_COMMANDS = (
    "create-run",
    "explain",
    "verify",
    "evaluate",
    "aggregate",
    "transport-evaluate",
    "campaign",
    "doctor",
    "why",
    "timing-check",
    "otel-summary",
)


def _metrics_file(path: Path, count: int = 1) -> Path:
    request = ExportMetricsServiceRequest()
    scope = request.resource_metrics.add().scope_metrics.add()
    for index in range(count):
        metric = scope.metrics.add(name=f"supported.{index}")
        point = metric.gauge.data_points.add(time_unix_nano=100, as_int=0)
        point.attributes.add(key="kept", value=AnyValue(bool_value=False))
        for _ in range(3):
            point.attributes.add(
                key="discarded",
                value=AnyValue(array_value=ArrayValue(values=[AnyValue(string_value=_SECRET)])),
            )
    unsupported = scope.metrics.add(name="unsupported.summary")
    unsupported.summary.data_points.add(time_unix_nano=100, count=1, sum=0)
    absent = scope.metrics.add(name="absent.exponential")
    absent.exponential_histogram.data_points.add(
        flags=DataPointFlags.DATA_POINT_FLAGS_NO_RECORDED_VALUE_MASK
    )
    path.write_text("{}\n\n" + json.dumps(MessageToDict(request)) + "\n", encoding="utf-8")
    return path


def _run_cli(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-m", "robotics_acceptance_harness.cli", *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )


@pytest.mark.parametrize("level", ("DEBUG", "INFO", "WARNING", "ERROR"))
def test_real_cli_keeps_stdout_json_and_writes_structured_otlp_warnings(
    tmp_path: Path, level: str
) -> None:
    source = _metrics_file(tmp_path / "metrics.jsonl")
    diagnostic = tmp_path / "diagnostic.json"
    process = _run_cli(
        [
            "otel-summary",
            "--otel-metrics",
            str(source),
            "--diagnostic-output",
            str(diagnostic),
            "--log-level",
            level,
        ]
    )

    assert process.returncode == 0
    assert json.loads(process.stdout) == {"sample_count": 1, "instruments": {"supported.0": 1}}
    report = json.loads(diagnostic.read_text(encoding="utf-8"))
    assert (report["command"], report["status"], report["exit_code"]) == (
        "otel-summary",
        "completed",
        0,
    )
    attribute, instrument = report["warnings"]
    assert attribute == {
        "diagnostic_id": "otlp.unsupported_attribute",
        "level": "warning",
        "message": "Discarding OTLP attribute with unsupported type array_value",
        "source_path": str(source.resolve()),
        "line_number": 3,
        "metric_name": "supported.0",
        "attribute_key": "discarded",
        "otlp_type": "array_value",
        "occurrences": 3,
    }
    assert instrument["diagnostic_id"] == "otlp.unsupported_instrument"
    assert instrument["metric_name"] == "unsupported.summary"
    assert instrument["otlp_type"] == "summary" and instrument["occurrences"] == 1
    assert _SECRET not in process.stdout + process.stderr + diagnostic.read_text(encoding="utf-8")
    assert process.stderr.count("WARNING:") == (0 if level == "ERROR" else 2)


def test_real_cli_warning_limit_preserves_supported_points(tmp_path: Path) -> None:
    source = _metrics_file(tmp_path / "many.jsonl", count=105)
    diagnostic = tmp_path / "diagnostic.json"
    process = _run_cli(
        [
            "otel-summary",
            "--otel-metrics",
            str(source),
            "--diagnostic-output",
            str(diagnostic),
        ]
    )

    assert process.returncode == 0
    assert json.loads(process.stdout)["sample_count"] == 105
    report = json.loads(diagnostic.read_text(encoding="utf-8"))
    assert len(report["warnings"]) == 100
    assert all(item["occurrences"] == 3 for item in report["warnings"])
    assert report["omitted_warnings"] == 16
    assert process.stderr.count("WARNING:") == 100
    assert _SECRET not in process.stderr + diagnostic.read_text(encoding="utf-8")


def test_real_cli_preserves_warnings_when_a_later_json_line_is_malformed(tmp_path: Path) -> None:
    source = _metrics_file(tmp_path / "invalid-tail.jsonl")
    with source.open("a", encoding="utf-8") as stream:
        stream.write("not-json\n")
    diagnostic = tmp_path / "diagnostic.json"

    process = _run_cli(
        [
            "otel-summary",
            "--otel-metrics",
            str(source),
            "--diagnostic-output",
            str(diagnostic),
            "--log-level",
            "ERROR",
        ]
    )

    assert process.returncode == 2 and process.stdout == ""
    report = json.loads(diagnostic.read_text(encoding="utf-8"))
    assert report["status"] == "error" and report["error_id"] == "MetricInputError.failed"
    assert "invalid-tail.jsonl:4:" in report["message"]
    assert len(report["warnings"]) == 2
    assert "WARNING:" not in process.stderr and "Traceback" not in process.stderr
    assert _SECRET not in process.stderr + diagnostic.read_text(encoding="utf-8")


@pytest.mark.parametrize("command", _COMMANDS)
def test_every_command_syntax_error_can_write_a_diagnostic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], command: str
) -> None:
    destination = tmp_path / "arguments.json"
    with pytest.raises(SystemExit) as caught:
        main([command, "--unknown-option", "--diagnostic-output", str(destination)])

    assert caught.value.code == 2
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["command"] == command and payload["status"] == "error"
    assert payload["error_id"] == "input.invalid" and payload["message"]
    streams = capsys.readouterr()
    assert streams.out == "" and "usage:" in streams.err and "Traceback" not in streams.err


@pytest.mark.parametrize("command", _COMMANDS)
def test_command_help_has_reporting_options_without_creating_a_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], command: str
) -> None:
    destination = tmp_path / "help.json"
    with pytest.raises(SystemExit) as caught:
        main([command, "--diagnostic-output", str(destination), "--help"])

    assert caught.value.code == 0 and not destination.exists()
    streams = capsys.readouterr()
    assert "--diagnostic-output" in streams.out and "--log-level" in streams.out
    assert streams.err == ""


@pytest.mark.parametrize(
    "arguments",
    [
        ["unknown-command"],
        ["doctor", "--mode", "invalid"],
        ["doctor", "--log-level", "invalid"],
        ["doctor", "--mode"],
        ["evaluate", "--window-start-ns", "not-an-integer"],
    ],
)
def test_syntax_errors_keep_system_exit_and_explicit_equals_destination(
    tmp_path: Path, arguments: list[str]
) -> None:
    destination = tmp_path / "syntax.json"
    process = _run_cli([*arguments, f"--diagnostic-output={destination}"])
    assert process.returncode == 2 and process.stdout == ""
    assert json.loads(destination.read_text(encoding="utf-8"))["error_id"] == "input.invalid"
    assert "Traceback" not in process.stderr


def test_syntax_error_does_not_treat_positional_text_as_a_diagnostic_option(tmp_path: Path) -> None:
    destination = tmp_path / "not-requested.json"
    with pytest.raises(SystemExit) as caught:
        main(["why", "--", "--diagnostic-output", str(destination)])
    assert caught.value.code == 2 and not destination.exists()


def test_syntax_error_with_missing_diagnostic_value_preserves_argparse_exit() -> None:
    with pytest.raises(SystemExit) as caught:
        main(["doctor", "--diagnostic-output"])
    assert caught.value.code == 2
