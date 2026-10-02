"""Check actual chunk sizes with the codecs' bounded streaming readers."""

from contextlib import closing
from io import BytesIO
from typing import IO, cast

import lz4.frame  # type: ignore[import-untyped]  # LZ4 does not ship typing metadata.
from mcap.records import Chunk
from zstandard import CONTENTSIZE_UNKNOWN, ZstdDecompressor, get_frame_parameters

from robotics_runtime_contracts.writers import WriterError


class BoundedReadStream:
    """Reject oversized individual read requests before the upstream allocation."""

    def __init__(self, stream: IO[bytes], limit: int) -> None:
        self.stream = stream
        self.limit = limit

    def read(self, size: int = -1) -> bytes:
        if size < 0 or size > self.limit:
            raise WriterError(
                f"MCAP read requests {size} bytes; the limit is {self.limit}",
                error_id="writer.invalid_mcap",
            )
        return self.stream.read(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self.stream.seek(offset, whence)

    def tell(self) -> int:
        return self.stream.tell()


def _reader(chunk: Chunk, limit: int) -> IO[bytes]:
    source = BytesIO(chunk.data)
    if chunk.compression == "lz4":
        frame_size = lz4.frame.get_frame_info(chunk.data)["content_size"]
        if frame_size and frame_size != chunk.uncompressed_size:
            raise WriterError(
                "MCAP LZ4 frame size contradicts its chunk", error_id="writer.invalid_mcap"
            )
        return cast(IO[bytes], lz4.frame.open(source, mode="rb"))
    if chunk.compression == "zstd":
        frame_size = get_frame_parameters(chunk.data).content_size
        if frame_size not in {CONTENTSIZE_UNKNOWN, chunk.uncompressed_size}:
            raise WriterError(
                "MCAP Zstandard frame size contradicts its chunk", error_id="writer.invalid_mcap"
            )
        # Native python-zstandard passes this value to ZSTD_DCtx_setMaxWindowSize in bytes.
        decoder = ZstdDecompressor(max_window_size=max(1024, limit))
        return cast(IO[bytes], decoder.stream_reader(source))
    if chunk.compression == "":
        return source
    raise WriterError(
        f"unsupported MCAP compression: {chunk.compression}", error_id="writer.invalid_mcap"
    )


def validate_chunk_size(chunk: Chunk, limit: int) -> None:
    if chunk.uncompressed_size > limit:
        raise WriterError(
            f"MCAP chunk declares {chunk.uncompressed_size} uncompressed bytes; "
            f"the limit is {limit}",
            error_id="writer.invalid_mcap",
        )
    size = 0
    with closing(_reader(chunk, limit)) as stream:
        while block := stream.read(min(64 * 1024, chunk.uncompressed_size - size + 1)):
            size += len(block)
            if size > chunk.uncompressed_size:
                break
    if size != chunk.uncompressed_size:
        raise WriterError(
            "MCAP chunk decoded size contradicts its declared uncompressed bytes",
            error_id="writer.invalid_mcap",
        )
