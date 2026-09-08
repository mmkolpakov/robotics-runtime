from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from junitparser import JUnitXml

from robotics_acceptance_harness.application import _enrich_clock_samples, _measurement_metrics
from robotics_acceptance_harness.metrics import MetricSample
from robotics_acceptance_harness.timing import ClockSample, TimingValidationError, evaluate_timing
from tests.support import FakeTime
from tests.test_application import (
    SIMULATION_DOMAIN,
    SIMULATION_RUN_ID,
    FakeObserver,
    _run_case,
    _simulation_bundle,
    _write_evidence,
    _write_metrics,
    _write_run_context,
)

SECOND = 1_000_000_000
EPOCH = 1_785_067_200 * SECOND
DEADLINE = "robotics.simulation.deadline_miss_ratio"


@pytest.mark.parametrize(
    "spike_offset", [SECOND - 1, SECOND, SECOND + SECOND // 2, 2 * SECOND, 2 * SECOND + 1]
)
def test_verification_uses_every_deadline_gauge_inside_the_wall_clock_window(
    tmp_path: Path,
    spike_offset: int,
) -> None:
    bundle = _simulation_bundle(tmp_path)
    metrics_path = tmp_path / "metrics.otlp.json"
    _write_metrics(
        metrics_path,
        run_id=SIMULATION_RUN_ID,
        domain_id=SIMULATION_DOMAIN,
        source_id="simulation-clock",
        start_ns=EPOCH + SECOND,
        end_ns=EPOCH + 2 * SECOND,
    )
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
    deadline = next(metric for metric in metrics if metric["name"] == DEADLINE)
    deadline["gauge"]["dataPoints"].append(
        {"timeUnixNano": str(EPOCH + spike_offset), "asDouble": 0.5}
    )
    metrics_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    evidence_path = _write_evidence(
        tmp_path / "evidence.json", metrics_path, run_id=SIMULATION_RUN_ID
    )
    context_path = _write_run_context(
        tmp_path / "run.yaml",
        bundle,
        run_id=SIMULATION_RUN_ID,
        domain_id=SIMULATION_DOMAIN,
        time_kind="sim_clock",
        source_id="simulation-clock",
    )
    clock = FakeTime()
    started = datetime(2026, 7, 26, 12, 0, 1, tzinfo=UTC)
    outputs = _run_case(
        tmp_path,
        bundle=bundle,
        run_id=SIMULATION_RUN_ID,
        domain_id=SIMULATION_DOMAIN,
        run_context_path=context_path,
        evidence_path=evidence_path,
        metrics_path=metrics_path,
        measurement_complete_path=tmp_path / "measurement-complete",
        observer=FakeObserver(clock),
        clock=clock,
        window=(EPOCH + SECOND, EPOCH + 2 * SECOND),
        interval=(started, started + timedelta(seconds=1)),
    )

    inside = SECOND <= spike_offset <= 2 * SECOND
    assert outputs.result["clock_observation"]["deadline_miss_ratio"] == (0.5 if inside else 0)
    assert outputs.result["status"] == ("failed" if inside else "passed")
    junit = JUnitXml.fromfile(str(outputs.junit_path))
    assert junit.failures == int(inside)


def test_cumulative_sum_baseline_cannot_impersonate_a_deadline_gauge() -> None:
    metrics = _measurement_metrics(
        [
            MetricSample(
                DEADLINE, 0.5, "1", EPOCH - 1, instrument_kind="sum", temporality="cumulative"
            )
        ],
        window_start_ns=EPOCH,
        window_end_ns=EPOCH + SECOND,
    )
    enriched = _enrich_clock_samples(
        "simulation_realtime",
        (ClockSample(0, 0), ClockSample(SECOND, SECOND)),
        metrics,
    )

    with pytest.raises(TimingValidationError, match="deadline_miss_ratio was not observed"):
        evaluate_timing(
            {"time_mode": "simulation_realtime"},
            {"min_realtime_factor": 0.8, "max_deadline_miss_ratio": 0.01},
            enriched,
        )
