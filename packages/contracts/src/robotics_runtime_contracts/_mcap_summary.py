"""MCAP-library implementation kept behind the optional dependency boundary."""

from __future__ import annotations

import hashlib
import shutil
from collections import Counter
from pathlib import Path
from tempfile import TemporaryFile
from typing import IO, Any

from mcap.reader import make_reader
from mcap.records import Attachment, Channel, Chunk, Message, Metadata, Schema
from mcap.stream_reader import StreamReader
from mcap.summary import Summary

from robotics_runtime_contracts.writers import WriterError


def _statistics(summary: Summary) -> dict[str, int]:
    stats = summary.statistics
    if stats is None:
        raise WriterError(
            "MCAP requires finalized summary Statistics", error_id="writer.invalid_mcap"
        )
    return {
        "message_count": stats.message_count,
        "schema_count": stats.schema_count,
        "channel_count": stats.channel_count,
        "attachment_count": stats.attachment_count,
        "metadata_count": stats.metadata_count,
        "chunk_count": stats.chunk_count,
        "message_start_time_ns": stats.message_start_time,
        "message_end_time_ns": stats.message_end_time,
    }


def _observed_statistics(stream: IO[bytes]) -> tuple[dict[str, int], Counter[int]]:
    counts: Counter[str] = Counter()
    messages: Counter[int] = Counter()
    schema_ids: set[int] = set()
    channel_ids: set[int] = set()
    start: int | None = None
    end = 0
    stream.seek(0)
    for record in StreamReader(stream, validate_crcs=True).records:
        if isinstance(record, Message):
            messages[record.channel_id] += 1
            start = record.log_time if start is None else min(start, record.log_time)
            end = max(end, record.log_time)
        elif isinstance(record, Schema):
            schema_ids.add(record.id)
        elif isinstance(record, Channel):
            channel_ids.add(record.id)
        elif isinstance(record, Attachment):
            counts["attachment_count"] += 1
        elif isinstance(record, Metadata):
            counts["metadata_count"] += 1
    return {
        "message_count": sum(messages.values()),
        "schema_count": len(schema_ids),
        "channel_count": len(channel_ids),
        "attachment_count": counts["attachment_count"],
        "metadata_count": counts["metadata_count"],
        "message_start_time_ns": 0 if start is None else start,
        "message_end_time_ns": end,
    }, messages


def _compressions(stream: IO[bytes]) -> tuple[list[str], int]:
    stream.seek(0)
    compressions: set[str] = set()
    chunks = 0
    for record in StreamReader(stream, emit_chunks=True, validate_crcs=True).records:
        if isinstance(record, Chunk):
            chunks += 1
            compressions.add(record.compression or "none")
    return sorted(compressions or {"none"}), chunks


def _channels(summary: Summary, counts: Counter[int]) -> list[dict[str, Any]]:
    channels = []
    for channel in sorted(summary.channels.values(), key=lambda item: (item.topic, item.id)):
        schema = summary.schemas.get(channel.schema_id)
        if schema is None:
            raise WriterError("recording-summary.v1 requires a named schema for every channel")
        channels.append(
            {
                "topic": channel.topic,
                "message_encoding": channel.message_encoding,
                "schema_name": schema.name,
                "message_count": counts[channel.id],
            }
        )
    return channels


def _summarize_stream(stream: IO[bytes], digest: str) -> dict[str, Any]:
    summary = make_reader(stream, validate_crcs=True).get_summary()
    if summary is None:
        raise WriterError("MCAP requires a finalized summary", error_id="writer.invalid_mcap")
    expected = _statistics(summary)
    observed, counts = _observed_statistics(stream)
    compressions, observed["chunk_count"] = _compressions(stream)
    if expected != observed:
        raise WriterError("MCAP Statistics contradict its records", error_id="writer.invalid_mcap")
    assert summary.statistics is not None
    if +Counter(summary.statistics.channel_message_counts) != counts:
        raise WriterError("MCAP per-channel Statistics contradict its messages")
    return {
        "schema_version": "recording-summary.v1",
        "source_sha256": digest,
        "statistics": observed,
        "compressions": compressions,
        "channels": _channels(summary, counts),
    }


def summarize(source: Path) -> dict[str, Any]:
    # Parse/hash the same private byte snapshot; source replacement cannot mix passes.
    with source.open("rb") as original, TemporaryFile() as snapshot:
        shutil.copyfileobj(original, snapshot)
        snapshot.seek(0)
        digest = hashlib.file_digest(snapshot, "sha256").hexdigest()
        snapshot.seek(0)
        try:
            return _summarize_stream(snapshot, digest)
        except WriterError:
            raise
        except Exception as error:
            raise WriterError(f"invalid MCAP: {error}", error_id="writer.invalid_mcap") from error
