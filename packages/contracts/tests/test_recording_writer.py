from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

import pytest
from mcap.opcode import Opcode
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
from tests.extension_support import SCHEMAS, with_extension
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


@pytest.mark.parametrize("extended", [False, True])
def test_recording_and_summary_are_both_bound_and_rechecked(tmp_path: Path, extended: bool) -> None:
    source = recording(tmp_path / "observations.mcap")
    output = tmp_path / "summary.json"
    assert main(["recording-summary", "from-mcap", str(source), "--output", str(output)]) == 0
    expected = output.read_bytes()
    assert main(["recording-summary", "from-mcap", str(source), "--output", str(output)]) == 0
    assert output.read_bytes() == expected
    if extended:
        write_document(with_extension(load_mapping(output)), output, extension_schemas=SCHEMAS)
        expected = output.read_bytes()
    metadata = artifact_metadata()
    metadata.update(kind="recording", media_type="application/mcap")
    draft = add_evidence_artifact(
        create_evidence_index(index_template()),
        source,
        metadata,
        recording_summary=output,
        extension_schemas=SCHEMAS,
    )
    result = finalize_evidence_index(draft, extension_schemas=SCHEMAS)
    assert result["artifacts"][0]["recording_summary"]["sha256"] == file_sha256(output)
    assert result["artifacts"][0]["sha256"] == file_sha256(source)
    output.write_bytes(expected + b"\n")
    with pytest.raises(WriterError, match="recording_summary"):
        finalize_evidence_index(draft, extension_schemas=SCHEMAS)


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


def test_oversized_chunks_are_rejected_before_decompression(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from robotics_runtime_contracts import _mcap_summary

    def decompressing_pass(_stream: object) -> None:
        raise AssertionError("chunk records were decompressed")

    source = recording(tmp_path / "recording.mcap")
    monkeypatch.setattr(_mcap_summary, "MAX_CHUNK_UNCOMPRESSED_BYTES", 16)
    monkeypatch.setattr(_mcap_summary, "_observed_statistics", decompressing_pass)

    with pytest.raises(WriterError, match="uncompressed bytes") as error:
        recording_summary_from_mcap(source)

    assert error.value.error_id == "writer.invalid_mcap"


def test_nested_chunk_length_is_bounded_before_upstream_allocation(tmp_path: Path) -> None:
    def envelope(opcode: Opcode, body: bytes) -> bytes:
        return struct.pack("<BQ", opcode, len(body)) + body

    # The outer envelope is tiny, but the nested data length requests 1 GiB.
    body = struct.pack("<QQQIIQ", 0, 0, 1, 0, 0, 1024**3) + b"x"
    magic = b"\x89MCAP0\r\n"
    source = tmp_path / "nested-length.mcap"
    source.write_bytes(
        magic
        + envelope(Opcode.CHUNK, body)
        + envelope(Opcode.DATA_END, struct.pack("<I", 0))
        + envelope(Opcode.FOOTER, struct.pack("<QQI", 0, 0, 0))
        + magic
    )
    with pytest.raises(WriterError, match="read requests 1073741824 bytes") as error:
        recording_summary_from_mcap(source)
    assert error.value.error_id == "writer.invalid_mcap"


@pytest.mark.parametrize("compression", list(CompressionType))
def test_raw_byte_budget_accepts_exact_complete_recording(
    tmp_path: Path, compression: CompressionType
) -> None:
    source = recording(tmp_path / "bounded.mcap", compression)
    expected = recording_summary_from_mcap(source)
    assert (
        recording_summary_from_mcap(source, max_raw_evidence_bytes=source.stat().st_size)
        == expected
    )
    assert recording_summary_from_mcap(source, max_raw_evidence_bytes=None) == expected


@pytest.mark.parametrize("budget", [0, -1, True, False, 1.5, "1"])
def test_invalid_raw_budget_precedes_optional_dependency_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, budget: object
) -> None:
    from typing import Any, cast

    monkeypatch.setitem(sys.modules, "robotics_runtime_contracts._mcap_summary", None)
    with pytest.raises(WriterError, match="positive integer or None") as caught:
        recording_summary_from_mcap(
            tmp_path / "unused.mcap", max_raw_evidence_bytes=cast(Any, budget)
        )
    assert caught.value.error_id == "writer.invalid_input"


def test_over_budget_refuses_source_before_read_or_parse_and_closes_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from io import FileIO
    from tempfile import TemporaryFile
    from typing import IO, Any

    from robotics_runtime_contracts import _mcap_summary

    # Many small records are individually valid but exceed the whole-file budget.
    source = tmp_path / "small-records.mcap"
    with source.open("wb") as stream:
        writer = Writer(stream, use_chunking=False)
        writer.start()
        schema = writer.register_schema("Example", "jsonschema", b"{}")
        channel = writer.register_channel("/small", "json", schema)
        for index in range(20):
            writer.add_message(channel, index, b"{}", index)
        writer.finish()
    original_open = Path.open
    original_temporary_file = TemporaryFile
    snapshots: list[IO[bytes]] = []
    reads: list[int] = []

    class SpySource(FileIO):
        def read(self, size: int | None = -1) -> bytes:
            assert size is not None
            reads.append(size)
            block = super().read(size)
            assert block is not None
            return block

    def source_open(path: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if path == source and mode == "rb":
            return SpySource(path, mode)
        return original_open(path, mode, *args, **kwargs)

    def private_snapshot() -> IO[bytes]:
        snapshot = original_temporary_file()
        snapshots.append(snapshot)
        return snapshot

    def parser(*_args: object) -> None:
        raise AssertionError("over-budget bytes reached MCAP parser")

    monkeypatch.setattr(Path, "open", source_open)
    monkeypatch.setattr(_mcap_summary, "TemporaryFile", private_snapshot)
    monkeypatch.setattr(_mcap_summary, "_summarize_stream", parser)
    with pytest.raises(WriterError, match="exceeds max_raw_evidence_bytes") as caught:
        recording_summary_from_mcap(source, max_raw_evidence_bytes=source.stat().st_size - 1)
    assert caught.value.error_id == "writer.invalid_mcap"
    assert reads == []
    assert len(snapshots) == 1 and snapshots[0].closed


def mutate_recording_source(source: Path, mutation: str, before: os.stat_result) -> None:
    if mutation == "growth":
        with source.open("ab") as writer:
            writer.write(b"extra bytes")
    elif mutation == "truncate":
        with source.open("r+b") as writer:
            writer.truncate(1)
    elif mutation == "mtime":
        os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns + 1))
    elif mutation == "ctime":
        with source.open("r+b") as writer:
            writer.write(b"x")
        # Restore size and mtime; ctime still records the in-place change.
        os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))


@pytest.mark.parametrize(
    "mutation,limited",
    [
        ("growth", True),
        ("growth", False),
        ("truncate", False),
        ("mtime", False),
        ("ctime", False),
        ("short_read", False),
    ],
)
def test_snapshot_refuses_source_drift_before_mcap_parse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str, limited: bool
) -> None:
    from io import FileIO
    from tempfile import TemporaryFile
    from typing import IO, Any

    from robotics_runtime_contracts import _mcap_summary

    source = recording(tmp_path / "changing.mcap")
    before = source.stat()
    original_open = Path.open
    original_temporary_file = TemporaryFile
    snapshots: list[IO[bytes]] = []
    reads: list[int] = []
    consumed = 0

    class SpySource(FileIO):
        def read(self, size: int | None = -1) -> bytes:
            nonlocal consumed
            assert size is not None
            reads.append(size)
            assert 0 < size <= 64
            if mutation == "short_read" and len(reads) > 1:
                return b""
            block = super().read(size)
            assert block is not None
            consumed += len(block)
            if len(reads) == 1:
                mutate_recording_source(source, mutation, before)
            return block

    def source_open(path: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if path == source and mode == "rb":
            return SpySource(path, mode)
        return original_open(path, mode, *args, **kwargs)

    def private_snapshot() -> IO[bytes]:
        snapshot = original_temporary_file()
        snapshots.append(snapshot)
        return snapshot

    def parser(*_args: object) -> None:
        raise AssertionError("changed source reached MCAP parser")

    monkeypatch.setattr(Path, "open", source_open)
    monkeypatch.setattr(_mcap_summary, "TemporaryFile", private_snapshot)
    monkeypatch.setattr(_mcap_summary, "_SNAPSHOT_BLOCK_BYTES", 64)
    monkeypatch.setattr(_mcap_summary, "_summarize_stream", parser)
    message = "exceeds max_raw_evidence_bytes" if limited else "source changed"
    with pytest.raises(WriterError, match=message) as caught:
        recording_summary_from_mcap(
            source, max_raw_evidence_bytes=before.st_size if limited else None
        )
    assert caught.value.error_id == "writer.invalid_mcap"
    if limited:
        assert consumed == before.st_size + 1
    assert len(snapshots) == 1 and snapshots[0].closed


def test_source_path_swap_between_parser_passes_preserves_private_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typing import IO

    from robotics_runtime_contracts import _mcap_summary

    source = recording(tmp_path / "original.mcap")
    expected = recording_summary_from_mcap(source)
    replacement = recording(tmp_path / "replacement.mcap", statistics=False)
    compressions = _mcap_summary._compressions

    def replace_source(stream: IO[bytes]) -> tuple[list[str], int]:
        result = compressions(stream)
        replacement.replace(source)
        return result

    monkeypatch.setattr(_mcap_summary, "_compressions", replace_source)
    actual = recording_summary_from_mcap(source, max_raw_evidence_bytes=source.stat().st_size)
    assert actual == expected
    assert actual["source_sha256"] != file_sha256(source)


@pytest.mark.parametrize("budget", ["0", "-1", "invalid", "under"])
def test_recording_cli_budget_failure_preserves_existing_output_and_diagnostics(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], budget: str
) -> None:
    import json

    source = recording(tmp_path / "input.mcap")
    output = tmp_path / "summary.json"
    output.write_bytes(b"previous output")
    supplied = str(source.stat().st_size - 1) if budget == "under" else budget
    result = main(
        [
            "--format",
            "json",
            "recording-summary",
            "from-mcap",
            str(source),
            "--output",
            str(output),
            "--max-raw-evidence-bytes",
            supplied,
        ]
    )
    assert result == (2 if budget == "invalid" else 1)
    assert output.read_bytes() == b"previous output"
    diagnostic = json.loads(capsys.readouterr().err)
    expected = (
        "cli.arguments_invalid"
        if budget == "invalid"
        else "writer.invalid_mcap"
        if budget == "under"
        else "writer.invalid_input"
    )
    assert diagnostic["error"]["error_id"] == expected


def test_recording_cli_exact_budget_retains_complete_summary(tmp_path: Path) -> None:
    source = recording(tmp_path / "input.mcap")
    expected = recording_summary_from_mcap(source)
    output = tmp_path / "summary.json"
    assert (
        main(
            [
                "recording-summary",
                "from-mcap",
                str(source),
                "--output",
                str(output),
                "--max-raw-evidence-bytes",
                str(source.stat().st_size),
            ]
        )
        == 0
    )
    assert load_mapping(output) == expected
