from __future__ import annotations

import lz4.frame  # type: ignore[import-untyped]
import pytest
import zstandard
from mcap.records import Chunk

from robotics_runtime_contracts._mcap_chunk_limits import validate_chunk_size
from robotics_runtime_contracts.writers import WriterError


def chunk(compression: str, payload: bytes, declared: int) -> Chunk:
    if compression == "lz4":
        data = lz4.frame.compress(payload, store_size=False)
    elif compression == "zstd":
        data = zstandard.ZstdCompressor(write_content_size=False).compress(payload)
    else:
        data = payload
    return Chunk(compression, data, 0, 0, 0, declared)


@pytest.mark.parametrize("compression", ["", "lz4", "zstd"])
def test_real_decoded_size_cannot_hide_behind_a_small_declared_size(compression: str) -> None:
    record = chunk(compression, b"x" * (1024 * 1024), 1)
    with pytest.raises(WriterError, match="decoded size contradicts") as error:
        validate_chunk_size(record, 2 * 1024 * 1024)
    assert error.value.error_id == "writer.invalid_mcap"


@pytest.mark.parametrize("compression", ["", "lz4", "zstd"])
@pytest.mark.parametrize("size", [0, 257, 1024 * 1024])
def test_bounded_streaming_preflight_accepts_real_frames(compression: str, size: int) -> None:
    validate_chunk_size(chunk(compression, b"x" * size, size), 2 * 1024 * 1024)


@pytest.mark.parametrize("compression", ["", "lz4", "zstd"])
def test_short_decoded_size_is_not_accepted(compression: str) -> None:
    with pytest.raises(WriterError, match="decoded size contradicts"):
        validate_chunk_size(chunk(compression, b"actual", 100), 1024 * 1024)


def test_declared_size_limit_is_enforced_before_opening_a_codec() -> None:
    # The invalid compressed data must not reach the codec.
    with pytest.raises(WriterError, match="the limit is 16"):
        validate_chunk_size(Chunk("zstd", b"invalid", 0, 0, 0, 17), 16)


@pytest.mark.parametrize("compression", ["lz4", "zstd"])
def test_codec_frame_size_is_checked_before_streaming(compression: str) -> None:
    payload = b"x" * 4096
    if compression == "lz4":
        data = lz4.frame.compress(payload)
    else:
        data = zstandard.ZstdCompressor().compress(payload)
    with pytest.raises(WriterError, match="frame size contradicts"):
        validate_chunk_size(Chunk(compression, data, 0, 0, 0, 1), 1024 * 1024)


def test_unfinished_zstd_frame_cannot_hide_a_giant_content_size() -> None:
    # Streaming yields 4096 bytes then EOF; upstream one-shot decoding trusts 1 GiB FCS.
    data = bytes.fromhex("28b52ffd8000000000404c00001078780100fb2b8005022000780220007802200078")
    assert zstandard.get_frame_parameters(data).content_size == 1024**3
    with pytest.raises(WriterError, match="frame size contradicts"):
        validate_chunk_size(Chunk("zstd", data, 0, 0, 0, 4096), 256 * 1024 * 1024)
