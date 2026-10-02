"""Copied beside release smoke and run only with the isolated installed interpreter."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from hashlib import sha256
from importlib import import_module
from importlib.metadata import distribution
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from robotics_acceptance_harness.documents import BundleValidationError, load_bundle
from robotics_runtime_contracts import (
    ContractError,
    dumps_canonical,
    load_mapping,
    validate_document,
    validate_role,
)
from robotics_runtime_contracts.qualification import (
    inspect_qualification_artifacts,
    validate_qualification_artifacts,
)
from robotics_runtime_contracts.statements import (
    validate_qualification_statement,
    write_qualification_statement,
)
from robotics_runtime_contracts.writers import (
    add_evidence_artifact,
    create_evidence_index,
    finalize_evidence_index,
    write_document,
)


def artifact_specifications(fixtures: Path, name: str) -> list[str]:
    inventory = json.loads((fixtures / f"{name}-artifacts.json").read_text("utf-8"))
    return [
        f"{item['kind']}:{item['subject_name']}={fixtures / item['file']}"
        for item in inventory["artifacts"]
    ]


def cli(module: str, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-m", module, *arguments],
        text=True,
        capture_output=True,
        check=False,
    )


def verify_negative_inputs(fixtures: Path, specifications: list[str]) -> list[str]:
    # Keep the complete inventory so missing links cannot explain this refusal.
    wrong_role = specifications.copy()
    wrong_role[0] = wrong_role[0].replace("scenario:", "runtime_manifest:", 1)
    report = inspect_qualification_artifacts(wrong_role)
    assert not report.valid and len(report.diagnostics) == 1
    diagnostic = report.diagnostics[0]
    assert diagnostic.error_id == "qualification.invalid"
    assert diagnostic.check == "artifact.load"
    missing = inspect_qualification_artifacts(specifications[1:])
    assert not missing.valid and missing.diagnostics
    missing_file = inspect_qualification_artifacts(["scenario:scenario.json=absent.yaml"])
    assert not missing_file.valid and missing_file.diagnostics

    statement = write_qualification_statement(specifications, "statement.json")
    validate_qualification_statement(statement, specifications)
    tampered = Path("tampered-diagnostics.json")
    tampered.write_bytes((fixtures / "diagnostics.json").read_bytes() + b"\n")
    changed = [
        item.partition("=")[0] + "=" + str(tampered) if item.endswith("diagnostics.json") else item
        for item in specifications
    ]
    try:
        validate_qualification_statement(statement, changed)
    except ContractError as error:
        assert error.error_id == "qualification.statement_mismatch"
    else:
        raise AssertionError("changed raw subject bytes were accepted")

    runtime = deepcopy(load_mapping(fixtures / "runtime-manifest.json"))
    runtime["execution"]["time_mode"] = "simulation_realtime"
    validate_document(runtime)
    mismatched = write_document(runtime, "mismatched-runtime.json")
    try:
        load_bundle(fixtures / "acceptance-scenario.yaml", runtime_path=mismatched)
    except BundleValidationError as error:
        assert error.json_path == "$.runtime.execution.time_mode"
    else:
        raise AssertionError("incompatible scenario and runtime were accepted")

    scenario = deepcopy(load_mapping(fixtures / "acceptance-scenario.yaml"))
    uri = "https://schemas.example.org/consumer-check.v1.schema.json"
    schema = dumps_canonical({"$id": uri, "type": "object"})
    scenario["extension_schemas"] = [
        {
            "namespace": "org.example.consumer",
            "schema_uri": uri,
            "sha256": sha256(schema).hexdigest(),
        }
    ]
    scenario["extensions"] = {"org.example.consumer": {}}
    validate_document(scenario, extension_schemas={uri: schema})
    extended = write_document(scenario, "extended-scenario.json", extension_schemas={uri: schema})
    refused = cli("robotics_runtime_contracts.cli", ["--format", "json", "validate", str(extended)])
    assert refused.returncode == 1, refused.stderr
    refusal = json.loads(refused.stderr)["error"]
    assert refusal["error_id"] == "extension.validation_failed"
    assert refusal["path"] == "$.extension_schemas"
    return [
        "wrong_role",
        "missing_subject",
        "missing_file",
        "changed_raw_bytes",
        "mismatched_documents",
        "missing_extension_schema",
    ]


def verify_offline_outputs(fixtures: Path) -> dict[str, Any]:
    if os.name != "posix":
        return {"status": "skipped", "reason": "evidence containment requires POSIX descriptors"}
    # Only relocate the metric bytes through the public writer. Keep every pinned
    # fixture untouched, and write the incomplete offline results separately.
    root = Path("offline-inputs")
    root.mkdir()
    metrics = root / "metrics.otlp.jsonl"
    metrics.write_bytes((fixtures / metrics.name).read_bytes())
    original = load_mapping(fixtures / "evidence-index.json")
    template = {
        key: value for key, value in original.items() if key not in {"artifacts", "finalized"}
    }
    metadata = {
        "artifact_id": "offline-metrics",
        "kind": "metric",
        "storage_state": "local",
        "media_type": "application/x-ndjson",
        "retention_class": "pull-request-7d",
    }
    draft = add_evidence_artifact(create_evidence_index(template), metrics, metadata)
    index = write_document(finalize_evidence_index(draft), root / "evidence-index.json")
    run = load_mapping(fixtures / "acceptance-run.json")
    output = Path("offline-output")
    evaluated = cli(
        "robotics_acceptance_harness.cli",
        [
            "evaluate",
            "--scenario",
            str(fixtures / "acceptance-scenario.yaml"),
            "--runtime",
            str(fixtures / "runtime-manifest.json"),
            "--run-id",
            run["run_id"],
            "--domain-id",
            "primary",
            "--run-context",
            str(fixtures / "acceptance-run.json"),
            "--evidence-index",
            str(index),
            "--otel-metrics",
            str(metrics),
            "--window-start-ns",
            "1785137220000000000",
            "--window-end-ns",
            "1785137221000000000",
            "--output",
            str(output),
        ],
    )
    assert evaluated.returncode == 1, evaluated.stderr
    result = load_mapping(output / "acceptance-result.json")
    validate_role(result, "acceptance_result")
    assert result["evaluation_mode"] == "offline" and result["status"] != "passed"
    assert {"$.clock_observation", "$.observed_ros_graph", "$.shutdown"}.issubset(
        result["unevaluated"]
    )
    junit = ElementTree.parse(output / "junit.xml")
    assert junit.findall(".//skipped")
    return {"status": result["status"], "unevaluated": result["unevaluated"], "junit": "verified"}


def verify_consumers(plan: dict[str, Any]) -> dict[str, Any]:
    fixtures = Path("infra-fixtures")
    provenance = plan["consumer_provenance"]
    for item in provenance["files"]:
        path = fixtures / Path(item["path"]).name
        assert sha256(path.read_bytes()).hexdigest() == item["sha256"]
    qualifications = {}
    for name in ("single", "transport"):
        specifications = artifact_specifications(fixtures, name)
        metadata = validate_qualification_artifacts(specifications)
        arguments = [arg for spec in specifications for arg in ("--artifact", spec)]
        validated = cli(
            "robotics_runtime_contracts.cli",
            ["--format", "json", "validate-qualification", *arguments],
        )
        assert validated.returncode == 0, validated.stderr
        qualifications[name] = {
            "run_id": metadata["run_id"],
            "artifacts": len(metadata["artifacts"]),
        }
    explained = cli(
        "robotics_acceptance_harness.cli",
        [
            "explain",
            "--scenario",
            str(fixtures / "acceptance-scenario.yaml"),
            "--runtime",
            str(fixtures / "runtime-manifest.json"),
        ],
    )
    assert explained.returncode == 0, explained.stderr
    assert json.loads(explained.stdout)["policy"] == "accepted-simulation"
    installed = {}
    for name, sources in plan["source_files"].items():
        module_name = next(iter(sources)).split("/")[0]
        module = import_module(module_name)
        installed[name] = {
            "version": distribution(name).version,
            "imported_from": module.__file__,
            "source_files": len(sources),
            "verified_source_manifest_sha256": sha256(dumps_canonical(sources)).hexdigest(),
        }
    return {
        "scope": "installed public APIs and synthetic qualification fixtures",
        "n01_status": "partial",
        "installed": installed,
        "isolated_interpreter": bool(sys.flags.isolated),
        "fixture_source": provenance,
        "qualifications": qualifications,
        "negative_checks": verify_negative_inputs(
            fixtures, artifact_specifications(fixtures, "single")
        ),
        "offline": verify_offline_outputs(fixtures),
        "live_ros": {
            "status": "skipped",
            "reason": "the pinned fixtures contain no live ROS observations",
        },
        "signature_verification": {
            "status": "skipped",
            "reason": "the pinned fixtures contain no signed live bundle",
        },
    }
