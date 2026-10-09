from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
import yaml
from robotics_runtime_contracts import RobotDescriptionBindingError

from robotics_acceptance_harness.documents import (
    BundleValidationError,
    load_bundle,
    load_document,
    load_document_bytes,
)

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


def _dataset_document(member_count: int = 2) -> dict[str, Any]:
    fixture = (
        Path(__file__).resolve().parents[2]
        / "contracts/tests/fixtures/dataset/valid/camera-mcap.yaml"
    )
    document = yaml.safe_load(fixture.read_text())
    assert isinstance(document, dict)
    assert document["schema_version"] == "dataset-manifest.v2"
    for channel, count in zip(document["channels"], (2, 1), strict=True):
        channel["message_count"] = count

    def reference(name: str, digest: str) -> dict[str, Any]:
        return {"uri": "s3://fixture-bags/" + name, "sha256": digest * 64, "size_bytes": 128}

    document["bag"] = {
        "storage_id": "mcap",
        "metadata": reference("metadata.yaml", "c"),
        "message_count": 3,
        "members": [
            {
                "segment_index": index,
                "relative_path": f"recording_{index}.mcap",
                "recording": reference(f"recording_{index}.mcap", digest),
                "recording_summary": reference(f"recording_{index}.summary.json", summary),
            }
            for index, digest, summary in ((0, "a", "d"), (1, "b", "e"))[:member_count]
        ],
    }
    return document


@pytest.mark.parametrize("member_count", [1, 2])
def test_load_dataset_role_accepts_one_canonical_bag_shape(member_count: int) -> None:
    raw = json.dumps(_dataset_document(member_count)).encode()
    document = load_document_bytes(
        raw, source=Path("dataset.json"), expected_role="dataset_manifest"
    )
    assert document.schema_version == "dataset-manifest.v2"
    assert len(document.data["bag"]["members"]) == member_count
    assert document.sha256 == sha256(raw).hexdigest()


@pytest.mark.parametrize("schema_version", ["dataset-manifest.v1", "dataset-manifest.v3"])
def test_load_dataset_role_refuses_unsupported_versions(schema_version: str) -> None:
    raw = json.dumps({"schema_version": schema_version}).encode()
    with pytest.raises(BundleValidationError) as caught:
        load_document_bytes(raw, source=Path("dataset.json"), expected_role="dataset_manifest")
    assert caught.value.json_path == "$.schema_version"


def test_v2_dataset_cannot_fall_back_to_single_artifact_validation() -> None:
    document = _dataset_document(1)
    document["artifact"] = document.pop("bag")["members"][0]["recording"]
    raw = json.dumps(document).encode()
    with pytest.raises(BundleValidationError, match="invalid"):
        load_document_bytes(raw, source=Path("dataset.json"), expected_role="dataset_manifest")


def test_loaded_bag_dataset_freezes_members_and_captured_digest(tmp_path: Path) -> None:
    path = tmp_path / "dataset.json"
    raw = json.dumps(_dataset_document(), indent=2).encode()
    path.write_bytes(raw)
    document = load_document(path, expected_role="dataset_manifest")
    path.write_bytes(b"replaced after load")
    assert document.sha256 == sha256(raw).hexdigest()
    assert isinstance(document.data["bag"]["members"], tuple)
    assert len(document.data["bag"]["members"]) == 2
    assert document.data["bag"]["members"][1]["relative_path"] == "recording_1.mcap"
    with pytest.raises(TypeError):
        document.data["bag"]["members"][0]["recording"]["sha256"] = "f" * 64


_EXTENSION_URI = "urn:example:runtime-settings:v1"
_EXTENSION_SCHEMA = (
    b'{"$schema":"https://json-schema.org/draft/2020-12/schema",'
    b'"$id":"urn:example:runtime-settings:v1",'
    b'"type":"object","required":["sample_count"],'
    b'"properties":{"sample_count":{"type":"integer","minimum":1}},'
    b'"additionalProperties":false}'
)


def _runtime_with_extension(tmp_path: Path, *, pinned: bool = True) -> Path:
    runtime = yaml.safe_load((FIXTURES / "runtime.yaml").read_text(encoding="utf-8"))
    runtime["extensions"] = {"org.example.settings": {"sample_count": 3}}
    if pinned:
        runtime["extension_schemas"] = [
            {
                "namespace": "org.example.settings",
                "schema_uri": _EXTENSION_URI,
                "sha256": sha256(_EXTENSION_SCHEMA).hexdigest(),
            }
        ]
    path = tmp_path / "runtime.yaml"
    path.write_text(yaml.safe_dump(runtime), encoding="utf-8")
    return path


def test_bundle_uses_caller_schema_registry_for_runtime(tmp_path: Path) -> None:
    path = _runtime_with_extension(tmp_path)
    registry = {_EXTENSION_URI: _EXTENSION_SCHEMA}
    direct = load_document(path, expected_role="runtime_manifest", extension_schemas=registry)
    bundle = load_bundle(FIXTURES / "scenario.yaml", runtime_path=path, extension_schemas=registry)
    assert bundle.runtime.data == direct.data
    assert bundle.runtime.sha256 == direct.sha256
    assert bundle.runtime.data["extensions"]["org.example.settings"]["sample_count"] == 3


@pytest.mark.parametrize(
    ("registry", "message"),
    [
        ({}, "schema document was not supplied"),
        ({_EXTENSION_URI: _EXTENSION_SCHEMA + b" "}, "schema digest does not match"),
    ],
)
def test_bundle_preserves_runtime_extension_admission(
    tmp_path: Path, registry: dict[str, bytes], message: str
) -> None:
    path = _runtime_with_extension(tmp_path)
    with pytest.raises(BundleValidationError, match=message):
        load_document(path, expected_role="runtime_manifest", extension_schemas=registry)
    with pytest.raises(BundleValidationError, match=message):
        load_bundle(FIXTURES / "scenario.yaml", runtime_path=path, extension_schemas=registry)


def test_bundle_validates_runtime_payload_before_alignment(tmp_path: Path) -> None:
    path = _runtime_with_extension(tmp_path)
    runtime = yaml.safe_load(path.read_text(encoding="utf-8"))
    runtime["extensions"]["org.example.settings"]["sample_count"] = 0
    path.write_text(yaml.safe_dump(runtime), encoding="utf-8")
    with pytest.raises(BundleValidationError, match="less than the minimum"):
        load_bundle(
            FIXTURES / "scenario.yaml",
            runtime_path=path,
            extension_schemas={_EXTENSION_URI: _EXTENSION_SCHEMA},
        )


def test_bundle_preserves_legacy_unpinned_runtime_extension(tmp_path: Path) -> None:
    path = _runtime_with_extension(tmp_path, pinned=False)
    bundle = load_bundle(FIXTURES / "scenario.yaml", runtime_path=path)
    assert bundle.runtime.data["extensions"]["org.example.settings"]["sample_count"] == 3


_OPTIONAL_ARTIFACTS = {
    "model": "model_artifact_manifest",
    "dataset": "dataset_manifest",
    "permit": "execution_permit",
    "verification": "execution_verification",
}


def _write_artifact(path: Path, document: dict[str, Any]) -> str:
    raw = (json.dumps(document, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return sha256(raw).hexdigest()


def _extended_artifact_bundle(
    tmp_path: Path, role: str, *, sample_count: int = 3
) -> tuple[Path, dict[str, Any]]:
    def extend(document: dict[str, Any]) -> dict[str, Any]:
        document["extensions"] = {"org.example.settings": {"sample_count": sample_count}}
        document["extension_schemas"] = [
            {
                "namespace": "org.example.settings",
                "schema_uri": _EXTENSION_URI,
                "sha256": sha256(_EXTENSION_SCHEMA).hexdigest(),
            }
        ]
        return document

    if role == "model":
        fixtures = (
            Path(__file__).resolve().parents[2] / "contracts/tests/fixtures/qualification/inference"
        )
        scenario = json.loads((fixtures / "scenario.json").read_bytes())
        runtime = json.loads((fixtures / "runtime.json").read_bytes())
        model = extend(json.loads((fixtures / "model.json").read_bytes()))
        digest = _write_artifact(tmp_path / "model.json", model)
        scenario["model_manifest_sha256"] = digest
        runtime["workload"]["model"]["manifest_sha256"] = digest
        _write_artifact(tmp_path / "scenario.json", scenario)
        _write_artifact(tmp_path / "runtime.json", runtime)
        return tmp_path / "scenario.json", {
            "runtime_path": tmp_path / "runtime.json",
            "model_path": tmp_path / "model.json",
            "dataset_path": fixtures / "dataset.json",
        }

    if role == "dataset":
        scenario = yaml.safe_load((FIXTURES / "scenario.yaml").read_bytes())
        scenario["dataset_manifest_sha256"] = _write_artifact(
            tmp_path / "dataset.json", extend(_dataset_document())
        )
        _write_artifact(tmp_path / "scenario.json", scenario)
        return tmp_path / "scenario.json", {
            "runtime_path": FIXTURES / "runtime.yaml",
            "dataset_path": tmp_path / "dataset.json",
        }

    fixtures = FIXTURES.parent / "physical"
    runtime = json.loads((fixtures / "hil-runtime.json").read_bytes())
    permit = json.loads((fixtures / "hil-permit.json").read_bytes())
    verification = json.loads((fixtures / "hil-verification.json").read_bytes())
    extend(permit if role == "permit" else verification)
    permit_digest = _write_artifact(tmp_path / "permit.json", permit)
    verification["permit_sha256"] = permit_digest
    verification_digest = _write_artifact(tmp_path / "verification.json", verification)
    runtime["authorization"]["permit_sha256"] = permit_digest
    runtime["authorization"]["execution_verification_sha256"] = verification_digest
    _write_artifact(tmp_path / "runtime.json", runtime)
    return fixtures / "hil-scenario.yaml", {
        "runtime_path": tmp_path / "runtime.json",
        "permit_path": tmp_path / "permit.json",
        "verification_path": tmp_path / "verification.json",
        "now": datetime(2026, 7, 12, 10, 0, tzinfo=UTC),
    }


@pytest.mark.parametrize("role", _OPTIONAL_ARTIFACTS)
def test_bundle_uses_caller_schema_registry_for_optional_artifact(
    tmp_path: Path, role: str
) -> None:
    scenario, arguments = _extended_artifact_bundle(tmp_path, role)
    registry = {_EXTENSION_URI: _EXTENSION_SCHEMA}
    direct = load_document(
        arguments[f"{role}_path"],
        expected_role=_OPTIONAL_ARTIFACTS[role],
        extension_schemas=registry,
    )
    bundle = load_bundle(scenario, extension_schemas=registry, **arguments)
    loaded = getattr(bundle, role)
    assert loaded.data == direct.data
    assert loaded.sha256 == direct.sha256


@pytest.mark.parametrize("role", _OPTIONAL_ARTIFACTS)
@pytest.mark.parametrize(
    ("failure", "message"),
    [
        ("missing-registry", "schema document was not supplied"),
        ("changed-schema", "schema digest does not match"),
        ("payload", "less than the minimum"),
    ],
)
def test_bundle_preserves_optional_artifact_extension_admission(
    tmp_path: Path, role: str, failure: str, message: str
) -> None:
    scenario, arguments = _extended_artifact_bundle(
        tmp_path, role, sample_count=0 if failure == "payload" else 3
    )
    registry = {_EXTENSION_URI: _EXTENSION_SCHEMA}
    if failure == "missing-registry":
        registry = {}
    elif failure == "changed-schema":
        registry = {_EXTENSION_URI: _EXTENSION_SCHEMA + b" "}
    with pytest.raises(BundleValidationError, match=message):
        load_bundle(scenario, extension_schemas=registry, **arguments)
