"""Real upstream recordings exercise metadata and checksum validation boundaries."""

from collections.abc import Callable
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from typing import TypedDict
from zlib import crc32

import pytest
from mcap.data_stream import RecordBuilder
from mcap.opcode import Opcode
from mcap.reader import make_reader
from mcap.records import Channel, DataEnd, Footer, McapRecord, Schema, Statistics
from mcap.stream_reader import StreamReader
from mcap.writer import CompressionType, IndexType, Writer

from robotics_runtime_contracts import file_sha256, load_mapping
from robotics_runtime_contracts._mcap_crc import verify_extra_crcs
from robotics_runtime_contracts.cli import main
from robotics_runtime_contracts.recordings import recording_summary_from_mcap
from robotics_runtime_contracts.writers import WriterError, write_document

START_NS = 2**63 + 17
PAYLOAD = b"ATTACHMENT_PAYLOAD_A"


class Options(TypedDict, total=False):
    compression: CompressionType
    index_types: IndexType
    use_chunking: bool
    use_summary_offsets: bool
    enable_crcs: bool
    enable_data_crcs: bool
    repeat_channels: bool
    repeat_schemas: bool


def recording(path: Path, options: Options | None = None, payload: bytes = PAYLOAD) -> Path:
    selected: Options = {
        "compression": CompressionType.NONE,
        "index_types": IndexType.NONE,
        "use_chunking": False,
        "use_summary_offsets": False,
        "enable_crcs": False,
    }
    selected.update(options or {})
    with path.open("wb") as stream:
        writer = Writer(stream, **selected)
        writer.start()
        schema = writer.register_schema("Actual.Schema", "jsonschema", b'{"type":"object"}')
        channel = writer.register_channel("/actual", "json", schema)
        writer.add_message(channel, START_NS, b'{"x":1}', START_NS - 1)
        writer.add_message(channel, START_NS + 6, b'{"x":2}', START_NS + 5)
        writer.add_attachment(1, 1, "calibration-данные", "application/octet-stream", payload)
        writer.finish()
    return path


def rewrite(path: Path, transform: Callable[[McapRecord], McapRecord | None]) -> None:
    """Re-encode unindexed fixtures with upstream writers and a relocated footer.

    These fixtures disable DataEnd/summary CRCs and summary offsets so a mutation
    isolates definition/statistics checks, independently of checksum validation.
    """
    magic = path.read_bytes()[:8]
    with path.open("rb") as stream:
        records = list(StreamReader(stream).records)
    builder = RecordBuilder()
    summary_start = 0
    for original in records:
        record = transform(original)
        if record is None:
            continue
        if isinstance(record, Footer):
            record = replace(record, summary_start=summary_start, summary_crc=0)
        record.write(builder)
        if isinstance(record, DataEnd):
            summary_start = len(magic) + builder.count
    # MCAP 1.4 omits the annotation on this public buffer finalizer.
    finish: Callable[[], bytes] = builder.end
    path.write_bytes(magic + finish() + magic)


@pytest.mark.parametrize("chunking", [False, True])
@pytest.mark.parametrize(
    "repeat_channels,repeat_schemas", [(False, False), (False, True), (True, False)]
)
def test_optional_summary_copies_use_streamed_definitions(
    tmp_path: Path, chunking: bool, repeat_channels: bool, repeat_schemas: bool
) -> None:
    source = recording(
        tmp_path / "input.mcap",
        {
            "use_chunking": chunking,
            "repeat_channels": repeat_channels,
            "repeat_schemas": repeat_schemas,
        },
    )
    with source.open("rb") as stream:
        assert len(list(make_reader(stream).iter_messages())) == 2
    document = recording_summary_from_mcap(source)
    assert document["channels"] == [
        {
            "topic": "/actual",
            "schema_name": "Actual.Schema",
            "message_encoding": "json",
            "message_count": 2,
        }
    ]
    output = write_document(document, tmp_path / "summary.json")
    assert document["source_sha256"] == file_sha256(source)
    assert load_mapping(output)["statistics"]["message_start_time_ns"] == START_NS
    assert load_mapping(output)["statistics"]["message_end_time_ns"] == START_NS + 6


@pytest.mark.parametrize("definition", [b"/actual", b"Actual.Schema"])
def test_conflicting_summary_definition_is_rejected(tmp_path: Path, definition: bytes) -> None:
    source = recording(tmp_path / "input.mcap")
    raw = source.read_bytes()
    assert raw.count(definition) == 2
    offset = raw.rfind(definition)
    altered = bytes([definition[0] ^ 1]) + definition[1:]
    source.write_bytes(raw[:offset] + altered + raw[offset + len(definition) :])
    with pytest.raises(WriterError, match="conflicting MCAP") as caught:
        recording_summary_from_mcap(source)
    assert caught.value.error_id == "writer.invalid_mcap"


@pytest.mark.parametrize("missing", [Schema, Channel])
def test_summary_only_definition_cannot_rescue_missing_data_definition(
    tmp_path: Path, missing: type[Schema] | type[Channel]
) -> None:
    source = recording(tmp_path / "input.mcap")
    in_summary = False

    def remove_data_definition(record: McapRecord) -> McapRecord | None:
        nonlocal in_summary
        if isinstance(record, DataEnd):
            in_summary = True
        return None if isinstance(record, missing) and not in_summary else record

    rewrite(source, remove_data_definition)
    with pytest.raises(WriterError, match="undefined") as caught:
        recording_summary_from_mcap(source)
    assert caught.value.error_id == "writer.invalid_mcap"


def test_message_without_any_channel_definition_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "input.mcap"
    with source.open("wb") as stream:
        writer = Writer(stream, use_chunking=False, index_types=IndexType.NONE)
        writer.start()
        writer.add_message(999, 10, b"{}", 10)
        writer.finish()
    with pytest.raises(WriterError, match="undefined channel 999"):
        recording_summary_from_mcap(source)


@pytest.mark.parametrize(
    "counts,valid", [({}, True), ({1: 2}, True), ({1: 1}, False), ({1: 2, 999: 0}, False)]
)
def test_optional_channel_statistics_are_checked_when_available(
    tmp_path: Path, counts: dict[int, int], valid: bool
) -> None:
    source = recording(tmp_path / "input.mcap")

    def change_statistics(record: McapRecord) -> McapRecord:
        if isinstance(record, Statistics):
            return replace(record, channel_message_counts=counts)
        return record

    rewrite(source, change_statistics)
    if valid:
        document = recording_summary_from_mcap(source)
        assert document["statistics"]["message_count"] == 2
        assert document["channels"][0]["message_count"] == 2
    else:
        with pytest.raises(WriterError, match="per-channel Statistics"):
            recording_summary_from_mcap(source)


@pytest.mark.parametrize("corruption", ["attachment", "summary", "data"])
def test_nonzero_crc_corruption_preserves_existing_cli_output(
    tmp_path: Path, corruption: str
) -> None:
    source = recording(
        tmp_path / "input.mcap",
        {
            "enable_crcs": True,
            "enable_data_crcs": corruption == "data",
        },
    )
    raw = bytearray(source.read_bytes())
    offsets = {
        "attachment": raw.index(PAYLOAD),
        "summary": len(raw) - 12,
        "data": raw.index(b'"x":1') + 4,
    }
    raw[offsets[corruption]] ^= 1
    source.write_bytes(raw)
    with pytest.raises(WriterError) as caught:
        recording_summary_from_mcap(source)
    assert caught.value.error_id == "writer.invalid_mcap"
    output = tmp_path / "summary.json"
    output.write_bytes(b"existing output")
    assert main(["recording-summary", "from-mcap", str(source), "--output", str(output)]) == 1
    assert output.read_bytes() == b"existing output"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["input.mcap", "summary.json"]


def test_extra_crc_ranges_use_bounded_reads(tmp_path: Path) -> None:
    source = recording(tmp_path / "input.mcap", {"enable_crcs": True}, PAYLOAD * 10000)

    class BoundedStream(BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            assert size is not None and 0 <= size <= 64 * 1024
            return super().read(size)

    verify_extra_crcs(BoundedStream(source.read_bytes()))


def test_checksum_locator_rejects_oversized_record_without_reading_payload(tmp_path: Path) -> None:
    source = recording(tmp_path / "input.mcap")
    raw = bytearray(source.read_bytes())
    raw[9:17] = (2**64 - 1).to_bytes(8, "little")
    source.write_bytes(raw)
    with pytest.raises(WriterError, match="record extends past"):
        recording_summary_from_mcap(source)


def attachment_bounds(raw: bytes | bytearray) -> tuple[int, int]:
    position = 8
    while position < len(raw) - 8:
        length = int.from_bytes(raw[position + 1 : position + 9], "little")
        if raw[position] == Opcode.ATTACHMENT:
            return position, position + 9 + length
        position += 9 + length
    raise AssertionError("upstream fixture did not contain its attachment")


def test_crc_uses_attachment_fields_before_future_extension_bytes(tmp_path: Path) -> None:
    source = recording(tmp_path / "input.mcap", {"enable_crcs": True})
    raw = bytearray(source.read_bytes())
    start, end = attachment_bounds(raw)
    extension = b"future attachment fields"
    raw[end:end] = extension
    raw[start + 1 : start + 9] = (end - start - 9 + len(extension)).to_bytes(8, "little")
    # The real payload CRC is unchanged. Relocate the footer's summary pointer
    # and recompute its checksum; no indexes/summary offsets/DataEnd CRC exist.
    summary_start = int.from_bytes(raw[-28:-20], "little") + len(extension)
    raw[-28:-20] = summary_start.to_bytes(8, "little")
    raw[-12:-8] = crc32(raw[summary_start:-12]).to_bytes(4, "little")
    source.write_bytes(raw)
    document = recording_summary_from_mcap(source)
    assert document["statistics"]["attachment_count"] == 1
    assert document["source_sha256"] == file_sha256(source)


def test_attachment_length_prefix_cannot_escape_its_record(tmp_path: Path) -> None:
    source = recording(tmp_path / "input.mcap")
    raw = bytearray(source.read_bytes())
    start, _ = attachment_bounds(raw)
    # First string length follows the nine-byte envelope and two timestamps.
    raw[start + 25 : start + 29] = (2**32 - 1).to_bytes(4, "little")
    source.write_bytes(raw)
    with pytest.raises(WriterError, match="checksum field exceeds its record"):
        recording_summary_from_mcap(source)
