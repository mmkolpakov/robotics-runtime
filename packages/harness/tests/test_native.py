from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from xml.etree import ElementTree

import pytest
from robotics_runtime_contracts import schema_for_role, schema_versions_for_role, validate_role

from robotics_acceptance_harness import native
from robotics_acceptance_harness.documents import BundleValidationError, load_bundle
from robotics_acceptance_harness.evidence import EvidenceValidationError, load_evidence_index
from tests.support import local_evidence_artifact, write_evidence_index

ROOT = Path(__file__).parents[3]
PRODUCER = ROOT / "packages/contracts/consumer-examples/minimal-native-archive/producer.py"


def produce(destination: Path, *options: str) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment["PATH"]
    completed = subprocess.run(
        [sys.executable, str(PRODUCER), "--output", str(destination), *options],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
        timeout=60,
    )
    return cast(dict[str, Any], json.loads(completed.stdout))


def evaluate(inputs: dict[str, Any], destination: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment["PATH"]
    arguments = ["robotics-acceptance", "evaluate"]
    arguments.extend(
        value
        for name, item in inputs.items()
        for value in ("--" + name.replace("_", "-"), str(item))
    )
    arguments.extend(["--output", str(destination)])
    return subprocess.run(arguments, capture_output=True, text=True, env=environment, timeout=60)


@pytest.fixture(scope="module")
def native_inputs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    return produce(tmp_path_factory.mktemp("native-archive"))


def test_public_native_archive_has_independent_assessment_and_preserves_original_bytes(
    native_inputs: dict[str, Any],
    tmp_path: Path,
) -> None:
    archive = Path(native_inputs["evidence_index"]).parent
    originals = {path: path.read_bytes() for path in archive.iterdir() if path.is_file()}
    completed = evaluate(native_inputs, tmp_path)
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    result = json.loads((tmp_path / "acceptance-result.json").read_bytes())
    validate_role(result, "acceptance_result")
    assert result["schema_version"] == "acceptance-result.v2"
    assert (
        result["original_execution"]["observation_sha256"]
        == hashlib.sha256((archive / "observation.json").read_bytes()).hexdigest()
    )
    for name, label in (
        ("run_context", "acceptance_run_sha256"),
        ("evidence_index", "evidence_index_sha256"),
    ):
        assert (
            result["original_execution"][label]
            == hashlib.sha256(Path(native_inputs[name]).read_bytes()).hexdigest()
        )
    assert result["observations"]["condition"]["value"] == 0
    assert (
        next(
            item for item in result["assertion_results"] if item["assertion_id"] == "counter-error"
        )["observed_value"]
        == 0
    )
    assert result["observations"]["delivery-clock"]["state"] == "not_applicable"
    observation = json.loads((archive / "observation.json").read_bytes())
    assert result["native_model"] == observation["native_model"]
    assert result["observations"]["loaded-model"]["value"] == result["native_model"]["sha256"]
    for name, reference in (
        ("evaluation-method.json", result["evaluation"]["method"]["configuration"]),
        ("evaluation-environment.json", result["evaluation"]["environment"]),
    ):
        raw = (tmp_path / name).read_bytes()
        assert reference["sha256"] == hashlib.sha256(raw).hexdigest()
        assert reference["size_bytes"] == len(raw)
    xml = ElementTree.parse(tmp_path / "junit.xml")
    properties = {item.attrib["name"]: item.attrib["value"] for item in xml.findall(".//property")}
    assert properties["status"] == "passed"
    assert properties["observation_sha256"] == result["original_execution"]["observation_sha256"]
    for name in ("scenario.json", "runtime.json", "observation.json"):
        document = json.loads((archive / name).read_bytes())
        assert (
            not {
                "expected_ros_graph",
                "observed_ros_graph",
                "data_plane_policy",
                "clock_observation",
                "lifecycle_states",
            }
            & document.keys()
        )
    assert {path: path.read_bytes() for path in originals} == originals


@pytest.mark.parametrize(
    "option,name,state",
    [
        ("--omit", "condition", "unobserved"),
        ("--invalid", "terminal", "invalid"),
    ],
)
def test_missing_or_invalid_required_native_fact_is_incomplete(
    tmp_path: Path,
    option: str,
    name: str,
    state: str,
) -> None:
    inputs = produce(tmp_path / "archive", option, name)
    output = tmp_path / "assessment"
    completed = evaluate(inputs, output)
    assert completed.returncode == 1, completed.stderr
    result = json.loads((output / "acceptance-result.json").read_bytes())
    assert result["status"] == "incomplete"
    assert result["observations"][name]["state"] == state
    assert f"$.observations.{name}" in result["unevaluated"]
    assert (
        ElementTree.parse(output / "junit.xml").find(
            f".//testcase[@name='observation-{name}']/skipped"
        )
        is not None
    )


def test_accepted_and_completed_command_does_not_mask_failed_postcondition(tmp_path: Path) -> None:
    inputs = produce(tmp_path / "archive", "--error", "7")
    output = tmp_path / "assessment"
    completed = evaluate(inputs, output)
    assert completed.returncode == 1, completed.stderr
    result = json.loads((output / "acceptance-result.json").read_bytes())
    assert result["observations"]["command"]["value"] is True
    assert result["observations"]["terminal"]["value"] == "completed"
    assert result["observations"]["condition"]["value"] == 7
    assert result["status"] == "failed"
    assertion = next(
        item for item in result["assertion_results"] if item["assertion_id"] == "counter-error"
    )
    assert assertion["observed_value"] == 7
    assert assertion["status"] == "failed"


def test_versioned_role_loading_keeps_v1_defaults_and_refuses_mixed_bundle(
    native_inputs: dict[str, Any],
) -> None:
    assert schema_for_role("acceptance_scenario") == "acceptance-scenario.v1"
    assert schema_for_role("runtime_manifest") == "runtime-manifest.v1"
    assert schema_for_role("acceptance_scenario", version=2) == "acceptance-scenario.v2"
    assert schema_versions_for_role("acceptance_scenario") == (
        "acceptance-scenario.v1",
        "acceptance-scenario.v2",
    )
    bundle = load_bundle(native_inputs["scenario"], runtime_path=native_inputs["runtime"])
    assert bundle.scenario.schema_version == "acceptance-scenario.v2"
    legacy = ROOT / "packages/harness/tests/fixtures/simulation"
    with pytest.raises(BundleValidationError, match="v2 scenarios require v2 runtime"):
        load_bundle(native_inputs["scenario"], runtime_path=legacy / "runtime.yaml")
    with pytest.raises(BundleValidationError, match="v1 scenarios require v1 runtime"):
        load_bundle(legacy / "scenario.yaml", runtime_path=native_inputs["runtime"])


def test_verified_evidence_sdk_returns_captured_bytes_and_checks_limits(tmp_path: Path) -> None:
    payload = tmp_path / "payload.json"
    original = b'{"value":0}\n'
    payload.write_bytes(original)
    index = write_evidence_index(
        tmp_path / "index.json",
        run_id="run-00000000-0000-4000-8000-000000000001",
        artifacts=[local_evidence_artifact(payload)],
    )
    evidence = load_evidence_index(index)
    captured = evidence.read_local(payload, max_raw_evidence_bytes=len(original))
    with pytest.raises(EvidenceValidationError, match="byte budget"):
        evidence.read_local(payload, max_raw_evidence_bytes=len(original) - 1)
    with pytest.raises(EvidenceValidationError, match="not verified local evidence"):
        evidence.read_local(tmp_path / "outside.json")
    payload.write_bytes(b'{"value":9}\n')
    assert captured == original
    with pytest.raises(EvidenceValidationError, match="expected"):
        evidence.read_local(payload)


@pytest.mark.parametrize(
    "option,missing",
    [
        ("--no-criteria", "$.assertions"),
        ("--all-not-applicable", "$.observations"),
    ],
)
def test_empty_criterion_or_native_coverage_cannot_produce_passed_verdict(
    tmp_path: Path, option: str, missing: str
) -> None:
    inputs = produce(tmp_path / "archive", option)
    output = tmp_path / "assessment"
    completed = evaluate(inputs, output)
    assert completed.returncode == 1, completed.stderr
    result = json.loads((output / "acceptance-result.json").read_bytes())
    assert result["status"] == "incomplete"
    assert missing in result["unevaluated"]


def test_native_discrete_simulation_is_evaluated_without_ros(tmp_path: Path) -> None:
    inputs = produce(tmp_path / "archive", "--simulation")
    output = tmp_path / "assessment"
    completed = evaluate(inputs, output)
    assert completed.returncode == 0, completed.stderr
    result = json.loads((output / "acceptance-result.json").read_bytes())
    assert result["execution"]["target_environment"] == "simulation"
    assert result["execution"]["plant_backend"] == "org.example.discrete-counter"
    assert result["observations"]["condition"]["value"] == 0
    assert result["native_model"]["sha256"] == result["observations"]["loaded-model"]["value"]
    assert result["status"] == "passed"


def test_native_raw_only_scope_needs_no_fabricated_otlp_input(tmp_path: Path) -> None:
    inputs = produce(tmp_path / "archive", "--raw-only")
    assert "otel_metrics" not in inputs
    output = tmp_path / "assessment"
    completed = evaluate(inputs, output)
    assert completed.returncode == 1, completed.stderr
    result = json.loads((output / "acceptance-result.json").read_bytes())
    assert result["status"] == "incomplete"
    assert "$.assertions" in result["unevaluated"]
    assert result["observations"]["condition"]["value"] == 0
    assert not any(
        item["assertion_id"].startswith("counter-") for item in result["assertion_results"]
    )


def test_declared_metric_method_rejects_an_omitted_otlp_input(
    native_inputs: dict[str, Any], tmp_path: Path
) -> None:
    inputs = {key: value for key, value in native_inputs.items() if key != "otel_metrics"}
    completed = evaluate(inputs, tmp_path / "assessment")
    assert completed.returncode == 2
    assert "requires --otel-metrics" in completed.stderr


def test_public_scenario_resolve_dispatches_the_declared_native_version(
    native_inputs: dict[str, Any], tmp_path: Path
) -> None:
    scenario_path = Path(native_inputs["scenario"])
    original = scenario_path.read_bytes()
    overlay = tmp_path / "overlay.json"
    overlay.write_text(json.dumps({"evidence_policy": {"max_upload_lag_sec": 5}}), encoding="utf-8")
    output = tmp_path / "resolved.json"
    completed = subprocess.run(
        [
            "robotics-contracts",
            "scenario",
            "resolve",
            str(scenario_path),
            "--overlay",
            str(overlay),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    resolved = json.loads(output.read_bytes())
    assert resolved["schema_version"] == "acceptance-scenario.v2"
    assert resolved["evidence_policy"]["max_upload_lag_sec"] == 5
    assert scenario_path.read_bytes() == original
    validate_role(resolved, "acceptance_scenario")


def test_environment_inventory_changes_with_protobuf_drift_and_is_order_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = SimpleNamespace(metadata={"Name": "protobuf"}, version="7.36.1")
    second = SimpleNamespace(metadata={"Name": "Example_Plugin"}, version="1")
    monkeypatch.setattr(native, "distributions", lambda: [first, second])
    original = native._evaluation_environment(tmp_path / "first.json")
    monkeypatch.setattr(native, "distributions", lambda: [second, first])
    reordered = native._evaluation_environment(tmp_path / "reordered.json")
    assert reordered["sha256"] == original["sha256"]
    first.version = "7.36.2"
    changed = native._evaluation_environment(tmp_path / "changed.json")
    assert changed["sha256"] != original["sha256"]
    metadata = json.loads((tmp_path / "changed.json").read_bytes())
    assert metadata["packages"] == {"example-plugin": "1", "protobuf": "7.36.2"}


def test_environment_inventory_refuses_ambiguous_distribution_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    distributions = [
        SimpleNamespace(metadata={"Name": "Example_Plugin"}, version="1"),
        SimpleNamespace(metadata={"Name": "example-plugin"}, version="2"),
    ]
    monkeypatch.setattr(native, "distributions", lambda: distributions)
    with pytest.raises(BundleValidationError, match="ambiguous versions"):
        native._evaluation_environment(tmp_path / "environment.json")
