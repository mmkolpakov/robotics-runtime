"""Produce synthetic document inputs with the published contracts writer APIs.

Run from an extracted consumer-inputs.zip; no repository imports are required.
The templates and metric points illustrate document handling, not a real run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from mcap.writer import CompressionType, Writer

from robotics_runtime_contracts import load_mapping
from robotics_runtime_contracts.recordings import recording_summary_from_mcap
from robotics_runtime_contracts.writers import (
    add_evidence_artifact,
    create_evidence_index,
    create_runtime_manifest,
    finalize_evidence_index,
    write_document,
    write_evidence_draft,
)

RUN_ID = "run-01234567-89ab-4def-8123-456789abcdef"
START_NS = 1785067200000000000
END_NS = START_NS + 1_000_000_000


def histogram(name: str, count: int, value: float) -> dict:
    bounds = [0.5, 2.0, 5.0]
    counts = [0, 0, 0, 0]
    bucket = next((i for i, bound in enumerate(bounds) if value <= bound), 3)
    counts[bucket] = count
    return {
        "name": name,
        "unit": "ms",
        "histogram": {
            "aggregationTemporality": 1,
            "dataPoints": [
                {
                    "startTimeUnixNano": str(START_NS),
                    "timeUnixNano": str(END_NS),
                    "count": str(count),
                    "sum": count * value,
                    "min": value,
                    "max": value,
                    "bucketCounts": [str(item) for item in counts],
                    "explicitBounds": bounds,
                }
            ],
        },
    }


def counter(name: str, value: int) -> dict:
    return {
        "name": name,
        "unit": "{message}",
        "sum": {
            "aggregationTemporality": 1,
            "isMonotonic": True,
            "dataPoints": [
                {
                    "startTimeUnixNano": str(START_NS),
                    "timeUnixNano": str(END_NS),
                    "asInt": str(value),
                    "attributes": [
                        {
                            "key": "sequence.measurement.method",
                            "value": {"stringValue": "rmw_publication_sequence_single_publisher"},
                        }
                    ],
                }
            ],
        },
    }


def produce(output: Path) -> None:
    source = Path(__file__).resolve().parent
    output.mkdir(parents=True, exist_ok=False)
    scenario = write_document(
        load_mapping(source / "scenario-input.json"), output / "scenario.json"
    )
    write_document(
        create_runtime_manifest(load_mapping(source / "runtime-template.json")),
        output / "runtime-manifest.json",
    )
    write_document(
        {
            "schema_version": "acceptance-run.v1",
            "run_id": RUN_ID,
            "created_at": "2026-07-26T12:00:00Z",
            "scenario_id": "org.example.published-cli",
            "scenario_sha256": hashlib.sha256(scenario.read_bytes()).hexdigest(),
            "time_authority": {"kind": "sim_clock", "source_id": "simulation-clock"},
            "domains": [{"domain_id": "primary", "role": "observer"}],
        },
        output / "acceptance-run.json",
    )
    attributes = {
        "run.id": RUN_ID,
        "domain.id": "primary",
        "time.source.id": "simulation-clock",
        "time.measurement.method": "rmw_source_to_reception_latency",
        "channel": "/robotics/runtime_probe",
        "topic": "/example/counter",
    }
    metrics = {
        "resourceMetrics": [
            {
                "resource": {
                    "attributes": [
                        {"key": key, "value": {"stringValue": value}}
                        for key, value in attributes.items()
                    ]
                },
                "scopeMetrics": [
                    {
                        "metrics": [
                            histogram("robotics.time_authority.delivery_latency", 30, 0.1),
                            histogram("robotics.message.age", 1, 1.0),
                            counter("robotics.message.received", 100),
                            counter("robotics.message.lost", 0),
                            counter("robotics.message.sequence_error", 0),
                        ]
                    }
                ],
            }
        ],
    }
    metrics_path = output / "metrics.otlp.jsonl"
    # This fixture producer owns the OTLP bytes; the evidence writer binds them.
    metrics_path.write_text(json.dumps(metrics, separators=(",", ":")) + "\n", encoding="utf-8")
    recording = output / "recording.mcap"
    with recording.open("wb") as stream:
        writer = Writer(stream, compression=CompressionType.ZSTD)
        writer.start(profile="ros2")
        schema_id = writer.register_schema("std_msgs/msg/UInt64", "ros2msg", b"uint64 data\n")
        channel_id = writer.register_channel("/example/counter", "cdr", schema_id)
        writer.add_message(
            channel_id,
            START_NS,
            struct.pack("<IQ", 0x100, 42),
            publish_time=START_NS,
            sequence=0,
        )
        writer.finish()
    summary = write_document(
        recording_summary_from_mcap(recording), output / "recording-summary.json"
    )
    draft = create_evidence_index(
        {
            "run_id": RUN_ID,
            "generated_at": "2026-07-26T12:00:01Z",
            "policy_observation": {
                "recording_mode": "bounded",
                "compression": "zstd",
                "upload_mode": "local_only",
                "retention_class": "pull-request-7d",
                "remote_sink_used": False,
                "spool_peak_size_bytes": metrics_path.stat().st_size + recording.stat().st_size,
                "upload_lag_max_sec": 0,
            },
        }
    )
    draft = add_evidence_artifact(
        draft,
        metrics_path,
        {
            "artifact_id": "synthetic-metrics",
            "kind": "otel_metrics",
            "media_type": "application/x-ndjson",
            "retention_class": "pull-request-7d",
            "storage_state": "local",
        },
    )
    draft = add_evidence_artifact(
        draft,
        recording,
        {
            "artifact_id": "synthetic-recording",
            "kind": "recording",
            "media_type": "application/mcap",
            "retention_class": "pull-request-7d",
            "storage_state": "local",
            "segment_index": 0,
        },
        recording_summary=summary,
    )
    write_evidence_draft(draft, output / "evidence-draft.json")
    write_document(finalize_evidence_index(draft), output / "evidence-index.json")
    print(f"Inputs written to {output}; RUN_ID={RUN_ID}")
    print(f"Window: {START_NS}..{END_NS} (synthetic Unix nanoseconds)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("inputs"))
    produce(parser.parse_args().output)
