from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from mcap.writer import Writer

from robotics_runtime_contracts import (
    ContractError,
    DatasetValidationError,
    load_mapping,
    schema_for_role,
    validate_bag_metadata,
    validate_bag_summaries,
    validate_document,
    validate_role,
)
from robotics_runtime_contracts.qualification import (
    QualificationArtifact,
    QualificationError,
    load_qualification_artifact,
    validate_qualification_documents,
)
from robotics_runtime_contracts.recordings import recording_summary_from_mcap
from tests.support import qualification_specifications

FIXTURE = Path(__file__).parent / "fixtures/qualification/inference"


def reference(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {"uri": path.as_uri(), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}


def bag_fixture(
    root: Path, *, late_channel: bool = False
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    document = load_mapping(FIXTURE / "dataset.json")
    document["schema_version"] = "dataset-manifest.v2"
    document.pop("artifact", None)
    document.pop("bag", None)
    document["source"] = "simulation"
    document["topic_remaps"] = []
    members, summaries = [], []
    for index, times in enumerate(((100, 110), (120, 135))):
        path = root / f"recording_{index}.mcap"
        with path.open("wb") as stream:
            writer = Writer(stream)
            writer.start()
            clock_schema = writer.register_schema(
                name="rosgraph_msgs/msg/Clock", encoding="ros2msg", data=b"time clock"
            )
            clock = writer.register_channel(
                topic="/clock", message_encoding="cdr", schema_id=clock_schema
            )
            for timestamp in times:
                writer.add_message(clock, log_time=timestamp, publish_time=timestamp, data=b"clock")
            if not late_channel or index:
                probe_schema = writer.register_schema(
                    name="std_msgs/msg/UInt64", encoding="ros2msg", data=b"uint64 data"
                )
                probe = writer.register_channel(
                    topic="/sequence", message_encoding="cdr", schema_id=probe_schema
                )
                writer.add_message(
                    probe, log_time=times[0] + 1, publish_time=times[0] + 1, data=b"sequence"
                )
            writer.finish()
        summary = recording_summary_from_mcap(path, max_raw_evidence_bytes=2097152)
        summary_path = root / f"summary_{index}.json"
        summary_path.write_text(json.dumps(summary, sort_keys=True))
        members.append(
            {
                "segment_index": index,
                "relative_path": path.name,
                "recording": reference(path),
                "recording_summary": reference(summary_path),
            }
        )
        summaries.append(summary)
    document["channels"] = [
        {
            "topic": topic,
            "type": message_type,
            "type_hash": "RIHS01_" + "a" * 64,
            "qos_profile": "sensor_data",
            "message_count": count,
        }
        for topic, message_type, count in (
            ("/clock", "rosgraph_msgs/msg/Clock", 4),
            ("/sequence", "std_msgs/msg/UInt64", 1 if late_channel else 2),
        )
    ]
    total = 5 if late_channel else 6
    document["time"].update(basis="system_time", start_ns=100, end_ns=135, clock_jumps=[])
    source_scenario, source_runtime = root / "source-scenario.json", root / "source-runtime.json"
    source_scenario.write_bytes((FIXTURE / "scenario.json").read_bytes())
    source_runtime.write_bytes((FIXTURE / "runtime.json").read_bytes())
    document["provenance"].update(
        capture_run_id="source-run",
        scenario_sha256=reference(source_scenario)["sha256"],
        runtime_manifest_sha256=reference(source_runtime)["sha256"],
    )
    metadata = {
        "rosbag2_bagfile_information": {
            "version": 9,
            "storage_identifier": "mcap",
            "relative_file_paths": [member["relative_path"] for member in members],
            "files": [
                {
                    "path": member["relative_path"],
                    "starting_time": {
                        "nanoseconds_since_epoch": summary["statistics"]["message_start_time_ns"]
                    },
                    "duration": {
                        "nanoseconds": summary["statistics"]["message_end_time_ns"]
                        - summary["statistics"]["message_start_time_ns"]
                    },
                    "message_count": summary["statistics"]["message_count"],
                }
                for member, summary in zip(members, summaries, strict=True)
            ],
            "starting_time": {"nanoseconds_since_epoch": 100},
            "duration": {"nanoseconds": 35},
            "message_count": total,
            "topics_with_message_count": [
                {
                    "topic_metadata": {
                        "name": channel["topic"],
                        "type": channel["type"],
                        "type_description_hash": channel["type_hash"],
                        "offered_qos_profiles": [{"reliability": "best_effort"}],
                    },
                    "message_count": channel["message_count"],
                }
                for channel in document["channels"]
            ],
            "custom_data": {
                "run_id": "source-run",
                "record_timestamp_basis": "system_time",
                "dataset_license": document["governance"]["license"],
                "data_classification": document["governance"]["data_classification"],
                "retention_class": document["governance"]["retention_class"],
                "captured_at": document["provenance"]["captured_at"],
            },
        }
    }
    metadata_path = root / "metadata.yaml"
    metadata_path.write_text(json.dumps(metadata, sort_keys=True))
    document["bag"] = {
        "storage_id": "mcap",
        "metadata": reference(metadata_path),
        "members": members,
        "message_count": total,
    }
    validate_document(document)
    return document, metadata, summaries


def qualification_items(root: Path, document: dict[str, Any]) -> list[QualificationArtifact]:
    from robotics_runtime_contracts.qualification import inspect_qualification_artifacts

    report = inspect_qualification_artifacts(qualification_specifications("inference"))
    report.raise_for_errors()
    items = list(report.artifacts)
    items = [
        item
        for item in items
        if item.subject_name
        not in {
            "recording-summaries/dataset.json",
            "datasets/metadata.yaml",
            "datasets/capture-scenario.json",
            "datasets/capture-runtime.json",
        }
    ]
    old = next(item for item in items if item.kind == "dataset_manifest")
    dataset_path = root / "dataset.json"
    dataset_path.write_text(json.dumps(document, sort_keys=True))
    new = load_qualification_artifact(f"dataset_manifest:{old.subject_name}={dataset_path}")
    items[items.index(old)] = new
    for item in items:
        if item.kind in {"scenario", "domain_result"}:
            assert isinstance(item.document, dict)
            item.document["dataset_manifest_sha256"] = new.sha256
    items.append(
        load_qualification_artifact(
            f"other_evidence:source/metadata.yaml={root / 'metadata.yaml'}",
            native_metadata_references={
                document["bag"]["metadata"]["sha256"]: document["bag"]["metadata"]["size_bytes"]
            },
        )
    )
    for member in document["bag"]["members"]:
        index = member["segment_index"]
        items.extend(
            (
                load_qualification_artifact(
                    f"recording:source/{member['relative_path']}={root / member['relative_path']}"
                ),
                load_qualification_artifact(
                    f"recording_summary:recording-summaries/source-{index}.json="
                    f"{root / f'summary_{index}.json'}"
                ),
            )
        )
    for name in ("source-scenario.json", "source-runtime.json"):
        items.append(load_qualification_artifact(f"other_evidence:source/{name}={root / name}"))
    return items


def test_complete_closed_bag_preserves_native_gap_and_late_channel(tmp_path: Path) -> None:
    document, metadata, summaries = bag_fixture(tmp_path, late_channel=True)
    validate_role(document, "dataset_manifest")
    validate_bag_summaries(document, summaries)
    validate_bag_metadata(document, metadata, summaries, expected_run_id="source-run")
    assert document["time"]["end_ns"] - document["time"]["start_ns"] == 35
    assert (
        sum(
            item["duration"]["nanoseconds"]
            for item in metadata["rosbag2_bagfile_information"]["files"]
        )
        == 25
    )
    assert summaries[0]["statistics"]["message_count"] == 2
    assert summaries[1]["statistics"]["message_count"] == 3


def test_singleton_bag_is_current_canonical_model() -> None:
    from robotics_runtime_contracts.qualification import validate_qualification_artifacts

    assert schema_for_role("dataset_manifest") == "dataset-manifest.v2"
    validate_role(load_mapping(FIXTURE / "dataset.json"), "dataset_manifest")
    validate_qualification_artifacts(qualification_specifications("inference"))


def test_v2_raw_and_typed_summary_closure_qualifies(tmp_path: Path) -> None:
    document, _, _ = bag_fixture(tmp_path)
    validate_qualification_documents(qualification_items(tmp_path, document))


@pytest.mark.parametrize(
    "missing",
    [
        "source/recording_0.mcap",
        "source/recording_1.mcap",
        "source/metadata.yaml",
        "recording-summaries/source-1.json",
        "source/source-runtime.json",
    ],
)
def test_incomplete_bag_cannot_qualify(tmp_path: Path, missing: str) -> None:
    document, _, _ = bag_fixture(tmp_path)
    items = [
        item for item in qualification_items(tmp_path, document) if item.subject_name != missing
    ]
    with pytest.raises(QualificationError):
        validate_qualification_documents(items)


@pytest.mark.parametrize("subject", ["source/recording_1.mcap", "source/metadata.yaml"])
def test_changed_raw_bytes_or_size_cannot_use_old_identity(tmp_path: Path, subject: str) -> None:
    document, _, _ = bag_fixture(tmp_path)
    items = qualification_items(tmp_path, document)
    index = next(i for i, item in enumerate(items) if item.subject_name == subject)
    original = items[index]
    items[index] = replace(original, size_bytes=original.size_bytes + 1)
    with pytest.raises(QualificationError):
        validate_qualification_documents(items)
    items[index] = replace(original, sha256="f" * 64)
    with pytest.raises(QualificationError):
        validate_qualification_documents(items)


def test_duplicate_retained_member_alias_cannot_qualify(tmp_path: Path) -> None:
    document, _, _ = bag_fixture(tmp_path)
    items = qualification_items(tmp_path, document)
    raw = next(item for item in items if item.subject_name == "source/recording_0.mcap")
    items.append(replace(raw, subject_name="source/alias.mcap"))
    with pytest.raises(QualificationError, match="exactly one"):
        validate_qualification_documents(items)


@pytest.mark.parametrize(
    "change",
    [
        "reorder",
        "missing",
        "duplicate",
        "summary-source",
        "total-count",
        "channel-count",
        "time-span",
        "run",
        "governance",
        "basis",
    ],
)
def test_native_metadata_and_summary_contradictions_are_refused(
    tmp_path: Path, change: str
) -> None:
    document, metadata, summaries = bag_fixture(tmp_path)
    info = metadata["rosbag2_bagfile_information"]
    if change == "reorder":
        info["relative_file_paths"].reverse()
    elif change == "missing":
        info["files"].pop()
    elif change == "duplicate":
        info["relative_file_paths"][1] = info["relative_file_paths"][0]
    elif change == "summary-source":
        summaries[1]["source_sha256"] = summaries[0]["source_sha256"]
    elif change == "total-count":
        info["message_count"] += 1
    elif change == "channel-count":
        info["topics_with_message_count"][0]["message_count"] += 1
    elif change == "time-span":
        info["duration"]["nanoseconds"] = 25
    elif change == "run":
        info["custom_data"]["run_id"] = "another-run"
    elif change == "governance":
        info["custom_data"]["data_classification"] = "public"
    else:
        info["custom_data"]["record_timestamp_basis"] = "ros_time"
    with pytest.raises(DatasetValidationError):
        validate_bag_metadata(document, metadata, summaries, expected_run_id="source-run")


@pytest.mark.parametrize(
    "path",
    [
        "../escape.mcap",
        "/absolute.mcap",
        "./recording_0.mcap",
        "a//b.mcap",
        "bad" + chr(92) + "file.mcap",
    ],
)
def test_member_paths_cannot_escape_or_alias(tmp_path: Path, path: str) -> None:
    document, _, _ = bag_fixture(tmp_path)
    document["bag"]["members"][0]["relative_path"] = path
    with pytest.raises(ContractError):
        validate_document(document)


def test_unknown_v3_is_not_admitted_as_either_known_version(tmp_path: Path) -> None:
    document, _, _ = bag_fixture(tmp_path)
    document["schema_version"] = "dataset-manifest.v3"
    with pytest.raises(ContractError):
        validate_document(document)
    with pytest.raises(ContractError):
        validate_role(document, "dataset_manifest")


def test_native_byte_snapshot_is_required_for_opaque_metadata_ref(tmp_path: Path) -> None:
    document, _, _ = bag_fixture(tmp_path)
    items = qualification_items(tmp_path, document)
    index = next(i for i, item in enumerate(items) if item.subject_name == "source/metadata.yaml")
    items[index] = replace(items[index], native_metadata_bytes=None)
    with pytest.raises(QualificationError, match="captured byte snapshot"):
        validate_qualification_documents(items)


def test_reordered_actual_metadata_bytes_cannot_qualify(tmp_path: Path) -> None:
    document, metadata, _ = bag_fixture(tmp_path)
    metadata["rosbag2_bagfile_information"]["relative_file_paths"].reverse()
    path = tmp_path / "metadata.yaml"
    path.write_text(json.dumps(metadata, sort_keys=True))
    document["bag"]["metadata"] = reference(path)
    with pytest.raises(QualificationError, match="native member order"):
        validate_qualification_documents(qualification_items(tmp_path, document))


def test_explicit_metadata_loader_hashes_and_parses_one_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from robotics_runtime_contracts import _qualification_files as loader

    document, metadata, _ = bag_fixture(tmp_path)
    reference = document["bag"]["metadata"]
    observed = []
    from robotics_runtime_contracts.serialization import read_document_bytes

    original = read_document_bytes

    def capture(path: Path) -> bytes:
        observed.append(path)
        return original(path)

    monkeypatch.setattr(loader, "read_document_bytes", capture)
    item = load_qualification_artifact(
        f"other_evidence:metadata.yaml={tmp_path / 'metadata.yaml'}",
        native_metadata_references={reference["sha256"]: reference["size_bytes"]},
    )
    assert observed == [tmp_path / "metadata.yaml"]
    assert item.native_metadata_bytes == (tmp_path / "metadata.yaml").read_bytes()
    assert (item.sha256, item.size_bytes) == (reference["sha256"], reference["size_bytes"])


def test_fabricated_metadata_bytes_cannot_reuse_snapshot_identity(tmp_path: Path) -> None:
    document, _, _ = bag_fixture(tmp_path)
    items = qualification_items(tmp_path, document)
    index = next(i for i, item in enumerate(items) if item.subject_name == "source/metadata.yaml")
    items[index] = replace(items[index], native_metadata_bytes=b"{}")
    with pytest.raises(QualificationError, match="do not match"):
        validate_qualification_documents(items)


def test_retained_native_type_hash_and_custom_qos_are_authority(tmp_path: Path) -> None:
    document, metadata, summaries = bag_fixture(tmp_path)
    metadata["rosbag2_bagfile_information"]["topics_with_message_count"][0]["topic_metadata"][
        "type_description_hash"
    ] = "RIHS01_" + "b" * 64
    with pytest.raises(DatasetValidationError, match="type hash"):
        validate_bag_metadata(document, metadata, summaries)
    document, metadata, summaries = bag_fixture(tmp_path)
    document["channels"][0].update(qos_profile="custom", qos_profile_sha256="f" * 64)
    with pytest.raises(DatasetValidationError, match="QoS metadata"):
        validate_bag_metadata(document, metadata, summaries)


def test_canonical_v2_extensions_must_be_registered(tmp_path: Path) -> None:
    document, _, _ = bag_fixture(tmp_path)
    document["extensions"] = {"org.example.unregistered": {"claimed": True}}
    with pytest.raises(ContractError):
        validate_document(document)


def test_confined_nested_members_preserve_native_metadata_order(tmp_path: Path) -> None:
    document, metadata, summaries = bag_fixture(tmp_path)
    info = metadata["rosbag2_bagfile_information"]
    for member, item in zip(document["bag"]["members"], info["files"], strict=True):
        name = "nested/" + member["relative_path"]
        member["relative_path"] = name
        item["path"] = name
    info["relative_file_paths"] = [member["relative_path"] for member in document["bag"]["members"]]
    validate_document(document)
    validate_bag_metadata(document, metadata, summaries, expected_run_id="source-run")


@pytest.mark.parametrize(
    "name", ["system_default", "sensor_data", "services_default", "parameters", "transient_local"]
)
def test_dataset_accepts_supported_named_qos(tmp_path: Path, name: str) -> None:
    document, _metadata, _summaries = bag_fixture(tmp_path)
    document["channels"][0]["qos_profile"] = name
    validate_document(document)
