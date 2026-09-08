from __future__ import annotations

import sys
from pathlib import Path

import pytest
from mcap.writer import CompressionType, IndexType, Writer

from robotics_runtime_contracts import file_sha256, load_mapping, validate_document
from robotics_runtime_contracts.cli import main
from robotics_runtime_contracts.recordings import recording_summary_from_mcap
from robotics_runtime_contracts.writers import (
    WriterError,
    add_evidence_artifact,
    create_evidence_index,
    finalize_evidence_index,
    write_document,
)
from tests.test_writers import artifact_metadata, index_template


def recording(
    path: Path,
    compression: CompressionType = CompressionType.ZSTD,
    *,
    statistics: bool = True,
    chunking: bool = True,
    indexes: IndexType = IndexType.ALL,
) -> Path:
    with path.open("wb") as stream:
        writer = Writer(
            stream,
            compression=compression,
            use_statistics=statistics,
            use_chunking=chunking,
            index_types=indexes,
            enable_data_crcs=True,
        )
        writer.start()
        schema = writer.register_schema("example.Observation", "jsonschema", b'{"type":"object"}')
        first = writer.register_channel("/observations", "json", schema)
        second = writer.register_channel("/events", "json", schema)
        writer.register_channel("/unused", "json", schema)
        writer.add_message(first, 30, b'{"value":1}', 29)
        writer.add_message(second, 10, b'{"value":2}', 9)
        writer.add_attachment(5, 6, "readme", "text/plain", b"actual attachment")
        writer.add_metadata("producer", {"id": "fixture"})
        writer.finish()
    return path


@pytest.mark.parametrize("compression", list(CompressionType))
@pytest.mark.parametrize("indexes", [IndexType.ALL, IndexType.NONE])
def test_summary_counts_real_records_and_exact_bytes(
    tmp_path: Path,
    compression: CompressionType,
    indexes: IndexType,
) -> None:
    source = recording(tmp_path / "recording.mcap", compression, indexes=indexes)
    summary = recording_summary_from_mcap(source)
    validate_document(summary)
    assert summary["source_sha256"] == file_sha256(source)
    assert summary["statistics"] == {
        "message_count": 2,
        "schema_count": 1,
        "channel_count": 3,
        "attachment_count": 1,
        "metadata_count": 1,
        "chunk_count": 1,
        "message_start_time_ns": 10,
        "message_end_time_ns": 30,
    }
    assert summary["compressions"] == [compression.name.lower()]
    assert [(item["topic"], item["message_count"]) for item in summary["channels"]] == [
        ("/events", 1),
        ("/observations", 1),
        ("/unused", 0),
    ]


def test_unchunked_and_empty_recordings_have_observed_zero_counts(tmp_path: Path) -> None:
    source = recording(tmp_path / "unchunked.mcap", chunking=False)
    summary = recording_summary_from_mcap(source)
    assert summary["statistics"]["chunk_count"] == 0
    assert summary["compressions"] == ["none"]
    empty = tmp_path / "empty.mcap"
    with empty.open("wb") as stream:
        writer = Writer(stream)
        writer.start()
        writer.finish()
    summary = recording_summary_from_mcap(empty)
    assert summary["channels"] == []
    assert set(summary["statistics"].values()) == {0}


def test_missing_statistics_or_truncated_file_preserves_output(tmp_path: Path) -> None:
    source = recording(tmp_path / "incomplete.mcap", statistics=False)
    output = tmp_path / "summary.json"
    output.write_bytes(b"previous")
    assert main(["recording-summary", "from-mcap", str(source), "--output", str(output)]) == 1
    assert output.read_bytes() == b"previous"
    recording(source)
    source.write_bytes(source.read_bytes()[:-20])
    with pytest.raises(WriterError) as error:
        recording_summary_from_mcap(source)
    assert error.value.error_id == "writer.invalid_mcap"


def test_recording_and_summary_are_both_bound_and_rechecked(tmp_path: Path) -> None:
    source = recording(tmp_path / "observations.mcap")
    output = tmp_path / "summary.json"
    assert main(["recording-summary", "from-mcap", str(source), "--output", str(output)]) == 0
    expected = output.read_bytes()
    assert main(["recording-summary", "from-mcap", str(source), "--output", str(output)]) == 0
    assert output.read_bytes() == expected
    metadata = artifact_metadata()
    metadata.update(kind="recording", media_type="application/mcap")
    draft = add_evidence_artifact(
        create_evidence_index(index_template()), source, metadata, recording_summary=output
    )
    result = finalize_evidence_index(draft)
    assert result["artifacts"][0]["recording_summary"]["sha256"] == file_sha256(output)
    assert result["artifacts"][0]["sha256"] == file_sha256(source)
    output.write_bytes(expected + b"\n")
    with pytest.raises(WriterError, match="recording_summary"):
        finalize_evidence_index(draft)


def test_foreign_summary_and_schemaless_channel_are_rejected(tmp_path: Path) -> None:
    source = recording(tmp_path / "recording.mcap")
    summary = recording_summary_from_mcap(source)
    summary["source_sha256"] = "0" * 64
    output = write_document(summary, tmp_path / "foreign-summary.json")
    with pytest.raises(WriterError, match="different file bytes"):
        add_evidence_artifact(
            create_evidence_index(index_template()),
            source,
            artifact_metadata(),
            recording_summary=output,
        )
    with source.open("wb") as stream:
        writer = Writer(stream)
        writer.start()
        channel = writer.register_channel("/schemaless", "json", 0)
        writer.add_message(channel, 1, b"{}", 1)
        writer.finish()
    with pytest.raises(WriterError, match="named schema"):
        recording_summary_from_mcap(source)


def test_missing_optional_dependency_has_actionable_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "robotics_runtime_contracts._mcap_summary", None)
    with pytest.raises(WriterError) as error:
        recording_summary_from_mcap(tmp_path / "unused.mcap")
    assert error.value.error_id == "writer.missing_dependency"
    assert "[mcap]" in str(error.value)


def test_recording_output_cannot_replace_its_source(tmp_path: Path) -> None:
    source = recording(tmp_path / "recording.mcap")
    digest = file_sha256(source)
    assert main(["recording-summary", "from-mcap", str(source), "--output", str(source)]) == 1
    assert file_sha256(source) == digest
    assert load_mapping(write_document(recording_summary_from_mcap(source), tmp_path / "ok.json"))
