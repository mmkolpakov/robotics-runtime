from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from robotics_runtime_contracts import RobotDescriptionBindingError

from robotics_acceptance_harness.documents import BundleValidationError, load_bundle

FIXTURES = Path(__file__).parent / "fixtures" / "simulation"


def test_load_bundle_cross_checks_execution_documents() -> None:
    bundle = load_bundle(
        FIXTURES / "scenario.yaml",
        runtime_path=FIXTURES / "runtime.yaml",
    )

    assert bundle.scenario.schema_version == "acceptance-scenario.v1"
    assert bundle.runtime.schema_version == "runtime-manifest.v1"
    assert bundle.runtime.data["workload"]["kind"] == "none"


def test_load_bundle_rejects_runtime_mode_mismatch(tmp_path: Path) -> None:
    runtime = yaml.safe_load((FIXTURES / "runtime.yaml").read_text(encoding="utf-8"))
    runtime["execution"]["time_mode"] = "simulation_stepped"
    runtime_path = tmp_path / "runtime.yaml"
    runtime_path.write_text(yaml.safe_dump(runtime), encoding="utf-8")

    with pytest.raises(BundleValidationError) as caught:
        load_bundle(FIXTURES / "scenario.yaml", runtime_path=runtime_path)

    assert caught.value.json_path == "$.runtime.execution.time_mode"


def test_load_bundle_requires_runtime() -> None:
    with pytest.raises(BundleValidationError, match="requires a runtime manifest"):
        load_bundle(FIXTURES / "scenario.yaml")


def test_load_bundle_rejects_a_document_with_the_wrong_role() -> None:
    with pytest.raises(BundleValidationError, match="expected runtime-manifest.v1"):
        load_bundle(FIXTURES / "scenario.yaml", runtime_path=FIXTURES / "scenario.yaml")


def test_load_bundle_requires_declared_provider_capabilities(tmp_path: Path) -> None:
    runtime = yaml.safe_load((FIXTURES / "runtime.yaml").read_text(encoding="utf-8"))
    runtime["provider_bindings"][0]["capabilities"] = []
    runtime_path = tmp_path / "runtime.yaml"
    runtime_path.write_text(yaml.safe_dump(runtime), encoding="utf-8")

    with pytest.raises(BundleValidationError, match="simulated_physics"):
        load_bundle(FIXTURES / "scenario.yaml", runtime_path=runtime_path)


def test_load_bundle_requires_one_complete_semantic_scene_binding(tmp_path: Path) -> None:
    scenario = yaml.safe_load((FIXTURES / "scenario.yaml").read_text(encoding="utf-8"))
    scenario["provider_requirements"]["scene"] = {
        "semantic_scene_id": "neutral-cell",
        "required_entities": ["camera"],
        "required_interfaces": ["/camera/image"],
        "physical_parameters": {"gravity_m_s2": 9.80665},
    }
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(yaml.safe_dump(scenario), encoding="utf-8")
    runtime = yaml.safe_load((FIXTURES / "runtime.yaml").read_text(encoding="utf-8"))
    runtime["provider_bindings"][0]["scene"] = {
        "semantic_scene_id": "neutral-cell",
        "entities": ["camera"],
        "interfaces": [],
        "physical_parameters": {"gravity_m_s2": 9.80665},
    }
    runtime["provider_bindings"].append(
        {
            "target_id": "camera-provider",
            "provider": {
                "kind": "sensor_provider",
                "implementation_id": "fixture_camera",
                "version": "1.0.0",
                "configuration_sha256": "1" * 64,
            },
            "qualification_profile_sha256": "2" * 64,
            "conformance_result_sha256": "4" * 64,
            "capabilities": [],
            "scene": {
                "semantic_scene_id": "neutral-cell",
                "entities": [],
                "interfaces": ["/camera/image"],
                "physical_parameters": {"gravity_m_s2": 9.80665},
            },
        }
    )
    runtime_path = tmp_path / "runtime.yaml"
    runtime_path.write_text(yaml.safe_dump(runtime), encoding="utf-8")

    with pytest.raises(BundleValidationError, match="no single provider scene"):
        load_bundle(scenario_path, runtime_path=runtime_path)


def _robot_bundle_paths(
    tmp_path: Path,
    expected: str | None,
    observed: str | None,
) -> tuple[Path, Path]:
    scenario = yaml.safe_load((FIXTURES / "scenario.yaml").read_text(encoding="utf-8"))
    runtime = yaml.safe_load((FIXTURES / "runtime.yaml").read_text(encoding="utf-8"))
    if expected is not None:
        scenario["workload"] = {"robot_description_sha256": expected}
    if observed is not None:
        runtime["workload"]["robot_description"] = {"sha256": observed}
    scenario_path, runtime_path = tmp_path / "scenario.yaml", tmp_path / "runtime.yaml"
    scenario_path.write_text(yaml.safe_dump(scenario), encoding="utf-8")
    runtime_path.write_text(yaml.safe_dump(runtime), encoding="utf-8")
    return scenario_path, runtime_path


@pytest.mark.parametrize(
    "expected, observed", [("a" * 64, "a" * 64), (None, "a" * 64), (None, None)]
)
def test_load_bundle_accepts_optional_robot_description_bindings(
    tmp_path: Path,
    expected: str | None,
    observed: str | None,
) -> None:
    scenario_path, runtime_path = _robot_bundle_paths(tmp_path, expected, observed)
    bundle = load_bundle(scenario_path, runtime_path=runtime_path)
    binding = bundle.runtime.data["workload"].get("robot_description")
    assert binding == ({"sha256": observed} if observed is not None else None)


@pytest.mark.parametrize("observed", [None, "b" * 64])
def test_load_bundle_rejects_missing_or_mismatched_robot_description(
    tmp_path: Path,
    observed: str | None,
) -> None:
    scenario_path, runtime_path = _robot_bundle_paths(tmp_path, "a" * 64, observed)
    with pytest.raises(BundleValidationError) as caught:
        load_bundle(scenario_path, runtime_path=runtime_path)
    assert caught.value.json_path == "$.runtime.workload.robot_description.sha256"
    assert isinstance(caught.value.__cause__, RobotDescriptionBindingError)
