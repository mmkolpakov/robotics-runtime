"""Cross-document bindings for optional workload artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from robotics_runtime_contracts.errors import ContractError


class RobotDescriptionBindingError(ContractError):
    """The observed description does not satisfy the scenario's pinned bytes."""

    error_id = "workload.robot_description_mismatch"


def validate_robot_description_binding(
    scenario: Mapping[str, Any], runtime: Mapping[str, Any]
) -> None:
    """Compare optional bindings in schema-validated scenario/runtime documents."""

    expected = scenario.get("workload", {}).get("robot_description_sha256")
    if expected is None:
        return
    observed = runtime["workload"].get("robot_description", {}).get("sha256")
    if observed != expected:
        raise RobotDescriptionBindingError(
            f"robot description digest does not match: "
            f"expected {expected!r}, received {observed!r}",
            json_path="$.workload.robot_description.sha256",
        )
