from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import partial
from hashlib import sha256
from pathlib import Path
from typing import BinaryIO, cast

import pytest

from robotics_acceptance_harness import otel
from robotics_acceptance_harness._evidence_files import open_evidence
from robotics_acceptance_harness.aggregate import evaluate_transport_qualification
from robotics_acceptance_harness.application import evaluate_from_evidence, run_verification
from robotics_acceptance_harness.documents import DocumentBundle
from robotics_acceptance_harness.errors import HarnessInputError
from robotics_acceptance_harness.otel import MetricInputError, load_otlp_json_metrics
from robotics_acceptance_harness.traces import TraceInputError, load_otlp_json_traces


@pytest.fixture(params=["metrics", "traces"])
def raw_loader(request: pytest.FixtureRequest) -> tuple[Callable[..., object], type[ValueError]]:
    if request.param == "metrics":
        return load_otlp_json_metrics, MetricInputError
    return (
        partial(load_otlp_json_traces, expected_run_id="run", expected_domain_id="domain"),
        TraceInputError,
    )


@pytest.mark.parametrize("budget", [0, -1, True, False, 1.5, "3"])
def test_public_otlp_budget_rejects_invalid_values_before_io(
    tmp_path: Path,
    raw_loader: tuple[Callable[..., object], type[ValueError]],
    budget: object,
) -> None:
    load, _ = raw_loader
    with pytest.raises(HarnessInputError, match="must be a positive integer or None") as caught:
        load(tmp_path / "missing.jsonl", max_raw_evidence_bytes=budget)
    assert caught.value.error_id == "input.invalid"


def test_declared_oversize_is_refused_without_reading_or_decoding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_loader: tuple[Callable[..., object], type[ValueError]],
) -> None:
    path = tmp_path / "oversize.jsonl"
    path.write_bytes(b"\xff\n")
    original_open = open_evidence
    requested: list[int] = []

    @contextmanager
    def opened(source: Path, root: Path) -> Iterator[BinaryIO]:
        with original_open(source, root) as stream:
            original_read = stream.read

            def read(size: int = -1) -> bytes:
                requested.append(size)
                return original_read(size)

            monkeypatch.setattr(stream, "read", read)
            yield stream

    monkeypatch.setattr(otel, "open_evidence", opened)
    load, error_type = raw_loader
    with pytest.raises(error_type, match="raw evidence exceeds max_raw_evidence_bytes"):
        load(path, expected_sha256="0" * 64, max_raw_evidence_bytes=1)
    assert requested == []


@pytest.mark.parametrize("extra_budget", [0, 16])
def test_growing_otlp_is_bounded_and_never_parses_a_valid_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_loader: tuple[Callable[..., object], type[ValueError]],
    extra_budget: int,
) -> None:
    path = tmp_path / "growing.jsonl"
    original_bytes = b"{}\n"
    path.write_bytes(original_bytes)
    budget = len(original_bytes) + extra_budget
    original_open = open_evidence
    requested: list[int] = []

    @contextmanager
    def opened(source: Path, root: Path) -> Iterator[BinaryIO]:
        with original_open(source, root) as stream:
            original_read = stream.read

            def read(size: int = -1) -> bytes:
                requested.append(size)
                with path.open("ab") as writer:
                    writer.write(b"{}\n")
                return original_read(size)

            monkeypatch.setattr(stream, "read", read)
            yield stream

    monkeypatch.setattr(otel, "open_evidence", opened)
    load, error_type = raw_loader
    message = "exceeds max_raw_evidence_bytes" if extra_budget == 0 else "changed while being read"
    with pytest.raises(error_type, match=message):
        load(path, max_raw_evidence_bytes=budget)
    assert requested == [len(original_bytes) + 1]
    assert requested[0] <= budget + 1


def test_same_size_otlp_mutation_still_refuses_the_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_loader: tuple[Callable[..., object], type[ValueError]],
) -> None:
    path = tmp_path / "changed.jsonl"
    path.write_bytes(b"{}\n")
    original_open = open_evidence

    @contextmanager
    def opened(source: Path, root: Path) -> Iterator[BinaryIO]:
        with original_open(source, root) as stream:
            original_read = stream.read

            def read(size: int = -1) -> bytes:
                payload = original_read(size)
                path.write_bytes(b"[]\n")
                return payload

            monkeypatch.setattr(stream, "read", read)
            yield stream

    monkeypatch.setattr(otel, "open_evidence", opened)
    load, error_type = raw_loader
    with pytest.raises(error_type, match="changed while being read"):
        load(path, max_raw_evidence_bytes=3)


def test_bounded_otlp_retains_hash_before_utf8_and_line_errors(
    tmp_path: Path,
    raw_loader: tuple[Callable[..., object], type[ValueError]],
) -> None:
    path = tmp_path / "bad.jsonl"
    payload = b"\xff\n"
    path.write_bytes(payload)
    load, error_type = raw_loader
    with pytest.raises(error_type, match="digest differs"):
        load(path, expected_sha256="0" * 64, max_raw_evidence_bytes=len(payload))
    with pytest.raises(error_type, match="cannot decode") as caught:
        load(path, expected_sha256=sha256(payload).hexdigest(), max_raw_evidence_bytes=len(payload))
    assert isinstance(caught.value.__cause__, UnicodeDecodeError)

    path.write_bytes(b"{}\nnot-json\n")
    with pytest.raises(error_type, match=r"bad\.jsonl:2:"):
        load(path, max_raw_evidence_bytes=path.stat().st_size)
    with pytest.raises(error_type, match="exceeds max_raw_evidence_bytes"):
        load(path, max_raw_evidence_bytes=path.stat().st_size - 1)


@pytest.mark.parametrize("budget", [0, True, 1.5])
@pytest.mark.parametrize("entry", ["verify", "evaluate", "transport"])
def test_high_level_budget_validation_precedes_observation_or_document_io(
    tmp_path: Path,
    budget: object,
    entry: str,
) -> None:
    limit = cast(int, budget)
    with pytest.raises(HarnessInputError, match="must be a positive integer or None"):
        if entry == "transport":
            evaluate_transport_qualification(
                run_id="run",
                scenario_path="missing.yaml",
                causal_chain_paths=(),
                channel_contract_paths=(),
                trace_paths={},
                evidence_index_paths={},
                observation_output_dir=tmp_path,
                output_path=tmp_path / "transport.json",
                max_raw_evidence_bytes=limit,
            )
        elif entry == "verify":
            run_verification(
                run_id="run",
                bundle=cast(DocumentBundle, None),
                domain_id="domain",
                run_context_path="missing.yaml",
                evidence_index_path="missing-index.json",
                otel_metrics_path="missing.jsonl",
                output_dir=tmp_path,
                measurement_complete_path=tmp_path / "complete",
                max_raw_evidence_bytes=limit,
            )
        else:
            evaluate_from_evidence(
                run_id="run",
                bundle=cast(DocumentBundle, None),
                domain_id="domain",
                run_context_path="missing.yaml",
                evidence_index_path="missing-index.json",
                otel_metrics_path="missing.jsonl",
                output_dir=tmp_path,
                window_start_ns=1,
                window_end_ns=2,
                max_raw_evidence_bytes=limit,
            )
    assert list(tmp_path.iterdir()) == []


def test_otel_summary_budget_failure_retains_structured_diagnostic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from robotics_acceptance_harness.cli import main

    source = tmp_path / "metrics.jsonl"
    source.write_bytes(b"{}\n")
    diagnostic = tmp_path / "diagnostic.json"
    assert (
        main(
            [
                "otel-summary",
                "--otel-metrics",
                str(source),
                "--max-raw-evidence-bytes",
                "3",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        main(
            [
                "otel-summary",
                "--otel-metrics",
                str(source),
                "--max-raw-evidence-bytes",
                "2",
                "--diagnostic-output",
                str(diagnostic),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "[MetricInputError.failed]" in captured.err
    assert "exceeds max_raw_evidence_bytes" in captured.err
    import json

    document = json.loads(diagnostic.read_text())
    assert document["error_id"] == "MetricInputError.failed"
    assert (
        main(
            [
                "otel-summary",
                "--otel-metrics",
                "missing.jsonl",
                "--max-raw-evidence-bytes",
                "0",
            ]
        )
        == 2
    )
    assert "[input.invalid]" in capsys.readouterr().err
