from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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


ResultWriter = Callable[[Mapping[str, Any], Path], Path]


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits; Windows uses inherited file ACLs")
@pytest.mark.parametrize("writer", [write_contract_json, write_junit_xml])
@pytest.mark.parametrize("mask,expected_mode", [(0o077, 0o600), (0o022, 0o644)])
def test_atomic_outputs_honor_umask(
    tmp_path: Path, writer: ResultWriter, mask: int, expected_mode: int
) -> None:
    result = build_acceptance_result(**result_inputs(tmp_path))
    previous = os.umask(mask)
    try:
        output = writer(result, tmp_path / "result")
        # The writer does not change the process mask for subsequent files.
        probe = tmp_path / "probe"
        probe.write_bytes(b"probe")
    finally:
        os.umask(previous)
    assert output.stat().st_mode & 0o777 == expected_mode
    assert probe.stat().st_mode & 0o777 == expected_mode


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits; Windows uses inherited file ACLs")
@pytest.mark.parametrize("writer", [write_contract_json, write_junit_xml])
@pytest.mark.parametrize("destination_mode", [0o600, 0o400, 0o640])
def test_atomic_outputs_retain_destination_restrictions(
    tmp_path: Path, writer: ResultWriter, destination_mode: int
) -> None:
    result = build_acceptance_result(**result_inputs(tmp_path))
    output = tmp_path / "result"
    output.write_bytes(b"previous result")
    output.chmod(destination_mode)
    retained = tmp_path / "previous"
    os.link(output, retained)
    previous = os.umask(0o022)
    try:
        assert writer(result, output) == output
    finally:
        os.umask(previous)
    assert output.stat().st_mode & 0o777 == destination_mode
    assert output.read_bytes() != b"previous result"
    assert retained.read_bytes() == b"previous result"
    assert output.stat().st_ino != retained.stat().st_ino


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits; Windows uses inherited file ACLs")
@pytest.mark.parametrize("writer", [write_contract_json, write_junit_xml])
def test_atomic_outputs_keep_private_symlink_targets(tmp_path: Path, writer: ResultWriter) -> None:
    result = build_acceptance_result(**result_inputs(tmp_path))
    destination = tmp_path / "target"
    destination.write_bytes(b"previous result")
    destination.chmod(0o600)
    link = tmp_path / "result"
    link.symlink_to(destination)
    previous = os.umask(0o022)
    try:
        assert writer(result, link) == destination
    finally:
        os.umask(previous)
    assert link.is_symlink()
    assert destination.stat().st_mode & 0o777 == 0o600
    assert destination.read_bytes() != b"previous result"


@pytest.mark.parametrize("writer", [write_contract_json, write_junit_xml])
def test_atomic_outputs_preserve_previous_file_on_publication_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, writer: ResultWriter
) -> None:
    result = build_acceptance_result(**result_inputs(tmp_path))
    output = tmp_path / "result"
    output.write_bytes(b"previous result")
    original_names = {path.name for path in tmp_path.iterdir()}

    def fail_replace(_source: object, _destination: object) -> None:
        raise OSError("replacement failed")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="replacement failed"):
        writer(result, output)
    assert output.read_bytes() == b"previous result"
    assert {path.name for path in tmp_path.iterdir()} == original_names


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits; Windows uses inherited file ACLs")
def test_exclusive_json_output_is_private_and_does_not_replace_an_existing_file(
    tmp_path: Path,
) -> None:
    result = build_acceptance_result(**result_inputs(tmp_path))
    output = tmp_path / "result.json"
    previous = os.umask(0o077)
    try:
        write_contract_json(result, output, replace=False)
    finally:
        os.umask(previous)
    original = output.read_bytes()
    original_names = {path.name for path in tmp_path.iterdir()}
    previous = os.umask(0o022)
    try:
        with pytest.raises(FileExistsError):
            write_contract_json(result, output, replace=False)
    finally:
        os.umask(previous)
    assert output.read_bytes() == original
    assert output.stat().st_mode & 0o777 == 0o600
    assert {path.name for path in tmp_path.iterdir()} == original_names
