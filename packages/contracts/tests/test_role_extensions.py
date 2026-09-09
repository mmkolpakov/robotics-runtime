from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from robotics_runtime_contracts import (
    ExtensionValidationError,
    contract_roles,
    load_mapping,
    validate_role,
)
from robotics_runtime_contracts.qualification import (
    ARTIFACT_ROLES,
    QualificationError,
    load_qualification_artifact,
)
from robotics_runtime_contracts.statements import create_qualification_statement
from tests.extension_support import NAMESPACE, RAW_SCHEMA, SCHEMA_URI, SCHEMAS, with_extension
from tests.support import qualification_specifications
from tests.test_trace_contracts import qualification_policy

PACKAGE = Path(__file__).parents[1]
FIXTURES = {
    "acceptance_aggregate": "consumer-examples/minimal-simulation/acceptance-aggregate.yaml",
    "acceptance_result": "consumer-examples/minimal-simulation/acceptance-result.yaml",
    "acceptance_run": "consumer-examples/minimal-simulation/acceptance-run.yaml",
    "acceptance_scenario": "consumer-examples/minimal-simulation/scenario.yaml",
    "artifact_receipt": "tests/fixtures/qualification/inference/evaluator-receipt.json",
    "artifact_verification": "tests/fixtures/qualification/inference/evaluator-verification.json",
    "campaign_summary": "tests/fixtures/campaign/valid/legacy-shortfall.json",
    "causal_chain": "tests/fixtures/qualification/transport/causal-chain.json",
    "clock_relation": "tests/fixtures/qualification/transport/clock-relation.json",
    "conformance_result": "tests/fixtures/qualification/inference/provider-conformance.json",
    "dataset_manifest": "tests/fixtures/dataset/valid/camera-mcap.yaml",
    "evidence_index": "consumer-examples/minimal-simulation/evidence-index.yaml",
    "execution_permit": "tests/fixtures/physical/valid/hil-permit.yaml",
    "execution_trust_policy": "consumer-examples/execution-trust-policy/trust-policy.json",
    "execution_verification": "tests/fixtures/physical/valid/hil-verification.yaml",
    "model_artifact_manifest": "tests/fixtures/qualification/inference/model.json",
    "qualification_profile": "consumer-examples/flight-controller/qualification-profile.json",
    "recording_summary": "tests/fixtures/qualification/inference/recording-summary.json",
    "robot_description": "consumer-examples/robot-description/sim/robot-description-sdf.json",
    "runtime_manifest": "consumer-examples/minimal-simulation/runtime-manifest.yaml",
    "transport_channel": "tests/fixtures/qualification/transport/channel.json",
    "transport_channel_observation": (
        "tests/fixtures/qualification/transport/channel-observation.json"
    ),
    "transport_qualification_result": "tests/fixtures/qualification/transport/transport.json",
}
LEGACY_ROLES = (
    "acceptance_result",
    "dataset_manifest",
    "evidence_index",
    "execution_permit",
    "execution_verification",
    "model_artifact_manifest",
    "runtime_manifest",
)


def document_for_role(role: str) -> dict[str, Any]:
    if role == "qualification_bundle":
        return create_qualification_statement(qualification_specifications("inference"))
    if role == "qualification_policy":
        return qualification_policy()
    if role == "acceptance_observation":
        result = load_mapping(PACKAGE / FIXTURES["acceptance_result"])
        return {
            "schema_version": "acceptance-observation.v1",
            "observation_id": "fixture.observation",
            **{
                key: result[key]
                for key in (
                    "run_id",
                    "scenario_id",
                    "domain_id",
                    "started_at",
                    "finished_at",
                    "runtime_observation",
                    "observed_ros_graph",
                    "lifecycle_states",
                )
            },
            "evidence": [
                {key: item[key] for key in ("uri", "sha256", "size_bytes", "media_type")}
                for item in result["evidence"]
            ],
        }
    return load_mapping(PACKAGE / FIXTURES[role])


def extended_document(role: str) -> dict[str, Any]:
    document = document_for_role(role)
    if role == "qualification_bundle":
        document["predicate"] = with_extension(document["predicate"])
        return document
    return with_extension(document)


def test_every_public_role_has_an_extension_fixture() -> None:
    assert set(contract_roles()) == set(FIXTURES) | {
        "qualification_bundle",
        "qualification_policy",
        "acceptance_observation",
    }


@pytest.mark.parametrize("role", contract_roles())
def test_public_role_accepts_verified_extension_without_mutating_input(role: str) -> None:
    document = extended_document(role)
    original = deepcopy(document)
    validate_role(document_for_role(role), role)
    validate_role(document, role, extension_schemas=SCHEMAS)
    assert document == original


@pytest.mark.parametrize("role", contract_roles())
@pytest.mark.parametrize("failure", ["payload", "missing-schema", "changed-schema"])
def test_public_role_rejects_invalid_extension(role: str, failure: str) -> None:
    document = extended_document(role)
    schemas = SCHEMAS
    prefix = "$.predicate" if role == "qualification_bundle" else "$"
    path = f"{prefix}.extension_schemas[0].schema_uri"
    if failure == "payload":
        payload = document["predicate"] if role == "qualification_bundle" else document
        payload["extensions"][NAMESPACE]["mission_id"] = ""
        path = f'{prefix}.extensions["{NAMESPACE}"].mission_id'
    elif failure == "missing-schema":
        schemas = {}
    else:
        schemas = {SCHEMA_URI: RAW_SCHEMA + b" "}
        path = f"{prefix}.extension_schemas[0].sha256"
    with pytest.raises(ExtensionValidationError) as raised:
        validate_role(document, role, extension_schemas=schemas)
    assert raised.value.json_path == path


@pytest.mark.parametrize("role", LEGACY_ROLES)
def test_legacy_unpinned_payload_remains_valid_until_declarations_opt_in(role: str) -> None:
    document = document_for_role(role)
    document["extensions"] = {NAMESPACE: {"mission_id": ""}}
    validate_role(document, role)
    document["extension_schemas"] = []
    with pytest.raises(ExtensionValidationError, match="exactly match"):
        validate_role(document, role, extension_schemas=SCHEMAS)


@pytest.mark.parametrize("role", sorted(set(contract_roles()) - set(LEGACY_ROLES)))
def test_new_extension_roles_reject_undeclared_payloads(role: str) -> None:
    document = extended_document(role)
    payload = document["predicate"] if role == "qualification_bundle" else document
    del payload["extension_schemas"]
    with pytest.raises(ExtensionValidationError, match="exactly match"):
        validate_role(document, role, extension_schemas=SCHEMAS)


def test_bundle_namespace_diagnostics_include_predicate() -> None:
    document = extended_document("qualification_bundle")
    document["predicate"]["extension_schemas"] *= 2
    with pytest.raises(ExtensionValidationError, match="unique") as raised:
        validate_role(document, "qualification_bundle", extension_schemas=SCHEMAS)
    assert raised.value.json_path == "$.predicate.extension_schemas"


@pytest.mark.parametrize("kind,role", sorted(ARTIFACT_ROLES.items()))
def test_qualification_loader_checks_extensions_for_every_contract_artifact(
    kind: str, role: str, tmp_path: Path
) -> None:
    document = extended_document(role)
    raw = json.dumps(document, indent=3).encode()
    source = tmp_path / "artifact.json"
    source.write_bytes(raw)
    specification = f"{kind}:artifact.json={source}"
    loaded = load_qualification_artifact(specification, SCHEMAS)
    assert loaded.document == document
    assert loaded.sha256 == sha256(raw).hexdigest()
    with pytest.raises(QualificationError) as raised:
        load_qualification_artifact(specification)
    assert raised.value.error_id == "extension.validation_failed"
