from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from junitparser import JUnitXml

from robotics_acceptance_harness.readiness import GraphSnapshot
from tests.test_application import FakeObserver, _simulation_case


@pytest.mark.parametrize(
    "fault, status, diagnostic",
    [
        ("publisher", "failed", "min_publishers"),
        ("topic", "failed", "topic /clock is absent"),
        ("unobservable", "error", "no message has been observed"),
        ("none", "passed", ""),
    ],
)
def test_verification_retains_measurement_faults_but_not_initialization_faults(
    tmp_path: Path,
    fault: str,
    status: str,
    diagnostic: str,
) -> None:
    observations: list[GraphSnapshot] = []

    class RecoveringObserver(FakeObserver):
        measurement_start: int | None = None

        def start_clock_observation(self) -> None:
            super().start_clock_observation()
            self.measurement_start = self.clock.value_ns

        def snapshot(self) -> GraphSnapshot:
            snapshot = super().snapshot()
            # A readiness discovery transient must never enter the measurement history.
            if self.measurement_start is None and self.clock.value_ns == 0:
                return replace(snapshot, topics={})
            if self.measurement_start is not None:
                if self.clock.value_ns == self.measurement_start + 50_000_000:
                    snapshot = _degrade(snapshot, fault)
                observations.append(snapshot)
            return snapshot

    outputs = _simulation_case(tmp_path, observer_type=RecoveringObserver)
    assert len(observations) == 4
    assert observations[-1].topics["/clock"].publishers == 1
    assert outputs.result["status"] == status
    assertions = outputs.result["assertion_results"]
    graph_assertions = [item for item in assertions if item["assertion_id"] == "expected-ros-graph"]
    junit = JUnitXml.fromfile(str(outputs.junit_path))
    assert junit.failures == int(status == "failed")
    assert junit.errors == int(status == "error")
    if status == "passed":
        assert graph_assertions == []
    else:
        (assertion,) = graph_assertions
        assert assertion["status"] == status
        assert diagnostic in assertion["message"]
        assert "monotonic_ns=100000000" in assertion["message"]
        assert diagnostic in outputs.junit_path.read_text(encoding="utf-8")


def _degrade(snapshot: GraphSnapshot, fault: str) -> GraphSnapshot:
    topic = snapshot.topics["/clock"]
    if fault == "topic":
        return replace(snapshot, topics={})
    if fault == "publisher":
        return replace(snapshot, topics={"/clock": replace(topic, publishers=0)})
    if fault == "unobservable":
        return replace(snapshot, topics={"/clock": replace(topic, first_message_at_ns=None)})
    return snapshot
