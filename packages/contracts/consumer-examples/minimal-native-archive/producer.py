"""Produce a small native archive through the installed public CLIs."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import time_ns
from typing import Any


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def reference(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "uri": path.resolve().as_uri(),
        "sha256": sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "media_type": "application/x-ndjson" if path.suffix == ".jsonl" else "application/json",
    }


def command(executable: str, *arguments: str) -> str:
    return subprocess.check_output([executable, *arguments], text=True).strip()


def profile(configuration: Path, descriptor: Path) -> dict[str, Any]:
    return {
        "profile_id": "org.example.native-counter",
        "channels": [
            {
                "name": "counter-state",
                "original_type": {
                    "name": "org.example.CounterState",
                    "codec": {
                        "implementation": "python-json",
                        "version": platform.python_version(),
                    },
                    "descriptor": reference(descriptor),
                },
                "backend": "local-file",
                "wire_envelope": "json-object",
                "native_encoding": "utf-8",
                "recorder": {
                    "implementation": "org.example.native-archive-producer",
                    "version": "1",
                    "transformation": "none",
                },
            }
        ],
        "executor": {
            "implementation": "org.example.native-archive-producer",
            "version": "1",
            "configuration": reference(configuration),
        },
        "clock": {"kind": "external", "source_id": "system-utc"},
        "observations": {
            "command": {"kind": "command_acceptance", "requirement": "required"},
            "terminal": {"kind": "native_final_state", "requirement": "required"},
            "condition": {"kind": "postcondition", "requirement": "required"},
            "loaded-model": {"kind": "other", "requirement": "required"},
            "delivery-clock": {
                "kind": "clock",
                "requirement": "not_applicable",
                "reason": "this local-file profile does not measure delivery-clock latency",
            },
        },
    }


def execution(simulation: bool) -> dict[str, str]:
    if simulation:
        return {
            "target_environment": "simulation",
            "data_source": "native-discrete-counter",
            "plant_backend": "org.example.discrete-counter",
            "time_mode": "discrete_steps",
        }
    return {"target_environment": "software", "data_source": "native-counter"}


def scenario(native_profile: dict[str, Any], model: Path, simulation: bool) -> dict[str, Any]:
    assertions = []
    definitions = []
    for name, expected in (("accepted", 1), ("finished", 1), ("error", 0)):
        metric_name = f"org.example.counter.{name}"
        definitions.append(
            {
                "metric_name": metric_name,
                "unit": "1",
                "instrument_kind": "gauge",
                "temporality": "instantaneous",
            }
        )
        assertions.append(
            {
                "assertion_id": f"counter-{name}",
                "kind": "metric",
                "metric_name": metric_name,
                "unit": "1",
                "aggregation": "max",
                "operator": "eq",
                "threshold": expected,
                "window_sec": 60,
                "attribute_match": {"native.profile.id": "org.example.native-counter"},
            }
        )
    return {
        "schema_version": "acceptance-scenario.v2",
        "scenario_id": "org.example.native-counter",
        "execution": execution(simulation),
        "profile": native_profile,
        "native_model": reference(model),
        "metric_definitions": definitions,
        "assertions": assertions,
        "evaluator_requirements": [],
        "evidence_policy": {
            "max_artifact_size_bytes": 1048576,
            "max_archive_size_bytes": 4194304,
            "max_upload_lag_sec": 0,
            "upload_mode": "local_only",
            "retention_class": "pull-request-7d",
            "remote_sink_allowed": False,
        },
    }


def metric(
    name: str, value: int, observed_at_ns: int, run_id: str, domain_id: str
) -> dict[str, Any]:
    return {
        "name": f"org.example.counter.{name}",
        "unit": "1",
        "gauge": {
            "dataPoints": [
                {
                    "timeUnixNano": str(observed_at_ns),
                    "asInt": str(value),
                    "attributes": [
                        {"key": "run.id", "value": {"stringValue": run_id}},
                        {"key": "domain.id", "value": {"stringValue": domain_id}},
                        {
                            "key": "native.profile.id",
                            "value": {"stringValue": "org.example.native-counter"},
                        },
                    ],
                }
            ]
        },
    }


def index_inputs(destination: Path, run_id: str, paths: list[Path]) -> Path:
    template = write_json(
        destination / "index-template.json",
        {
            "schema_version": "evidence-index.v1",
            "run_id": run_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "policy_observation": {
                "recording_mode": "native-files",
                "compression": "none",
                "retention_class": "pull-request-7d",
                "upload_mode": "local_only",
                "remote_sink_used": False,
                "spool_peak_size_bytes": sum(path.stat().st_size for path in paths),
                "upload_lag_max_sec": 0,
            },
        },
    )
    draft = destination / "index-draft.json"
    metadata = destination / "artifact-metadata.json"
    command(
        "robotics-contracts",
        "evidence-index",
        "init",
        "--template",
        str(template),
        "--output",
        str(draft),
    )
    for path in paths:
        kind = "acceptance_observation" if path.name == "observation.json" else "other_evidence"
        media_type = "application/json"
        if path.name == "metrics.jsonl":
            kind, media_type = "metrics", "application/x-ndjson"
        write_json(
            metadata,
            {
                "artifact_id": path.stem.replace(".", "-"),
                "kind": kind,
                "media_type": media_type,
                "retention_class": "pull-request-7d",
                "storage_state": "local",
            },
        )
        command(
            "robotics-contracts",
            "evidence-index",
            "add-artifact",
            str(draft),
            "--source",
            str(path),
            "--metadata",
            str(metadata),
        )
    index = destination / "evidence-index.json"
    command("robotics-contracts", "evidence-index", "finalize", str(draft), "--output", str(index))
    for path in (template, draft, metadata):
        path.unlink()
    return index


def unix_ns(timestamp: datetime) -> int:
    elapsed = timestamp - datetime(1970, 1, 1, tzinfo=UTC)
    return (
        elapsed.days * 86_400_000_000_000
        + elapsed.seconds * 1_000_000_000
        + elapsed.microseconds * 1_000
    )


def counter_transition(
    configuration: Path, model: Path, error: int, simulation: bool
) -> tuple[dict[str, Any], dict[str, Any]]:
    loaded_configuration = json.loads(configuration.read_bytes())
    model_bytes = model.read_bytes()
    loaded_model = json.loads(model_bytes)
    loaded_model_reference = {
        "uri": model.resolve().as_uri(),
        "sha256": sha256(model_bytes).hexdigest(),
        "size_bytes": len(model_bytes),
        "media_type": "application/json",
    }
    actual = int(loaded_configuration["desired"]) + int(loaded_model["offset"])
    if simulation:
        actual = 0
        for _step in range(int(loaded_model["steps"])):
            actual += int(loaded_configuration["desired"]) + int(loaded_model["offset"])
    actual += error
    native_state = {"command_accepted": True, "native_final_state": "completed", "counter": actual}
    return native_state, loaded_model_reference


def produce(arguments: argparse.Namespace) -> dict[str, Any]:
    destination = Path(arguments.output).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    configuration = write_json(destination / "configuration.json", {"desired": 0})
    descriptor = write_json(
        destination / "native-type.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["command_accepted", "native_final_state", "counter"],
            "properties": {
                "command_accepted": {"type": "boolean"},
                "native_final_state": {"type": "string"},
                "counter": {"type": "integer"},
                "loaded_model_sha256": {"type": "string"},
            },
            "additionalProperties": False,
        },
    )
    model = write_json(destination / "model.json", {"offset": 0, "steps": 3})
    native_profile = profile(configuration, descriptor)
    if arguments.all_not_applicable:
        for requirement in native_profile["observations"].values():
            requirement["requirement"] = "not_applicable"
            requirement["reason"] = "the selected assessment scope excludes this native fact"
    scenario_document = scenario(native_profile, model, arguments.simulation)
    if arguments.no_criteria:
        scenario_document["assertions"] = []
    if arguments.raw_only:
        scenario_document["assertions"] = []
        scenario_document["metric_definitions"] = []
    bindings = []
    if arguments.evaluator_binding:
        bindings = [json.loads(Path(arguments.evaluator_binding).read_bytes())]
    scenario_document["evaluator_requirements"] = bindings
    scenario_path = write_json(destination / "scenario.json", scenario_document)
    command("robotics-contracts", "validate", str(scenario_path))
    run_path = destination / "run.json"
    run_id = command(
        "robotics-acceptance",
        "create-run",
        "--scenario",
        str(scenario_path),
        "--output",
        str(run_path),
        "--domain",
        f"{arguments.domain}=primary",
        "--time-authority",
        "external",
        "--time-source",
        "system-utc",
    )
    runtime_template = write_json(
        destination / "runtime-template.json",
        {
            "schema_version": "runtime-manifest.v2",
            "runtime_id": "native-counter-runtime",
            "generated_at": datetime.now(UTC).isoformat(),
            "scenario_sha256": reference(scenario_path)["sha256"],
            "execution": execution(arguments.simulation),
            "profile": native_profile,
            "native_model": reference(model),
            "evaluator_bindings": bindings,
        },
    )
    runtime_path = destination / "runtime.json"
    command(
        "robotics-contracts",
        "runtime-manifest",
        "init",
        "--template",
        str(runtime_template),
        "--output",
        str(runtime_path),
    )
    runtime_template.unlink()
    started_at = datetime.now(UTC)
    window_start_ns = unix_ns(started_at)
    native_state, loaded_model_reference = counter_transition(
        configuration, model, arguments.error, arguments.simulation
    )
    actual = int(native_state["counter"])
    raw_native = write_json(destination / "native-state.json", native_state)
    observed_at_ns = time_ns()
    metrics = destination / "metrics.jsonl"
    payload = {
        "resourceMetrics": [
            {
                "scopeMetrics": [
                    {
                        "scope": {"name": "org.example.native-archive-producer", "version": "1"},
                        "metrics": [
                            metric(name, value, observed_at_ns, run_id, arguments.domain)
                            for name, value in (
                                ("accepted", 1),
                                ("finished", 1),
                                ("error", abs(actual)),
                            )
                        ],
                    }
                ]
            }
        ]
    }
    metrics.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    finished_at = datetime.now(UTC)
    window_end_ns = unix_ns(finished_at)
    observations = {
        "command": {
            "state": "measured",
            "value": native_state["command_accepted"],
            "evidence": reference(raw_native),
        },
        "terminal": {
            "state": "measured",
            "value": native_state["native_final_state"],
            "evidence": reference(raw_native),
        },
        "condition": {
            "state": "measured",
            "value": native_state["counter"],
            "evidence": reference(raw_native),
        },
        "loaded-model": {
            "state": "measured",
            "value": loaded_model_reference["sha256"],
            "evidence": reference(raw_native),
        },
        "delivery-clock": {
            "state": "not_applicable",
            "reason": "this local-file profile does not measure delivery-clock latency",
        },
    }
    if arguments.all_not_applicable:
        observations = {
            name: {"state": "not_applicable", "reason": requirement["reason"]}
            for name, requirement in native_profile["observations"].items()
        }
    if arguments.omit:
        del observations[arguments.omit]
    if arguments.invalid:
        observations[arguments.invalid] = {
            "state": "invalid",
            "reason": "producer could not validate this native observation",
            "evidence": reference(raw_native),
        }
    observation_path = write_json(
        destination / "observation.json",
        {
            "schema_version": "acceptance-observation.v2",
            "observation_id": "native-counter-observation",
            "run_id": run_id,
            "scenario_id": "org.example.native-counter",
            "domain_id": arguments.domain,
            "scenario_sha256": reference(scenario_path)["sha256"],
            "runtime_manifest_sha256": reference(runtime_path)["sha256"],
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "observations": observations,
            "measurement_window": {
                "start_ns": window_start_ns,
                "end_ns": window_end_ns,
                "clock": {"kind": "external", "source_id": "system-utc"},
                "timestamp_encoding": "unix_ns",
            },
            "native_model": loaded_model_reference,
            "evidence": [reference(raw_native), reference(metrics)],
        },
    )
    command("robotics-contracts", "validate", str(observation_path))
    index = index_inputs(
        destination,
        run_id,
        [configuration, descriptor, model, raw_native, metrics, observation_path],
    )
    result = {
        "run_id": run_id,
        "domain_id": arguments.domain,
        "window_start_ns": window_start_ns,
        "window_end_ns": window_end_ns,
        "scenario": str(scenario_path),
        "runtime": str(runtime_path),
        "run_context": str(run_path),
        "evidence_index": str(index),
        "otel_metrics": str(metrics),
    }

    if arguments.raw_only:
        result.pop("otel_metrics")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--domain", default="primary")
    parser.add_argument("--evaluator-binding", metavar="PATH")
    parser.add_argument("--error", type=int, default=0)
    parser.add_argument("--simulation", action="store_true")
    parser.add_argument("--no-criteria", action="store_true")
    parser.add_argument("--raw-only", action="store_true")
    parser.add_argument("--all-not-applicable", action="store_true")
    parser.add_argument("--omit", choices=["command", "terminal", "condition"])
    parser.add_argument("--invalid", choices=["command", "terminal", "condition"])
    print(json.dumps(produce(parser.parse_args()), sort_keys=True))


if __name__ == "__main__":
    main()
