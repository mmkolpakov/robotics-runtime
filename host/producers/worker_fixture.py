"""Finite test producer using installed public writer and run APIs."""
from __future__ import annotations
import argparse
from pathlib import Path
from robotics_runtime_contracts import load_mapping
from robotics_runtime_contracts.writers import (
    add_evidence_artifact, create_evidence_index, finalize_evidence_index,
    write_bytes_atomically, write_document,
)
from robotics_acceptance_harness.run_context import create_run_context

parser = argparse.ArgumentParser()
parser.add_argument("--source-root", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
run_id = "run-01234567-89ab-4def-8123-456789abcdef"
scenario = args.source_root / "packages/harness/tests/fixtures/simulation/scenario.yaml"
create_run_context(
    scenario, args.output / "run.json", domains={"primary": "observer"},
    time_authority="sim_clock", time_source="fixture-clock", run_id=run_id,
)
metrics = write_bytes_atomically(b'{"resourceMetrics":[]}\n', args.output / "metrics.ndjson")
sample = load_mapping(args.source_root / "packages/contracts/consumer-examples/minimal-simulation/evidence-index.yaml")
template = {key: value for key, value in sample.items() if key not in {"artifacts", "finalized"}}
draft = create_evidence_index(template)
draft = add_evidence_artifact(draft, metrics, {
    "artifact_id": "metrics", "kind": "observation", "media_type": "application/x-ndjson",
    "retention_class": "pull-request-7d", "segment_index": 0, "storage_state": "local",
})
write_document(finalize_evidence_index(draft), args.output / "evidence.json")
