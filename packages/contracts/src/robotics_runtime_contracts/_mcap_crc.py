"""Verify the two CRC kinds not covered by MCAP 1.4's public StreamReader.

This is a checksum-range locator, not an MCAP decoder. It skips top-level
records using their fixed nine-byte envelopes and reads only attachment length
prefixes and the fixed footer. Decoding, decompression and data/chunk CRCs remain
upstream responsibilities. Attachment extension bytes after its CRC are allowed.
Ranges cover original bytes, never reserialized records, in bounded read blocks.
See https://mcap.dev/spec (Attachment and Footer).
"""

from typing import IO
from zlib import crc32

from mcap.opcode import Opcode
from mcap.stream_reader import MAGIC_SIZE

from robotics_runtime_contracts.writers import WriterError


def _invalid(message: str) -> WriterError:
    return WriterError(message, error_id="writer.invalid_mcap")


def _read_integer(stream: IO[bytes], size: int, end: int) -> int:
    if stream.tell() + size > end:
        raise _invalid("truncated MCAP checksum fields")
    raw = stream.read(size)
    if len(raw) != size:
        raise _invalid("truncated MCAP checksum fields")
    return int.from_bytes(raw, "little")


def _skip(stream: IO[bytes], size: int, end: int) -> None:
    destination = stream.tell() + size
    if destination > end:
        raise _invalid("MCAP checksum field exceeds its record")
    stream.seek(destination)


def _check_crc(stream: IO[bytes], start: int, end: int, label: str) -> None:
    stream.seek(end)
    expected = _read_integer(stream, 4, end + 4)
    if expected == 0:
        return  # The format explicitly permits an unavailable checksum.
    stream.seek(start)
    actual = 0
    remaining = end - start
    while remaining:
        block = stream.read(min(remaining, 64 * 1024))
        if not block:
            raise _invalid(f"truncated MCAP {label} checksum range")
        actual = crc32(block, actual)
        remaining -= len(block)
    if actual != expected:
        raise _invalid(f"MCAP {label} CRC mismatch")


def _attachment_crc(stream: IO[bytes], start: int, end: int) -> None:
    # Two timestamps, two length-prefixed strings, then uint64-prefixed data.
    stream.seek(start)
    _skip(stream, 16, end)
    for _ in range(2):
        _skip(stream, _read_integer(stream, 4, end), end)
    _skip(stream, _read_integer(stream, 8, end), end)
    crc_offset = stream.tell()
    if crc_offset + 4 > end:
        raise _invalid("truncated MCAP attachment CRC")
    _check_crc(stream, start, crc_offset, "attachment")


def _footer_crc(stream: IO[bytes], start: int, end: int) -> None:
    if end - start != 20:
        raise _invalid("invalid MCAP footer length")
    stream.seek(start)
    summary_start = _read_integer(stream, 8, end)
    if summary_start and not MAGIC_SIZE <= summary_start <= start - 9:
        raise _invalid("invalid MCAP summary checksum range")
    # With no summary records the checksum covers only the footer prefix.
    _check_crc(stream, summary_start or start - 9, end - 4, "summary")


def verify_extra_crcs(stream: IO[bytes]) -> None:
    """Check attachment/summary CRCs in the same seekable snapshot as the reader."""
    limit = stream.seek(0, 2) - MAGIC_SIZE
    position = MAGIC_SIZE
    while position < limit:
        stream.seek(position)
        opcode = _read_integer(stream, 1, limit)
        length = _read_integer(stream, 8, limit)
        start = stream.tell()
        end = start + length
        if end > limit:
            raise _invalid("MCAP record extends past the trailing magic")
        if opcode == Opcode.ATTACHMENT:
            _attachment_crc(stream, start, end)
        elif opcode == Opcode.FOOTER:
            if end != limit:
                raise _invalid("MCAP footer must be the last record")
            _footer_crc(stream, start, end)
        position = end
    stream.seek(0)
