"""MCAP-library implementation kept behind the optional dependency boundary."""

from __future__ import annotations

import hashlib
import shutil
from collections import Counter
from pathlib import Path
from tempfile import TemporaryFile
from typing import IO, Any

from mcap.reader import make_reader
from mcap.records import Chunk, Statistics
from mcap.stream_reader import StreamReader
from mcap.summary import Summary

from robotics_runtime_contracts._mcap_crc import verify_extra_crcs
from robotics_runtime_contracts._mcap_observations import Observations
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


def _observed_statistics(stream: IO[bytes]) -> Observations:
    observed = Observations()
    stream.seek(0)
    for record in StreamReader(stream, validate_crcs=True).records:
        observed.observe(record)
    return observed


def _compressions(stream: IO[bytes]) -> tuple[list[str], int]:
    stream.seek(0)
    compressions: set[str] = set()
    chunks = 0
    for record in StreamReader(stream, emit_chunks=True, validate_crcs=True).records:
        if isinstance(record, Chunk):
            chunks += 1
            compressions.add(record.compression or "none")
    return sorted(compressions or {"none"}), chunks


def _channels(observed: Observations) -> list[dict[str, Any]]:
    channels = []
    for channel in sorted(observed.channels.values(), key=lambda item: (item.topic, item.id)):
        schema = observed.schemas[channel.schema_id]
        channels.append(
            {
                "topic": channel.topic,
                "message_encoding": channel.message_encoding,
                "schema_name": schema.name,
                "message_count": observed.messages[channel.id],
            }
        )
    return channels


def _check_channel_counts(statistics: Statistics, observed: Observations) -> None:
    counts = statistics.channel_message_counts
    if counts and (
        +Counter(counts) != observed.messages or not counts.keys() <= observed.channels.keys()
    ):
        raise WriterError(
            "MCAP per-channel Statistics contradict its messages", error_id="writer.invalid_mcap"
        )


def _summarize_stream(stream: IO[bytes], digest: str) -> dict[str, Any]:
    verify_extra_crcs(stream)
    summary = make_reader(stream, validate_crcs=True).get_summary()
    if summary is None:
        raise WriterError("MCAP requires a finalized summary", error_id="writer.invalid_mcap")
    expected = _statistics(summary)
    observed = _observed_statistics(stream)
    statistics = observed.statistics()
    compressions, statistics["chunk_count"] = _compressions(stream)
    if expected != statistics:
        raise WriterError("MCAP Statistics contradict its records", error_id="writer.invalid_mcap")
    assert summary.statistics is not None
    _check_channel_counts(summary.statistics, observed)
    return {
        "schema_version": "recording-summary.v1",
        "source_sha256": digest,
        "statistics": statistics,
        "compressions": compressions,
        "channels": _channels(observed),
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
