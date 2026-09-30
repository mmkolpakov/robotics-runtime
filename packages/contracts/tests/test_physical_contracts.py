from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from robotics_runtime_contracts import (
    ContractError,
    ContractValidationError,
    SemanticValidationError,
    validate_document,
)
from robotics_runtime_contracts.document_ops import create_execution_permit
from tests.support import load_fixture

FIXTURES = Path(__file__).parent / "fixtures" / "physical" / "valid"


def test_contracts_accept_real_target_only_as_observation() -> None:
    scenario = load_fixture(FIXTURES / "hil-scenario.yaml")
    scenario["execution"]["target_environment"] = "real_robot"
    scenario["execution"]["physical_effect"] = "observation"

    permit = load_fixture(FIXTURES / "hil-permit.yaml")
    permit["target"]["environment"] = "real_robot"
    permit["allowed_physical_effect"] = "observation"

    runtime = load_fixture(FIXTURES / "hil-runtime.yaml")
    runtime["execution"]["target_environment"] = "real_robot"

    result = load_fixture(FIXTURES / "hil-result.yaml")
    result["execution"]["target_environment"] = "real_robot"
    result["authorization"]["target"]["environment"] = "real_robot"

    validate_document(scenario)
    validate_document(permit)
    validate_document(runtime)
    validate_document(result)


def test_physical_scenario_requires_a_forbidden_interface() -> None:
    scenario = load_fixture(FIXTURES / "hil-scenario.yaml")
    scenario["forbidden_ros_graph"] = {"topics": [], "services": [], "actions": []}

    with pytest.raises(SemanticValidationError, match="at least one forbidden"):
        validate_document(scenario)


def test_runtime_rejects_duplicate_target_identity() -> None:
    runtime = load_fixture(FIXTURES / "hil-runtime.yaml")
    duplicate = deepcopy(runtime["physical_targets"][0])
    duplicate["target_id"] = "controller-beta"
    runtime["physical_targets"].append(duplicate)

    with pytest.raises(SemanticValidationError, match="identity_sha256 values must be unique"):
        validate_document(runtime)


def test_permit_rejects_same_operator_and_approver() -> None:
    permit = load_fixture(FIXTURES / "hil-permit.yaml")
    permit["approver_id"] = permit["operator_id"]

    with pytest.raises(SemanticValidationError, match="must differ from operator_id"):
        validate_document(permit)


def test_permit_is_bounded_to_thirty_minutes() -> None:
    permit = load_fixture(FIXTURES / "hil-permit.yaml")
    permit["expires_at"] = "2026-07-12T10:30:01Z"

    with pytest.raises(SemanticValidationError, match="no more than 30 minutes"):
        validate_document(permit)


@pytest.mark.parametrize(
    ("fixture_name", "mutation"),
    (
        (
            "hil-scenario.yaml",
            lambda document: document["execution"].update({"physical_effect": "actuation"}),
        ),
        (
            "hil-permit.yaml",
            lambda document: document["hardware_scope"].append("actuator"),
        ),
        (
            "hil-runtime.yaml",
            lambda document: document["physical_targets"][0].update({"scope": "actuator"}),
        ),
    ),
)
def test_foundation_rejects_actuation(
    fixture_name: str,
    mutation: Any,
) -> None:
    document = load_fixture(FIXTURES / fixture_name)
    mutation(document)

    with pytest.raises(ContractValidationError):
        validate_document(document)


def test_verification_requires_one_signer_for_each_role() -> None:
    verification = load_fixture(FIXTURES / "hil-verification.yaml")
    verification["signers"][1]["role"] = "operator"

    with pytest.raises(SemanticValidationError, match="one operator and one approver"):
        validate_document(verification)


def test_verification_rejects_reused_signer_identity() -> None:
    verification = load_fixture(FIXTURES / "hil-verification.yaml")
    verification["signers"][1]["identity"] = verification["signers"][0]["identity"]

    with pytest.raises(SemanticValidationError, match="identity values must be unique"):
        validate_document(verification)


def test_result_target_environment_must_match_execution() -> None:
    result = load_fixture(FIXTURES / "hil-result.yaml")
    result["authorization"]["target"]["environment"] = "real_robot"

    with pytest.raises(SemanticValidationError, match="must match execution"):
        validate_document(result)


def test_passed_physical_result_requires_timing_within_policy() -> None:
    result = load_fixture(FIXTURES / "hil-result.yaml")
    result["hardware_clock_observation"]["within_policy"] = False

    with pytest.raises(SemanticValidationError, match="timing within policy"):
        validate_document(result)


def test_hardware_clock_source_must_match_protocol() -> None:
    result = load_fixture(FIXTURES / "hil-result.yaml")
    result["hardware_clock_observation"]["source"] = "pmc"

    with pytest.raises(SemanticValidationError, match="must match sync_protocol"):
        validate_document(result)


def test_hardware_clock_evidence_must_be_listed() -> None:
    result = load_fixture(FIXTURES / "hil-result.yaml")
    result["hardware_clock_observation"]["evidence_sha256"] = "9" * 64

    with pytest.raises(SemanticValidationError) as caught:
        validate_document(result)
    assert caught.value.json_path == "$.hardware_clock_observation.evidence_sha256"


def test_passed_result_rejects_forbidden_interface_violation() -> None:
    result = load_fixture(FIXTURES / "hil-result.yaml")
    result["forbidden_graph_observation"] = {
        "passed": False,
        "checked_topics": ["/cmd_vel"],
        "checked_services": [],
        "checked_actions": [],
        "violations": [{"kind": "topic", "name": "/cmd_vel"}],
    }

    with pytest.raises(ContractValidationError, match="expected to be empty") as caught:
        validate_document(result)
    assert caught.value.error_id == "schema.validation_failed"
    assert caught.value.json_path == "$.forbidden_graph_observation.violations"


def _permit(now: datetime) -> dict[str, Any]:
    return create_execution_permit(
        scenario_sha256="a" * 64,
        subject_digest="sha256:" + "b" * 64,
        trust_policy_sha256="c" * 64,
        environment="hil",
        target_id="bench-01",
        identity_kind="udev_serial",
        identity_sha256="d" * 64,
        hardware_scope=["controller"],
        operator_id="operator",
        approver_id="approver",
        interlock_reference="s3://robotics-evidence/interlocks/bench-01.json",
        interlock_sha256="e" * 64,
        validity_sec=600,
        now=now,
    )


def test_permit_rejects_a_naive_issue_time() -> None:
    with pytest.raises(ContractError, match="timezone-aware") as caught:
        _permit(datetime(2026, 7, 12, 10, 0))

    assert caught.value.error_id == "input.invalid_timestamp"


def test_permit_normalizes_an_aware_issue_time_to_utc() -> None:
    moscow = timezone(timedelta(hours=3))
    permit = _permit(datetime(2026, 7, 12, 13, 0, tzinfo=moscow))

    assert permit["issued_at"] == "2026-07-12T10:00:00Z"
    assert permit["expires_at"] == "2026-07-12T10:10:00Z"
    assert permit["interlock_check"]["checked_at"] == permit["issued_at"]
    assert _permit(datetime(2026, 7, 12, 10, 0, tzinfo=UTC))["issued_at"] == permit["issued_at"]
