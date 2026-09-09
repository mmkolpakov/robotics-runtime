"""Validate the pinned infra consumer using this workspace's public contracts."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from robotics_runtime_contracts import load_mapping, validate_document
from robotics_runtime_contracts.qualification import inspect_qualification_artifacts


@pytest.fixture(scope="module")
def infra() -> Path:
    location = os.environ.get("INFRA_CONSUMER_ROOT")
    revision = os.environ.get("INFRA_CONSUMER_REVISION")
    if not location or not revision:
        pytest.fail("set INFRA_CONSUMER_ROOT and INFRA_CONSUMER_REVISION to the pinned checkout")
    root = Path(location).resolve()
    observed = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    assert observed == revision, "consumer checkout does not match the requested immutable revision"
    return root


def specifications(fixtures: Path, case: str, *, substitute_runtime: bool = False) -> list[str]:
    inventory = load_mapping(fixtures / f"{case}-artifacts.json")["artifacts"]
    assert isinstance(inventory, list) and inventory, "qualification inventory is empty"
    result: list[str] = []
    for entry in inventory:
        assert isinstance(entry, dict)
        name = entry["file"]
        if substitute_runtime and entry["kind"] == "runtime_manifest":
            name = "acceptance-run.json"
        path = (fixtures / name).resolve()
        assert path.is_relative_to(fixtures.resolve()), "artifact is outside the fixture directory"
        result.append(f"{entry['kind']}:{entry['subject_name']}={path}")
    return result


@pytest.mark.parametrize("case", ["single", "transport"])
def test_complete_infra_qualification_bundle(infra: Path, case: str) -> None:
    fixtures = infra / "test/qualification/fixtures"
    report = inspect_qualification_artifacts(specifications(fixtures, case))
    assert not report.diagnostics, [item.as_dict() for item in report.diagnostics]
    assert not report.blocked_checks, report.blocked_checks


def test_infra_inventory_cannot_replace_runtime_with_another_valid_role(infra: Path) -> None:
    fixtures = infra / "test/qualification/fixtures"
    validate_document(load_mapping(fixtures / "acceptance-run.json"), schema="acceptance-run.v1")
    report = inspect_qualification_artifacts(
        specifications(fixtures, "single", substitute_runtime=True)
    )
    assert report.diagnostics, "a run context must not be accepted as a runtime manifest"
    assert any(
        diagnostic["check"] == "artifact.load"
        and diagnostic["error_id"] == "qualification.invalid"
        and "unsupported runtime_manifest schema_version 'acceptance-run.v1'"
        in diagnostic["message"]
        for diagnostic in (item.as_dict() for item in report.diagnostics)
    )
    assert report.blocked_checks, "dependent checks must not consume an invalid runtime"


@pytest.mark.parametrize(
    ("relative", "schema"),
    [
        ("test/acceptance/stepped-smoke.yaml", "acceptance-scenario.v1"),
        ("test/zenoh/scenario.yaml", "acceptance-scenario.v1"),
        ("test/accelerators/sensor-provider-scenario.yaml", "acceptance-scenario.v1"),
        ("test/physical/hil-runtime.input.json", "runtime-manifest.v1"),
    ],
)
def test_infra_entrypoint_document(infra: Path, relative: str, schema: str) -> None:
    validate_document(load_mapping(infra / relative), schema=schema)
