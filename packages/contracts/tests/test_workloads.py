from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from robotics_runtime_contracts import (
    ContractValidationError,
    RobotDescriptionBindingError,
    validate_document,
    validate_robot_description_binding,
)
from tests.support import load_fixture

FIXTURES = Path(__file__).parent / "fixtures" / "qualification"


@pytest.mark.parametrize(
    "runtime_name", ["transport/control-runtime.json", "inference/runtime.json"]
)
def test_optional_robot_description_on_both_workload_kinds(runtime_name: str) -> None:
    runtime = load_fixture(FIXTURES / runtime_name)
    validate_document(runtime)
    runtime["workload"]["robot_description"] = {"sha256": "a" * 64}
    validate_document(runtime)


@pytest.mark.parametrize("binding", [{}, {"sha256": "short"}, {"sha256": "A" * 64}, {"sha256": 1}])
def test_runtime_rejects_malformed_description_binding(binding: dict[str, Any]) -> None:
    runtime = load_fixture(FIXTURES / "transport/control-runtime.json")
    runtime["workload"]["robot_description"] = binding
    with pytest.raises(ContractValidationError):
        validate_document(runtime)


@pytest.mark.parametrize("observed", [None, "b" * 64, "a" * 64])
def test_scenario_pin_must_be_observed(observed: str | None) -> None:
    scenario = load_fixture(FIXTURES / "transport/scenario.json")
    runtime = load_fixture(FIXTURES / "transport/control-runtime.json")
    scenario["workload"] = {"robot_description_sha256": "a" * 64}
    if observed is not None:
        runtime["workload"]["robot_description"] = {"sha256": observed}
    validate_document(scenario)
    validate_document(runtime)
    if observed == "a" * 64:
        validate_robot_description_binding(scenario, runtime)
    else:
        with pytest.raises(RobotDescriptionBindingError) as caught:
            validate_robot_description_binding(scenario, runtime)
        assert caught.value.error_id == "workload.robot_description_mismatch"
        assert caught.value.json_path == "$.workload.robot_description.sha256"


def test_unpinned_scenario_accepts_optional_runtime_binding() -> None:
    scenario = load_fixture(FIXTURES / "transport/scenario.json")
    runtime = load_fixture(FIXTURES / "transport/control-runtime.json")
    validate_robot_description_binding(scenario, runtime)
    runtime["workload"]["robot_description"] = {"sha256": "a" * 64}
    validate_robot_description_binding(scenario, runtime)
