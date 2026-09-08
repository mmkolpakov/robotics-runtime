from __future__ import annotations

from dataclasses import replace

import pytest

from robotics_acceptance_harness.graph_window import ExpectedGraphMonitor
from robotics_acceptance_harness.metrics import AssertionEvaluation
from robotics_acceptance_harness.readiness import (
    GraphSnapshot,
    LifecycleObservation,
    TopicObservation,
)
from tests.graph_types import ExpectedGraph
from tests.test_readiness import expected_graph, ready_snapshot


def lifecycle_graph() -> ExpectedGraph:
    return {
        "topics": [],
        "services": [],
        "actions": [],
        "lifecycle_nodes": [
            {
                "name": "/camera",
                "required_state": "active",
                "timeout_sec": 5,
                "stable_for_sec": 0,
            }
        ],
    }


def topic_snapshot(topic: TopicObservation) -> GraphSnapshot:
    return replace(ready_snapshot(), topics={"/camera/image": topic})


TOPIC = ready_snapshot().topics["/camera/image"]


@pytest.mark.parametrize(
    "degraded, diagnostic",
    [
        (replace(ready_snapshot(), topics={}), "topic /camera/image is absent"),
        (topic_snapshot(replace(TOPIC, publishers=0)), "min_publishers"),
        (topic_snapshot(replace(TOPIC, subscribers=0)), "min_subscribers"),
        (
            topic_snapshot(replace(TOPIC, types=("sensor_msgs/msg/CompressedImage",))),
            "CompressedImage",
        ),
        (topic_snapshot(replace(TOPIC, qos_compatible=False)), "QoS policies are incompatible"),
        (replace(ready_snapshot(), services={}), "service server /camera/get_parameters is absent"),
        (replace(ready_snapshot(), actions={}), "action server /takeoff is absent"),
    ],
)
def test_observed_degradation_survives_recovery(
    degraded: GraphSnapshot,
    diagnostic: str,
) -> None:
    monitor = ExpectedGraphMonitor(expected_graph(), 10, 20)
    monitor.observe(replace(ready_snapshot(), observed_at_ns=10))
    monitor.observe(replace(degraded, observed_at_ns=12))
    monitor.observe(replace(degraded, observed_at_ns=13))
    monitor.observe(replace(ready_snapshot(), observed_at_ns=19))

    (assertion,) = monitor.assertions(())
    assert assertion.status == "failed"
    assert diagnostic in assertion.message
    assert "monotonic_ns=12" in assertion.message
    assert "monotonic_ns=13" not in assertion.message


@pytest.mark.parametrize(
    "observed_at_ns, fails",
    [
        (9, False),
        (10, True),
        (11, True),
        (19, True),
        (20, False),
        (21, False),
    ],
)
def test_measurement_window_boundaries(observed_at_ns: int, fails: bool) -> None:
    monitor = ExpectedGraphMonitor(expected_graph(), 10, 20)
    monitor.observe(replace(ready_snapshot(), observed_at_ns=15))
    monitor.observe(GraphSnapshot(observed_at_ns=observed_at_ns))

    assert bool(monitor.assertions(())) is fails


@pytest.mark.parametrize(
    "snapshot, status, diagnostic",
    [
        (
            GraphSnapshot(12, lifecycle_nodes={"/camera": LifecycleObservation("inactive", 12)}),
            "failed",
            "observed inactive",
        ),
        (
            GraphSnapshot(
                12,
                node_names=frozenset(),
                lifecycle_nodes={"/camera": LifecycleObservation("active", 11)},
            ),
            "failed",
            "managed node /camera is absent",
        ),
        (GraphSnapshot(12, node_names=frozenset({"/camera"})), "error", "state is unavailable"),
        (GraphSnapshot(12), "error", "state is unavailable"),
        (
            GraphSnapshot(12, lifecycle_nodes={"/camera": LifecycleObservation("unknown", 12)}),
            "error",
            "state is unavailable",
        ),
    ],
)
def test_lifecycle_failure_and_unavailable_state_are_distinct_and_retained(
    snapshot: GraphSnapshot,
    status: str,
    diagnostic: str,
) -> None:
    monitor = ExpectedGraphMonitor(lifecycle_graph(), 10, 20)
    monitor.observe(snapshot)
    monitor.observe(
        GraphSnapshot(
            19,
            lifecycle_nodes={
                "/camera": LifecycleObservation("active", 19),
            },
        )
    )

    (assertion,) = monitor.assertions(())
    assert assertion.status == status
    assert diagnostic in assertion.message


def test_unobservable_window_is_error_without_inventing_absence() -> None:
    monitor = ExpectedGraphMonitor(expected_graph(), 10, 20)
    monitor.observe(replace(ready_snapshot(), observed_at_ns=9))
    monitor.observe(replace(ready_snapshot(), observed_at_ns=20))

    (assertion,) = monitor.assertions(())
    assert assertion.status == "error"
    assert "no graph snapshot inside measurement window" in assertion.message
    assert "is absent" not in assertion.message
    assert "first observed" not in assertion.message


def test_empty_expected_graph_has_no_unobservable_obligations() -> None:
    graph: ExpectedGraph = {"topics": [], "services": [], "actions": [], "lifecycle_nodes": []}
    assert ExpectedGraphMonitor(graph, 10, 20).assertions(()) == ()


def test_errors_take_precedence_without_losing_confirmed_failures() -> None:
    monitor = ExpectedGraphMonitor(lifecycle_graph(), 10, 20)
    monitor.observe(GraphSnapshot(11, node_names=frozenset()))
    monitor.observe(GraphSnapshot(12, node_names=frozenset({"/camera"})))

    (assertion,) = monitor.assertions(())
    assert assertion.status == "error"
    assert "is absent" in assertion.message
    assert "state is unavailable" in assertion.message


def test_graph_diagnostic_does_not_reuse_a_valid_scenario_assertion_id() -> None:
    existing = [
        AssertionEvaluation(name, "passed", 1, "1", "observed")
        for name in ("expected-ros-graph", "expected-ros-graph-1")
    ]
    monitor = ExpectedGraphMonitor(expected_graph(), 10, 20)
    monitor.observe(GraphSnapshot(12))

    (assertion,) = monitor.assertions(existing)
    assert assertion.assertion_id == "expected-ros-graph-2"


@pytest.mark.parametrize("end_ns", [9, 10])
def test_rejects_nonpositive_window(end_ns: int) -> None:
    with pytest.raises(ValueError, match="positive duration"):
        ExpectedGraphMonitor(expected_graph(), 10, end_ns)
