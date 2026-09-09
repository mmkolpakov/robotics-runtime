from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

import pytest
from robotics_runtime_contracts import load_mapping, validate_document

from robotics_acceptance_harness.aggregate import (
    aggregate_results,
    evaluate_transport_qualification,
)
from robotics_acceptance_harness.application import evaluate_from_evidence
from robotics_acceptance_harness.campaign import aggregate_campaign
from robotics_acceptance_harness.cli import main
from robotics_acceptance_harness.documents import DocumentSource
from robotics_acceptance_harness.evidence import EvidenceValidationError, load_evidence_index
from tests.support import local_recording_artifact, write_evidence_index
from tests.test_aggregate import (
    FIXTURES,
    RUN_ID,
    causal_chain,
    channel_contract,
    clock_relation,
    result,
    run_context,
    trace_evidence_index,
    trace_file,
    transport_scenario,
)
from tests.test_application import (
    SIMULATION_DOMAIN,
    SIMULATION_RUN_ID,
    _simulation_bundle,
    _write_evidence,
    _write_metrics,
    _write_run_context,
)

NAMESPACE = "org.example.metadata"
URI = "https://example.org/schemas/metadata.v1.schema.json"
SCHEMA = json.dumps(
    {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": URI,
        "type": "object",
        "properties": {"frame": {"type": "string"}},
        "required": ["frame"],
        "additionalProperties": False,
    }
).encode()
REGISTRY = {URI: SCHEMA}


def _extend(path: Path) -> Path:
    document = load_mapping(path)
    document["extensions"] = {NAMESPACE: {"frame": "map"}}
    document["extension_schemas"] = [
        {"namespace": NAMESPACE, "schema_uri": URI, "sha256": sha256(SCHEMA).hexdigest()}
    ]
    validate_document(document, extension_schemas=REGISTRY)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


@pytest.mark.parametrize("role", ["evidence_index", "recording_summary"])
def test_evidence_consumers_validate_extensions_with_the_supplied_registry(
    tmp_path: Path, role: str
) -> None:
    artifact = local_recording_artifact(tmp_path / "recording.mcap", topics={"/clock": "Clock"})
    if role == "recording_summary":
        reference = artifact["recording_summary"]
        summary = _extend(Path(url2pathname(urlsplit(reference["uri"]).path)))
        reference.update(
            sha256=sha256(summary.read_bytes()).hexdigest(), size_bytes=summary.stat().st_size
        )
    index = write_evidence_index(tmp_path / "index.json", run_id=RUN_ID, artifacts=[artifact])
    if role == "evidence_index":
        _extend(index)

    evidence = load_evidence_index(DocumentSource(index, REGISTRY))
    document = evidence.index if role == "evidence_index" else evidence.recording_summaries[0]
    assert document.data["extensions"][NAMESPACE]["frame"] == "map"
    with pytest.raises(
        EvidenceValidationError, match="declared extensions require supplied schema documents"
    ):
        load_evidence_index(index)
    with pytest.raises(EvidenceValidationError, match="sha256"):
        load_evidence_index(DocumentSource(index, {URI: SCHEMA + b" "}))


def test_offline_evaluation_carries_the_bundle_registry_into_run_and_evidence(
    tmp_path: Path,
) -> None:
    registry = dict(REGISTRY)
    bundle = replace(_simulation_bundle(tmp_path), extension_schemas=registry)
    registry.clear()
    assert bundle.extension_schemas == REGISTRY
    metrics = tmp_path / "metrics.jsonl"
    _write_metrics(
        metrics,
        run_id=SIMULATION_RUN_ID,
        domain_id=SIMULATION_DOMAIN,
        source_id="simulation-clock",
        start_ns=1_000_000_000,
        end_ns=2_000_000_000,
    )
    evidence = _extend(
        _write_evidence(tmp_path / "evidence.json", metrics, run_id=SIMULATION_RUN_ID)
    )
    context = _extend(
        _write_run_context(
            tmp_path / "run.yaml",
            bundle,
            run_id=SIMULATION_RUN_ID,
            domain_id=SIMULATION_DOMAIN,
            time_kind="sim_clock",
            source_id="simulation-clock",
        )
    )
    outputs = evaluate_from_evidence(
        run_id=SIMULATION_RUN_ID,
        domain_id=SIMULATION_DOMAIN,
        run_context_path=context,
        bundle=bundle,
        evidence_index_path=evidence,
        otel_metrics_path=metrics,
        window_start_ns=1_000_000_000,
        window_end_ns=2_000_000_000,
        output_dir=tmp_path / "output",
    )
    assert outputs.result["evaluation_mode"] == "offline"
    assert outputs.result["status"] == "incomplete"
    assert "$.observed_ros_graph" in outputs.result["unevaluated"]


def test_aggregate_and_campaign_accept_extended_run_and_result_documents(tmp_path: Path) -> None:
    context = _extend(run_context(tmp_path))
    results = [
        _extend(result(tmp_path, domain, str(index)))
        for index, domain in enumerate(("camera-domain", "control-domain"))
    ]
    aggregate = aggregate_results(
        scenario_path=FIXTURES / "scenario.yaml",
        run_context_path=context,
        result_paths=results,
        output_path=tmp_path / "aggregate.json",
        extension_schemas=REGISTRY,
    )
    _extend(aggregate)
    campaign = aggregate_campaign(
        scenario_path=FIXTURES / "scenario.yaml",
        run_context_paths=[context],
        aggregate_paths=[aggregate],
        output_path=tmp_path / "campaign.json",
        minimum_passed_runs=1,
        extension_schemas=REGISTRY,
    )
    assert load_mapping(campaign)["verdict"]["status"] == "passed"


def test_doctor_and_why_accept_the_same_local_extension_schema_option(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_bytes(SCHEMA)
    option = f"{URI}={schema_path}"
    scenario = tmp_path / "scenario.json"
    scenario.write_text(json.dumps(load_mapping(FIXTURES / "scenario.yaml")), encoding="utf-8")
    _extend(scenario)
    assert main(["doctor", "--scenario", str(scenario), "--extension-schema", option]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "passed"
    result_path = _extend(result(tmp_path, "camera-domain", "0"))
    assert main(["why", str(result_path), "--extension-schema", option]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "passed"
    schema_path.write_bytes(SCHEMA + b" ")
    assert main(["why", str(result_path), "--extension-schema", option]) == 2
    assert "sha256" in capsys.readouterr().err


def test_transport_consumes_extended_channels_chains_relations_and_indexes(tmp_path: Path) -> None:
    scenario = transport_scenario(tmp_path)
    producer = trace_file(
        tmp_path, "camera-domain", "observation publish", 2, message_id="message-1"
    )
    consumer = trace_file(
        tmp_path,
        "control-domain",
        "observation receive",
        3,
        message_id="message-1",
        link_byte=2,
    )
    channel = _extend(channel_contract(tmp_path, "link"))
    chain = _extend(causal_chain(tmp_path, channel))
    relation = _extend(clock_relation(tmp_path, scenario, producer))
    output = evaluate_transport_qualification(
        run_id=RUN_ID,
        scenario_path=scenario,
        causal_chain_paths=[chain],
        channel_contract_paths=[channel],
        trace_paths={"camera-domain": producer, "control-domain": consumer},
        evidence_index_paths={
            "camera-domain": _extend(trace_evidence_index(tmp_path, "camera-domain", producer)),
            "control-domain": _extend(trace_evidence_index(tmp_path, "control-domain", consumer)),
        },
        clock_relation_paths=[relation],
        observation_output_dir=tmp_path / "observations",
        output_path=tmp_path / "qualification.json",
        extension_schemas=REGISTRY,
    )
    document = load_mapping(output)
    assert document["verdict"]["status"] == "passed"
    assert document["clock_relations"][0]["status"] == "passed"
