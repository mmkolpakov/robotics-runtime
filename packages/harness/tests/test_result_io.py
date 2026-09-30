from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from robotics_acceptance_harness import ros
from robotics_acceptance_harness.result import (
    build_acceptance_result,
    write_contract_json,
    write_junit_xml,
)
from tests.test_result import result_inputs
from tests.test_ros import FakeNode, expected_graph, fake_modules


def test_ros_document_timestamps_use_wall_time_while_duration_clock_stays_monotonic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wall_ns = 1785067200123456789
    monkeypatch.setattr(ros, "time_ns", lambda: wall_ns)
    monkeypatch.setattr(ros, "monotonic_ns", lambda: 700)
    node = FakeNode()
    graph = expected_graph()
    graph["topics"].append(
        {
            **graph["topics"][0],
            "name": "/clock",
            "type": "rosgraph_msgs/msg/Clock",
        }
    )
    with ros.RosGraphObserver(
        graph,
        observe_clock=True,
        module_loader=fake_modules(node).__getitem__,
    ) as observer:
        observer.start_clock_observation()
        node.callbacks["/clock"](SimpleNamespace(clock=SimpleNamespace(sec=1, nanosec=2)))
        observer.snapshot()
        snapshot = observer.snapshot()
        assert snapshot.topics["/camera/image"].first_message_at_ns == wall_ns
        assert snapshot.topics["/clock"].first_message_at_ns == wall_ns
        assert snapshot.lifecycle_nodes["/camera"].observed_at_ns == wall_ns
        assert snapshot.observed_at_ns == 700
        assert observer.stop_clock_observation()[0].observed_at_ns == 700


def test_observed_type_selection_is_independent_of_discovery_order(tmp_path: Path) -> None:
    inputs = result_inputs(tmp_path)
    readiness = inputs["readiness"]
    topic = readiness.snapshot.topics["/clock"]
    results = []
    for types in (
        ("zzz/msg/Alternate", "rosgraph_msgs/msg/Clock"),
        ("rosgraph_msgs/msg/Clock", "zzz/msg/Alternate"),
    ):
        inputs["readiness"] = replace(
            readiness,
            snapshot=replace(readiness.snapshot, topics={"/clock": replace(topic, types=types)}),
        )
        results.append(build_acceptance_result(**inputs)["observed_ros_graph"])
    assert results[0] == results[1]


def test_atomic_outputs_are_readable_under_a_private_umask(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("POSIX mode bits; Windows uses inherited file ACLs")
    result = build_acceptance_result(**result_inputs(tmp_path))
    previous = os.umask(0o077)
    try:
        outputs = (
            write_contract_json(result, tmp_path / "result.json"),
            write_junit_xml(result, tmp_path / "junit.xml"),
        )
    finally:
        os.umask(previous)
    assert all(path.stat().st_mode & 0o777 == 0o644 for path in outputs)
