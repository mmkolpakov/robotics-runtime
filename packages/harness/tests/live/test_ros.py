from __future__ import annotations

from time import monotonic, monotonic_ns, sleep
from typing import TYPE_CHECKING

import pytest

from robotics_acceptance_harness.graph_window import ExpectedGraphMonitor
from robotics_acceptance_harness.readiness import evaluate_graph, wait_for_readiness
from robotics_acceptance_harness.ros import RosGraphObserver
from tests.graph_types import ExpectedGraph

if TYPE_CHECKING:
    from tests.live.graph import LiveGraph

pytestmark = pytest.mark.live_ros


def test_clock_not_declared_in_expected_graph(live_graph: LiveGraph) -> None:
    graph: ExpectedGraph = {"topics": [], "services": [], "actions": [], "lifecycle_nodes": []}
    with RosGraphObserver(graph, observe_clock=True) as observer:
        initial_samples = observer.clock_samples
        assert initial_samples == ()
        observer.start_clock_observation()
        deadline = monotonic() + 15
        while len(observer.clock_samples) < 10 and monotonic() < deadline:
            observer.snapshot()
            sleep(0.02)
        samples = observer.stop_clock_observation()
        assert len(samples) >= 10, "no real /clock messages received through implicit subscription"
        assert all(
            b.source_time_ns > a.source_time_ns for a, b in zip(samples, samples[1:], strict=False)
        )
        assert all(
            b.observed_at_ns > a.observed_at_ns for a, b in zip(samples, samples[1:], strict=False)
        )
        sleep(0.1)
        assert observer.clock_samples == samples
        assert observer.snapshot().topics == {}


def test_observes_topic_service_action_and_lifecycle(live_graph: LiveGraph) -> None:
    graph = live_graph.expected()
    with RosGraphObserver(graph, observe_clock=False) as observer:
        readiness = wait_for_readiness(
            graph, observer, timeout_sec=20, stable_for_sec=0.3, poll_interval_sec=0.05
        )
        snapshot = readiness.snapshot
        assert evaluate_graph(graph, snapshot) == ()
        topic = snapshot.topics[live_graph.topic]
        assert topic.types == ("std_msgs/msg/String",)
        assert topic.publishers == 1
        assert topic.subscribers == 1  # The observer's subscription must not count.
        assert topic.first_message_at_ns is not None
        assert topic.qos_compatible
        # Discovery of client endpoints can lag behind server readiness.
        deadline = monotonic() + 10
        while monotonic() < deadline:
            snapshot = observer.snapshot()
            if (
                snapshot.services[live_graph.service].client_nodes == 1
                and snapshot.actions[live_graph.action].client_nodes == 1
            ):
                break
            sleep(0.05)
        service = snapshot.services[live_graph.service]
        assert service.types == ("example_interfaces/srv/AddTwoInts",)
        assert (service.server_nodes, service.client_nodes) == (1, 1)
        action = snapshot.actions[live_graph.action]
        assert action.types == ("action_tutorials_interfaces/action/Fibonacci",)
        assert (action.server_nodes, action.client_nodes) == (1, 1)
        assert snapshot.lifecycle_nodes[live_graph.lifecycle].state == "active"
        assert observer.clock_samples == ()


def _observe_lifecycle_state(
    observer: RosGraphObserver,
    monitor: ExpectedGraphMonitor,
    name: str,
    state: str,
) -> None:
    deadline = monotonic() + 15
    while monotonic() < deadline:
        snapshot = observer.snapshot()
        monitor.observe(snapshot)
        observed = snapshot.lifecycle_nodes.get(name)
        if observed is not None and observed.state == state:
            return
        sleep(0.05)
    pytest.fail(f"real ROS lifecycle node {name} never reported {state}")


def test_measurement_retains_real_lifecycle_deactivation_after_recovery(
    live_graph: LiveGraph,
) -> None:
    from rclpy.lifecycle import TransitionCallbackReturn

    graph = live_graph.expected()
    with RosGraphObserver(graph, observe_clock=False) as observer:
        wait_for_readiness(
            graph,
            observer,
            timeout_sec=20,
            stable_for_sec=0.3,
            poll_interval_sec=0.05,
        )
        start_ns = monotonic_ns()
        monitor = ExpectedGraphMonitor(graph, start_ns, start_ns + 40_000_000_000)
        monitor.observe(observer.snapshot())
        # Only test-owned nodes change state; the production observer remains read-only.
        assert live_graph.managed.trigger_deactivate() == TransitionCallbackReturn.SUCCESS
        _observe_lifecycle_state(observer, monitor, live_graph.lifecycle, "inactive")
        assert live_graph.managed.trigger_activate() == TransitionCallbackReturn.SUCCESS
        _observe_lifecycle_state(observer, monitor, live_graph.lifecycle, "active")

        (assertion,) = monitor.assertions(())
        assert assertion.status == "failed"
        assert "observed inactive" in assertion.message
        assert live_graph.lifecycle in assertion.message


@pytest.mark.parametrize(
    "profile",
    ["system_default", "sensor_data", "services_default", "parameters", "transient_local"],
)
def test_late_observer_receives_cache_only_with_explicit_durability(
    live_graph: LiveGraph, profile: str
) -> None:
    from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
    from std_msgs.msg import String

    topic = live_graph.namespace + "/retained"
    # This regression uses the Jazzy/Fast DDS default cohort, not universal RMW defaults.
    # The offered cache has one sample; the observer's named profile keeps at most ten.
    publisher = live_graph.producer.create_publisher(
        String,
        topic,
        QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        ),
    )
    try:
        # No timer or later publish supplies this sample after observer construction.
        publisher.publish(String(data="retained-before-observer"))
        graph: ExpectedGraph = {
            "topics": [
                {
                    "name": topic,
                    "type": "std_msgs/msg/String",
                    "min_publishers": 1,
                    "min_subscribers": 0,
                    "first_message_timeout_sec": 5,
                    "qos_profile": profile,
                }
            ],
            "services": [],
            "actions": [],
            "lifecycle_nodes": [],
        }
        with RosGraphObserver(graph, observe_clock=False) as observer:
            deadline = monotonic() + 10
            while observer.snapshot().topics[topic].publishers != 1:
                if monotonic() >= deadline:
                    pytest.fail("test publisher was not discovered")
                sleep(0.02)
            if profile == "transient_local":
                wait_for_readiness(
                    graph, observer, timeout_sec=5, stable_for_sec=0, poll_interval_sec=0.02
                )
                assert observer.snapshot().topics[topic].first_message_at_ns is not None
            else:
                end = monotonic() + 0.5
                while monotonic() < end:
                    assert observer.snapshot().topics[topic].first_message_at_ns is None
                    sleep(0.02)
                publisher.publish(String(data="fresh-after-observer"))
                wait_for_readiness(
                    graph, observer, timeout_sec=5, stable_for_sec=0, poll_interval_sec=0.02
                )
                assert observer.snapshot().topics[topic].first_message_at_ns is not None
            assert observer.snapshot().topics[topic].qos_compatible
    finally:
        live_graph.producer.destroy_publisher(publisher)
