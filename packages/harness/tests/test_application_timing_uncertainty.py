from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from junitparser import JUnitXml

from robotics_acceptance_harness import ros
from robotics_acceptance_harness.application import VerificationOutputs
from robotics_acceptance_harness.documents import load_bundle
from tests import test_application_timing_bounds as timing_bounds
from tests.support import FakeTime
from tests.test_application import (
    FIXTURES,
    SIMULATION_DOMAIN,
    SIMULATION_RUN_ID,
    _run_case,
    _write_evidence,
    _write_metrics,
    _write_run_context,
)

SECOND = 1_000_000_000
DURATION = 30 * SECOND
EPOCH = 1_785_067_200 * SECOND
DEADLINE = "robotics.simulation.deadline_miss_ratio"


def _verify(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    profile: str,
    *,
    threshold: float = 0.95,
    deadline_values: tuple[float, ...] = (0.0,),
) -> VerificationOutputs:
    """Run real policy, OTLP/evidence validation and writers with injected ROS delivery."""

    scenario = yaml.safe_load((FIXTURES / "scenario.yaml").read_text(encoding="utf-8"))
    scenario["timeouts"].update(stable_for_sec=0, execution_sec=30)
    scenario["time_policy"]["min_realtime_factor"] = threshold
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
    bundle = load_bundle(scenario_path, runtime_path=FIXTURES / "runtime.yaml")
    metrics_path = tmp_path / "metrics.jsonl"
    _write_metrics(
        metrics_path,
        run_id=SIMULATION_RUN_ID,
        domain_id=SIMULATION_DOMAIN,
        source_id="simulation-clock",
        start_ns=EPOCH,
        end_ns=EPOCH + DURATION,
    )
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
    deadline = next(metric for metric in metrics if metric["name"] == DEADLINE)
    deadline["gauge"]["dataPoints"] = [
        {
            "timeUnixNano": str(EPOCH + DURATION * index // max(1, len(deadline_values) - 1)),
            "asDouble": value,
        }
        for index, value in enumerate(deadline_values)
    ]
    metrics_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    evidence = _write_evidence(tmp_path / "evidence.yaml", metrics_path, run_id=SIMULATION_RUN_ID)
    context = _write_run_context(
        tmp_path / "run.yaml",
        bundle,
        run_id=SIMULATION_RUN_ID,
        domain_id=SIMULATION_DOMAIN,
        time_kind="sim_clock",
        source_id="simulation-clock",
    )
    original_source = timing_bounds._source_time

    def source_time(profile: str, elapsed: int) -> int | None:
        if profile == "no-clock" or (profile == "one-clock" and elapsed != 0):
            return None
        if profile == "steady10" and elapsed % 100_000_000:
            return None
        if profile == "gap-then-freeze":
            return None if 10 * SECOND <= elapsed < 12 * SECOND else min(elapsed, 20 * SECOND)
        return original_source(profile, elapsed)

    monkeypatch.setattr(timing_bounds, "_source_time", source_time)
    observer = timing_bounds.InjectedClockObserver(FakeTime(), profile)
    monkeypatch.setattr(ros, "monotonic_ns", lambda: observer.callback_time_ns)
    started = datetime(2026, 7, 26, 12, tzinfo=UTC)
    outputs = _run_case(
        tmp_path,
        bundle=bundle,
        run_id=SIMULATION_RUN_ID,
        domain_id=SIMULATION_DOMAIN,
        run_context_path=context,
        evidence_path=evidence,
        metrics_path=metrics_path,
        measurement_complete_path=tmp_path / "measurement-complete",
        observer=observer,
        clock=observer.clock,
        window=(EPOCH, EPOCH + DURATION),
        interval=(started, started + timedelta(seconds=30)),
    )
    assert outputs.result["monotonic_duration_sec"] == 30
    assert observer.measurement_start is not None
    assert observer.clock.value_ns - observer.measurement_start == DURATION
    authority = outputs.result["time_authority_observation"]
    assert authority["sample_count"] == 30  # Actual latency evidence survives clock uncertainty.
    assert authority["within_policy"]
    assert outputs.result["observed_ros_graph"]["topics"][0]["publishers"] == 1
    assert observer.closed
    assert json.loads(outputs.result_path.read_text(encoding="utf-8")) == outputs.result
    if profile in {"steady10", "jitter"}:
        assert (
            observer.callback_count
            == len(observer.clock_samples)
            == (300 if profile == "steady10" else 600)
        )
    return outputs


@pytest.mark.parametrize("profile", ["steady10", "jitter"])
def test_thirty_second_1x_clock_uncertainty_is_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile: str
) -> None:
    outputs = _verify(tmp_path, monkeypatch, profile)
    result = outputs.result
    assert result["status"] == "incomplete"
    assert result["clock_observation"]["real_time_factor"] == 0.9
    assert "$.clock_observation.real_time_factor" in result["unevaluated"]
    assertion = next(
        item for item in result["assertion_results"] if item["assertion_id"] == "time-policy"
    )
    assert assertion["status"] == "skipped"
    assert "bound" in assertion["message"]
    junit = JUnitXml.fromfile(str(outputs.junit_path))
    assert junit.failures == junit.errors == 0
    assert junit.skipped > 0


@pytest.mark.parametrize(
    "profile",
    [
        "no-clock",
        "one-clock",
        "short-final-trace",
        "silent-tail",
        "silent-interior",
        "burst-freeze-catch-up",
    ],
)
def test_missing_or_ambiguous_clock_progress_is_not_a_measured_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile: str
) -> None:
    outputs = _verify(tmp_path, monkeypatch, profile)
    assert outputs.result["status"] == "incomplete"
    assert "$.clock_observation.real_time_factor" in outputs.result["unevaluated"]
    junit = JUnitXml.fromfile(str(outputs.junit_path))
    assert junit.failures == junit.errors == 0 and junit.skipped > 0


@pytest.mark.parametrize(
    "profile", ["freeze-midpoint", "freeze-tail", "freeze-catch-up", "slowdown", "gap-then-freeze"]
)
def test_proven_clock_violations_remain_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile: str
) -> None:
    outputs = _verify(tmp_path, monkeypatch, profile)
    assert outputs.result["status"] == "failed"
    assertion = next(
        item
        for item in outputs.result["assertion_results"]
        if item["assertion_id"] == "time-policy"
    )
    assert assertion["status"] == "failed"
    assert "RTF is at most" in assertion["message"]
    junit = JUnitXml.fromfile(str(outputs.junit_path))
    assert junit.failures == 1 and junit.errors == 0


@pytest.mark.parametrize("profile", ["steady", "jitter", "no-clock", "silent-interior"])
def test_deadline_peak_failure_takes_precedence_over_clock_uncertainty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile: str
) -> None:
    outputs = _verify(tmp_path, monkeypatch, profile, deadline_values=(0.0, 0.5, 0.0))
    assert outputs.result["status"] == "failed"
    assert outputs.result["clock_observation"]["deadline_miss_ratio"] == 0.5
    junit = JUnitXml.fromfile(str(outputs.junit_path))
    assert junit.failures == 1 and junit.errors == 0


@pytest.mark.parametrize(
    ("profile", "status"), [("steady", "incomplete"), ("freeze-tail", "failed")]
)
def test_missing_deadline_evidence_is_unevaluated_and_preserves_failure_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile: str, status: str
) -> None:
    outputs = _verify(tmp_path, monkeypatch, profile, deadline_values=())
    assert outputs.result["status"] == status
    assert "$.clock_observation.deadline_miss_ratio" in outputs.result["unevaluated"]
    junit = JUnitXml.fromfile(str(outputs.junit_path))
    assert junit.failures == int(status == "failed") and junit.errors == 0


@pytest.mark.parametrize(
    ("profile", "threshold"), [("steady", 0.95), ("steady10", 0.9), ("jitter", 0.9)]
)
def test_a_sufficient_lower_bound_still_passes_at_the_unchanged_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile: str, threshold: float
) -> None:
    outputs = _verify(tmp_path, monkeypatch, profile, threshold=threshold)
    assert outputs.result["status"] == "passed"
    assert outputs.result["unevaluated"] == []
    junit = JUnitXml.fromfile(str(outputs.junit_path))
    assert junit.failures == junit.errors == junit.skipped == 0
