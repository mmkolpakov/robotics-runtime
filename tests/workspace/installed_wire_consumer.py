"""Exercise a foreign file evaluator with installed harness and contracts wheels."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from hashlib import sha256
from importlib import resources
from pathlib import Path
from typing import Any

import robotics_acceptance_harness as harness
import robotics_runtime_contracts as contracts
from jsonschema import Draft202012Validator, FormatChecker
from robotics_acceptance_harness.evaluation import EvaluationError
from robotics_acceptance_harness.evaluator_json import (
    decode_evaluator_response,
    encode_evaluator_request,
)
from robotics_runtime_contracts.writers import (
    add_evidence_artifact,
    create_evidence_index,
    finalize_evidence_index,
    write_document,
)

NODE_IMAGE = (
    "node:24.21.0-trixie-slim@sha256:"
    "c83040f7e24bacea68e58a0b96a484ba430bf24abb2973eab7ba4701144b7b63"
)
NAMESPACE = "org.example.evidence-bytes-node"
IDS = [f"{NAMESPACE}.nonempty", f"{NAMESPACE}.calibrated-error"]
ROOT = Path.cwd()


def stored(directory: Path, name: str, data: bytes, uri: str) -> dict[str, Any]:
    path = directory / name
    path.write_bytes(data)
    path.chmod(0o444)
    return {
        "uri": uri,
        "sha256": sha256(data).hexdigest(),
        "size_bytes": len(data),
    }


def main() -> None:
    assert sys.flags.isolated
    for module in (harness, contracts):
        assert module.__file__ is not None
        assert Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    assert shutil.which("docker"), "Docker is required for the foreign fixture"
    fixture = ROOT / "node-fixture" / "evaluate.mjs"
    assert fixture.is_file()
    schemas = resources.files("robotics_acceptance_harness").joinpath("schemas")
    validators = {}
    for role in ("request", "response"):
        schema = json.loads(schemas.joinpath(f"evaluator-{role}.v1.schema.json").read_bytes())
        Draft202012Validator.check_schema(schema)
        validators[role] = Draft202012Validator(
            schema, registry=contracts.schema_registry(), format_checker=FormatChecker()
        )

    # The public synthetic archive producer uses installed CLIs, not the source tree.
    env = dict(os.environ)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env["PATH"]
    env.pop("PYTHONPATH", None)
    archive = ROOT / "wire-archive"
    produced = subprocess.run(
        [
            sys.executable,
            "-I",
            str(ROOT / "native-producer.py"),
            "--output",
            str(archive),
            "--error",
            "7",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
        env=env,
    )
    archive_info = json.loads(produced.stdout)
    observation = json.loads((archive / "observation.json").read_bytes())
    scenario = json.loads((archive / "scenario.json").read_bytes())
    controls_validator = Draft202012Validator(
        {
            "$ref": (
                "urn:robotics-runtime-contracts:v2:internal:native-execution"
                "#/$defs/assessmentControls"
            )
        },
        registry=contracts.schema_registry(),
        format_checker=FormatChecker(),
    )
    documents = {
        "acceptance_scenario": archive / "scenario.json",
        "runtime_manifest": archive / "runtime.json",
        "acceptance_run": archive / "run.json",
        "acceptance_observation": archive / "observation.json",
    }

    cases = [
        ("selected-seven", b'{"counter":7}', b'{"offset":7}', "selected", "passed", 0),
        ("selected-six", b'{"counter":7}', b'{"offset":6}', "selected", "failed", 1),
        ("unobserved", b'{"counter":7}', b"", "unobserved", "skipped", None),
        ("bad-counter", b'{"counter":"bad"}', b'{"offset":7}', "selected", "error", None),
        ("bad-offset", b'{"counter":7}', b'{"offset":"bad"}', "selected", "error", None),
        (
            "bad-counter-utf8",
            b'{"counter":7,"note":"\xff"}',
            b'{"offset":7}',
            "selected",
            "error",
            None,
        ),
        (
            "bad-offset-utf8",
            b'{"counter":7}',
            b'{"offset":7,"note":"\xff"}',
            "selected",
            "error",
            None,
        ),
        (
            "large-integer",
            b'{"counter":9007199254740993}',
            b'{"offset":0}',
            "selected",
            "failed",
            9007199254740993,
        ),
        (
            "uint64",
            b'{"counter":18446744073709551615}',
            b'{"offset":0}',
            "selected",
            "failed",
            18446744073709551615,
        ),
    ]
    outputs = {}
    for name, counter, offset, state, expected_status, expected_value in cases:
        directory = ROOT / ("wire-" + name)
        input_root = directory / "input"
        input_root.mkdir(parents=True, mode=0o700)
        method_input = directory / "original-method-input.json"
        method_input.write_bytes(counter)
        source_index = json.loads((archive / "evidence-index.json").read_bytes())
        index_template = {
            key: value
            for key, value in source_index.items()
            if key not in {"artifacts", "finalized"}
        }
        index_template["policy_observation"]["spool_peak_size_bytes"] += len(counter)
        draft = create_evidence_index(index_template)
        for item in source_index["artifacts"]:
            draft = add_evidence_artifact(draft, item["local_path"], item)
        draft = add_evidence_artifact(
            draft,
            method_input,
            {
                "artifact_id": "method-input",
                "kind": "other_evidence",
                "media_type": "application/json",
                "retention_class": "pull-request-7d",
                "storage_state": "local",
            },
        )
        index = finalize_evidence_index(draft)
        index_path = write_document(index, directory / "selected-evidence-index.json")
        selected_documents = {**documents, "evidence_index": index_path}
        references = {
            role: stored(input_root, role + ".json", path.read_bytes(), path.resolve().as_uri())
            for role, path in selected_documents.items()
        }
        config_path = archive / "configuration.json"
        config = stored(
            input_root, "config.json", config_path.read_bytes(), config_path.resolve().as_uri()
        )
        source = next(item for item in index["artifacts"] if item["artifact_id"] == "method-input")
        evidence = stored(input_root, "method-input.json", method_input.read_bytes(), source["uri"])
        calibration: dict[str, Any]
        if state == "selected":
            offset_source = directory / "original-offset.json"
            offset_source.write_bytes(offset)
            calibration = {
                "state": "selected",
                "artifacts": [
                    stored(input_root, "offset.json", offset, offset_source.resolve().as_uri())
                ],
            }
        else:
            calibration = {"state": "unobserved", "reason": "not measured"}
        control_data = {
            key: scenario[key]
            for key in (
                "metric_definitions",
                "assertions",
                "evaluator_requirements",
                "evidence_policy",
            )
        }
        control_data["calibration"] = calibration
        controls_validator.validate(control_data)
        controls_source = directory / "original-controls.json"
        controls_source.write_bytes(json.dumps(control_data).encode())
        controls = stored(
            input_root,
            "controls.json",
            controls_source.read_bytes(),
            controls_source.resolve().as_uri(),
        )
        locations = {
            sha256(path.read_bytes()).hexdigest(): path.name
            for path in input_root.iterdir()
            if path.is_file()
        }
        request = {
            "schema_version": "evaluator-request.v1",
            "run_id": archive_info["run_id"],
            "domain_id": archive_info["domain_id"],
            "namespace": NAMESPACE,
            "expected_assertion_ids": IDS,
            "method": {"implementation": NAMESPACE, "version": "1", "configuration": config},
            "documents": references,
            "controls": controls,
            "evidence": [
                {
                    **evidence,
                    "artifact_id": source["artifact_id"],
                    "kind": source["kind"],
                    "media_type": source["media_type"],
                    "retention_class": source["retention_class"],
                }
            ],
            "locations": [{"sha256": digest, "path": path} for digest, path in locations.items()],
            "window": observation["measurement_window"],
        }
        request_bytes = encode_evaluator_request(request)
        validators["request"].validate(json.loads(request_bytes))
        assert str(request["window"]["start_ns"]).encode() in request_bytes
        (input_root / "request.json").write_bytes(request_bytes)
        (input_root / "request.json").chmod(0o444)
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "64",
            "--memory",
            "256m",
            "--mount",
            f"type=bind,src={input_root},dst=/run/robotics-evaluator,readonly",
            "--mount",
            f"type=bind,src={fixture},dst=/fixture/evaluate.mjs,readonly",
            "--entrypoint",
            "node",
            NODE_IMAGE,
            "/fixture/evaluate.mjs",
            "--request",
            "/run/robotics-evaluator/request.json",
        ]
        completed = subprocess.run(command, capture_output=True, check=True, timeout=30)
        response_bytes = completed.stdout
        assert len(response_bytes) <= 1024 * 1024
        validators["response"].validate(json.loads(response_bytes))
        allowed = {str(evidence["sha256"])}
        if state == "selected":
            allowed.add(str(calibration["artifacts"][0]["sha256"]))
        rows = decode_evaluator_response(
            response_bytes,
            request_sha256=sha256(request_bytes).hexdigest(),
            namespace=NAMESPACE,
            expected_assertion_ids=IDS,
            allowed_evidence_sha256=allowed,
        )
        by_id = {row.assertion_id: row for row in rows}
        assert by_id[IDS[0]].status == "passed"
        assert by_id[IDS[0]].source == "product"
        assert set(by_id[IDS[0]].evidence_sha256) == {str(evidence["sha256"])}
        assert by_id[IDS[1]].source == "product"
        assert set(by_id[IDS[1]].evidence_sha256) == allowed
        assert by_id[IDS[1]].status == expected_status
        assert by_id[IDS[1]].observed_value == expected_value
        for foreign in (str(config["sha256"]), str(controls["sha256"])):
            assert foreign not in allowed
            altered = json.loads(response_bytes)
            altered["assertion_results"][1]["evidence_sha256"] = [foreign]
            try:
                decode_evaluator_response(
                    json.dumps(altered).encode(),
                    request_sha256=sha256(request_bytes).hexdigest(),
                    namespace=NAMESPACE,
                    expected_assertion_ids=IDS,
                    allowed_evidence_sha256=allowed,
                )
            except EvaluationError:
                pass
            else:
                raise AssertionError("unselected configuration or controls digest was accepted")
        outputs[name] = {"status": expected_status, "observed_value": expected_value}
    (ROOT / "wire-consumer-report.json").write_text(json.dumps(outputs, indent=2) + "\n")
    print(json.dumps(outputs, sort_keys=True))


if __name__ == "__main__":
    main()
