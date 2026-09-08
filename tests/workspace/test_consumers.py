"""Exercise the public boundary between contract producers and their consumer."""

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from robotics_acceptance_harness.cli import main
from robotics_acceptance_harness.documents import BundleValidationError, load_bundle
from robotics_runtime_contracts import load_mapping, validate_document

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "packages/contracts/consumer-examples/minimal-simulation"
HARNESS = ROOT / "packages/harness/tests/fixtures"
CONTRACT_DOCUMENTS = sorted(EXAMPLES.glob("*.yaml"))
HARNESS_DOCUMENTS = sorted(
    path for path in HARNESS.rglob("*") if path.suffix in {".json", ".yaml", ".yml"}
)
DOCUMENTS = CONTRACT_DOCUMENTS + HARNESS_DOCUMENTS


def test_consumer_inventory_contains_both_packages() -> None:
    assert len(CONTRACT_DOCUMENTS) >= 6
    assert len(HARNESS_DOCUMENTS) >= 6


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda path: str(path.relative_to(ROOT)))
def test_consumer_document_uses_current_public_contracts(path: Path) -> None:
    validate_document(load_mapping(path))


def test_harness_explains_contracts_consumer_example(capsys: pytest.CaptureFixture[str]) -> None:
    status = main(
        [
            "explain",
            "--scenario",
            str(EXAMPLES / "scenario.yaml"),
            "--runtime",
            str(EXAMPLES / "runtime-manifest.yaml"),
        ]
    )
    output = json.loads(capsys.readouterr().out)
    assert status == 0
    assert output["policy"] == "accepted-simulation"
    assert output["unevaluated"] == []


def test_harness_physical_fixture_keeps_cross_document_links_valid() -> None:
    physical = HARNESS / "physical"
    bundle = load_bundle(
        physical / "hil-scenario.yaml",
        runtime_path=physical / "hil-runtime.json",
        permit_path=physical / "hil-permit.json",
        verification_path=physical / "hil-verification.json",
        now=datetime(2026, 7, 12, 10, 0, tzinfo=UTC),
    )
    assert bundle.permit is not None
    assert bundle.verification is not None


def test_cross_package_gate_rejects_individually_valid_but_mismatched_documents(
    tmp_path: Path,
) -> None:
    runtime = deepcopy(load_mapping(EXAMPLES / "runtime-manifest.yaml"))
    runtime["execution"]["time_mode"] = "simulation_stepped"
    validate_document(runtime)
    path = tmp_path / "runtime.json"
    path.write_text(json.dumps(runtime), encoding="utf-8")
    with pytest.raises(BundleValidationError) as caught:
        load_bundle(EXAMPLES / "scenario.yaml", runtime_path=path)
    assert caught.value.json_path == "$.runtime.execution.time_mode"
