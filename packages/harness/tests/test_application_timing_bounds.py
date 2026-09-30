from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from types import MethodType, SimpleNamespace
from typing import cast

import pytest
import yaml
from junitparser import JUnitXml

from robotics_acceptance_harness import ros
from robotics_acceptance_harness.application import VerificationError, VerificationOutputs
from robotics_acceptance_harness.documents import load_bundle
from robotics_acceptance_harness.readiness import GraphSnapshot, TopicObservation
from robotics_acceptance_harness.ros import RosGraphObserver, RosObserverError
from robotics_acceptance_harness.timing import ClockSample
from tests.support import FakeTime
from tests.test_application import (
    FIXTURES,
    SIMULATION_DOMAIN,
    SIMULATION_RUN_ID,
    FakeObserver,
    _run_case,
    _write_evidence,
    _write_metrics,
    _write_run_context,
)

SECOND = 1_000_000_000
DURATION = 30 * SECOND
EPOCH = 1_785_067_200 * SECOND
DEADLINE = "robotics.simulation.deadline_miss_ratio"


def _source_time(profile: str, elapsed: int) -> int | None:
    if profile == "freeze-midpoint":
        return min(elapsed, 15 * SECOND)
    if profile == "freeze-tail":
        return min(elapsed, 29 * SECOND)
    if profile == "freeze-catch-up" and 15 * SECOND <= elapsed < 20 * SECOND:
        return 15 * SECOND
    if profile == "burst-freeze-catch-up":
        if 15 * SECOND < elapsed < 16 * SECOND + SECOND // 20:
            return 115 * SECOND
        return elapsed + (200 * SECOND if elapsed >= 16 * SECOND + SECOND // 20 else 0)
    if profile == "short-final-trace" and elapsed < DURATION - 100_000_000:
        return None
    if profile == "silent-tail" and elapsed >= 29 * SECOND:
        return None
    if profile == "silent-interior" and 15 * SECOND <= elapsed < 20 * SECOND:
        return None
    if profile == "slowdown":
        return elapsed // 2
    return elapsed


class InjectedClockObserver(FakeObserver):
    """Synchronous graph adapter exercising production clock retention/overflow."""

    def __init__(self, clock: FakeTime, profile: str) -> None:
        super().__init__(clock)
        self.profile = profile
        self.measurement_start: int | None = None
        self.callback_time_ns = 0
        self.callback_count = 0
        self._observation_lock = Lock()
        self._first_messages: dict[str, int] = {}
        self._max_clock_samples = RosGraphObserver.DEFAULT_MAX_CLOCK_SAMPLES
        self._clock_sample_overflow = False
        self._callback = MethodType(RosGraphObserver._clock_callback, self)

    def start_clock_observation(self) -> None:
        super().start_clock_observation()
        self.measurement_start = self.clock.value_ns
        self.callback_count = 0

    def _require_running(self) -> None:
        # The adapter has no ROS executor; graph and callback delivery are injected.
        if self.closed:
            raise RosObserverError("observer is closed")

    def stop_clock_observation(self) -> tuple[ClockSample, ...]:
        return RosGraphObserver.stop_clock_observation(cast(RosGraphObserver, self))

    def snapshot(self) -> GraphSnapshot:
        elapsed = self.clock.value_ns - (self.measurement_start or 0)
        source = elapsed if self.measurement_start is None else _source_time(self.profile, elapsed)
        self.callback_time_ns = self.clock.value_ns
        if self.profile == "jitter" and elapsed == 10 * SECOND:
            self.callback_time_ns += 3_000_000
        if source is not None:
            source += 500 * SECOND  # Source, monotonic and Unix origins differ.
            self._callback(
                SimpleNamespace(
                    clock=SimpleNamespace(sec=source // SECOND, nanosec=source % SECOND)
                )
            )
            if self.measurement_start is not None:
                self.callback_count += 1
        return GraphSnapshot(
            observed_at_ns=self.clock.value_ns,
            topics={
                "/clock": TopicObservation(
                    types=("rosgraph_msgs/msg/Clock",),
                    publishers=1,
                    subscribers=0,
                    first_message_at_ns=0,
                )
            },
        )


def _verify(
    tmp_path: Path,
    observer: InjectedClockObserver,
    monkeypatch: pytest.MonkeyPatch,
    deadline_values: tuple[float, ...] = (0.0,),
) -> VerificationOutputs:
    scenario = yaml.safe_load((FIXTURES / "scenario.yaml").read_text(encoding="utf-8"))
    scenario["timeouts"]["stable_for_sec"] = 0
    scenario["timeouts"]["execution_sec"] = 30
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
    assert outputs.result["time_authority_observation"]["within_policy"]
    assert outputs.result["observed_ros_graph"]["topics"][0]["publishers"] == 1
    return outputs


@pytest.mark.parametrize(
    ("profile", "expected_status"),
    [
        ("freeze-midpoint", "failed"),
        ("freeze-tail", "failed"),
        ("freeze-catch-up", "failed"),
        ("burst-freeze-catch-up", "incomplete"),
        ("short-final-trace", "incomplete"),
        ("silent-tail", "incomplete"),
        ("silent-interior", "incomplete"),
    ],
)
def test_full_measurement_rejects_pauses_and_missing_clock_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile: str, expected_status: str
) -> None:
    observer = InjectedClockObserver(FakeTime(), profile)
    outputs = _verify(tmp_path, observer, monkeypatch)
    assert outputs.result["status"] == expected_status
    assert outputs.result["clock_observation"]["real_time_factor"] == 0
    junit = JUnitXml.fromfile(str(outputs.junit_path))
    assert junit.failures == (1 if expected_status == "failed" else 0)
    assert junit.errors == 0
    if expected_status == "incomplete":
        assert junit.skipped == 2  # Time policy and incomplete evaluation coverage.
        assert "$.clock_observation.real_time_factor" in outputs.result["unevaluated"]
    if "freeze" in profile:
        assert observer.callback_count == len(observer.clock_samples) == 600


@pytest.mark.parametrize(("profile", "status"), [("jitter", "passed"), ("slowdown", "failed")])
def test_callback_jitter_and_real_slowdown_remain_distinct(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile: str, status: str
) -> None:
    observer = InjectedClockObserver(FakeTime(), profile)
    outputs = _verify(tmp_path, observer, monkeypatch)
    assert outputs.result["status"] == status
    # The delayed callback can exclude one recorded endpoint at each edge of a
    # one-second interval. The bound uses the remaining 900 ms of source progress;
    # it does not interpolate those two unobserved endpoint values.
    assert outputs.result["clock_observation"]["real_time_factor"] == (
        0.9 if profile == "jitter" else 0.475
    )
    junit = JUnitXml.fromfile(str(outputs.junit_path))
    assert junit.failures == int(status == "failed") and junit.errors == 0


@pytest.mark.parametrize("values", [(-0.1, 0.0), (0.0, -0.1), (0.0, 1.1), (1.1, 0.0)])
def test_invalid_deadline_measurements_cannot_be_hidden_by_the_maximum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, values: tuple[float, ...]
) -> None:
    with pytest.raises(VerificationError, match="finite ratios in"):
        _verify(tmp_path, InjectedClockObserver(FakeTime(), "steady"), monkeypatch, values)
    assert not list((tmp_path / "output").glob("*.json"))


def test_valid_deadline_peak_still_fails_the_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outputs = _verify(
        tmp_path, InjectedClockObserver(FakeTime(), "steady"), monkeypatch, (0.0, 0.5, 0.0)
    )
    assert outputs.result["status"] == "failed"
    assert outputs.result["clock_observation"]["deadline_miss_ratio"] == 0.5
    assert JUnitXml.fromfile(str(outputs.junit_path)).failures == 1


def test_repeated_callback_overflow_aborts_verification_instead_of_truncating_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observer = InjectedClockObserver(FakeTime(), "freeze-midpoint")
    observer._max_clock_samples = 350  # 301 unique values would fit; repeats must count too.
    with pytest.raises(RosObserverError, match="350 clock samples"):
        _verify(tmp_path, observer, monkeypatch)
    assert len(observer.clock_samples) == 350
    assert observer.closed
    assert not list((tmp_path / "output").glob("*.json"))
