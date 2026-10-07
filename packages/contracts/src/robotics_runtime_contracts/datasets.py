"""Identity and native metadata checks for a complete recorded bag dataset."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any

from robotics_runtime_contracts.errors import ContractError


class DatasetValidationError(ContractError):
    """A complete dataset contradicts its retained native recording facts."""

    error_id = "dataset.invalid"


def _require(label: str, expected: Any, actual: Any) -> None:
    if expected != actual or (isinstance(expected, int) and type(actual) is not int):
        raise DatasetValidationError(f"{label} does not match the complete dataset")


def validate_bag_structure(document: Mapping[str, Any]) -> None:
    """Check order and uniqueness without dereferencing producer-owned URIs."""
    bag = document["bag"]
    members = bag["members"]
    paths: set[str] = set()
    recordings: set[str] = set()
    summaries: set[str] = set()
    uris: set[str] = {bag["metadata"]["uri"]}
    for index, member in enumerate(members):
        name = member["relative_path"]
        path = PurePosixPath(name)
        if (
            path.is_absolute()
            or chr(92) in name
            or any(part in {"", ".", ".."} for part in name.split("/"))
            or any(ord(character) < 32 or ord(character) == 127 for character in name)
            or path.suffix != ".mcap"
        ):
            raise DatasetValidationError("bag member path must be a confined relative MCAP path")
        _require("bag member segment index", index, member["segment_index"])
        if name in paths or member["recording"]["sha256"] in recordings:
            raise DatasetValidationError(
                "bag members must have unique paths and recording identities"
            )
        if member["recording_summary"]["sha256"] in summaries:
            raise DatasetValidationError(
                "bag members must have distinct recording summary identities"
            )
        paths.add(name)
        recordings.add(member["recording"]["sha256"])
        summaries.add(member["recording_summary"]["sha256"])
        for reference in (member["recording"], member["recording_summary"]):
            if reference["uri"] in uris:
                raise DatasetValidationError("bag references must not alias one URI")
            uris.add(reference["uri"])


def validate_bag_summaries(
    document: Mapping[str, Any], summaries: Sequence[Mapping[str, Any]]
) -> None:
    """Bind every ordered member to its typed finalized summary and aggregate facts."""
    validate_bag_structure(document)
    members = document["bag"]["members"]
    _require("bag summary cardinality", len(members), len(summaries))
    counts: Counter[tuple[str, str]] = Counter()
    intervals: list[tuple[int, int]] = []
    total = 0
    for member, summary in zip(members, summaries, strict=True):
        _require("member summary source", member["recording"]["sha256"], summary["source_sha256"])
        stats = summary["statistics"]
        count = stats["message_count"]
        total += count
        for channel in summary["channels"]:
            counts[(channel["topic"], channel["schema_name"])] += channel["message_count"]
        if count:
            start, end = stats["message_start_time_ns"], stats["message_end_time_ns"]
            intervals.append((start, end))
    _require("bag message count", document["bag"]["message_count"], total)
    expected = {
        (channel["topic"], channel["type"]): channel["message_count"]
        for channel in document["channels"]
    }
    _require("bag channel counts", Counter(expected), counts)
    if not intervals:
        raise DatasetValidationError("bag dataset has no recorded messages")
    _require("bag start time", document["time"]["start_ns"], min(start for start, _ in intervals))
    _require("bag end time", document["time"]["end_ns"], max(end for _, end in intervals))


def _validate_bag_metadata(
    document: Mapping[str, Any],
    metadata: Mapping[str, Any],
    summaries: Sequence[Mapping[str, Any]],
    *,
    expected_run_id: str | None = None,
) -> None:
    """Compare unchanged native rosbag2 metadata to the same finalized member set."""
    validate_bag_summaries(document, summaries)
    info = metadata["rosbag2_bagfile_information"]
    names = [member["relative_path"] for member in document["bag"]["members"]]
    _require("native storage", "mcap", info["storage_identifier"])
    _require("native member order", names, info["relative_file_paths"])
    files = info["files"]
    _require("native file order", names, [item["path"] for item in files])
    _require("native message count", document["bag"]["message_count"], info["message_count"])
    for item, summary in zip(files, summaries, strict=True):
        stats = summary["statistics"]
        _require("native member count", stats["message_count"], item["message_count"])
        if stats["message_count"]:
            _require(
                "native member start",
                stats["message_start_time_ns"],
                item["starting_time"]["nanoseconds_since_epoch"],
            )
            _require(
                "native member duration",
                stats["message_end_time_ns"] - stats["message_start_time_ns"],
                item["duration"]["nanoseconds"],
            )
    _require(
        "native bag start",
        document["time"]["start_ns"],
        info["starting_time"]["nanoseconds_since_epoch"],
    )
    _require(
        "native bag duration",
        document["time"]["end_ns"] - document["time"]["start_ns"],
        info["duration"]["nanoseconds"],
    )
    actual_counts = {
        (item["topic_metadata"]["name"], item["topic_metadata"]["type"]): item["message_count"]
        for item in info["topics_with_message_count"]
    }
    if len(actual_counts) != len(info["topics_with_message_count"]):
        raise DatasetValidationError("native channel inventory contains duplicate identities")
    expected_counts = {
        (channel["topic"], channel["type"]): channel["message_count"]
        for channel in document["channels"]
    }
    _require("native channel counts", expected_counts, actual_counts)
    topics = {
        item["topic_metadata"]["name"]: item["topic_metadata"]
        for item in info["topics_with_message_count"]
    }
    for channel in document["channels"]:
        native = topics[channel["topic"]]
        _require("native channel type hash", channel["type_hash"], native["type_description_hash"])
        if channel["qos_profile"] == "custom":
            if not native["offered_qos_profiles"]:
                raise DatasetValidationError("native custom QoS must retain its offered profiles")
            _require(
                "native channel QoS metadata",
                document["bag"]["metadata"]["sha256"],
                channel["qos_profile_sha256"],
            )
    custom = info["custom_data"]
    if expected_run_id is not None:
        _require("native capture run", expected_run_id, custom["run_id"])
    _require(
        "native recorded time basis", document["time"]["basis"], custom["record_timestamp_basis"]
    )
    for dataset_key, native_key in (
        ("license", "dataset_license"),
        ("data_classification", "data_classification"),
        ("retention_class", "retention_class"),
    ):
        _require(
            "native capture governance", document["governance"][dataset_key], custom[native_key]
        )
    _require(
        "native capture timestamp", document["provenance"]["captured_at"], custom["captured_at"]
    )


def validate_bag_metadata(
    document: Mapping[str, Any],
    metadata: Mapping[str, Any],
    summaries: Sequence[Mapping[str, Any]],
    *,
    expected_run_id: str | None = None,
) -> None:
    """Refuse incomplete native metadata as a contract failure, not a loader crash."""
    try:
        _validate_bag_metadata(document, metadata, summaries, expected_run_id=expected_run_id)
    except DatasetValidationError:
        raise
    except (KeyError, TypeError, IndexError, ValueError) as error:
        raise DatasetValidationError("native bag metadata is incomplete or malformed") from error


__all__ = [
    "DatasetValidationError",
    "validate_bag_metadata",
    "validate_bag_structure",
    "validate_bag_summaries",
]
