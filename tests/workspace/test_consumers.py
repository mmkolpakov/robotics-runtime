"""Exercise the public boundary between contract producers and their consumer."""

import json
import subprocess
import sys
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


PUBLISHED_CLI = ROOT / "packages/contracts/consumer-examples/published-cli"
# Declared window of the published-cli producer fixture (produce.py constants).
FIXTURE_WINDOW_START_NS = 1785067200000000000
FIXTURE_WINDOW_END_NS = 1785067201000000000


def test_published_cli_first_result_journey(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Guard the offline first-result journey the Dagu recipe drives."""
    inputs = tmp_path / "inputs"
    subprocess.run(
        [sys.executable, str(PUBLISHED_CLI / "produce.py"), "--output", str(inputs)],
        check=True,
    )
    run_id = json.loads((inputs / "acceptance-run.json").read_text())["run_id"]
    evaluate_args = [
        "evaluate",
        "--scenario",
        str(inputs / "scenario.json"),
        "--runtime",
        str(inputs / "runtime-manifest.json"),
        "--run-id",
        run_id,
        "--domain-id",
        "primary",
        "--run-context",
        str(inputs / "acceptance-run.json"),
        "--evidence-index",
        str(inputs / "evidence-index.json"),
        "--otel-metrics",
        str(inputs / "metrics.otlp.jsonl"),
        "--window-start-ns",
        str(FIXTURE_WINDOW_START_NS),
        "--window-end-ns",
        str(FIXTURE_WINDOW_END_NS),
    ]

    results = tmp_path / "results"
    status = main(
        [
            *evaluate_args,
            "--output",
            str(results),
            "--diagnostic-output",
            str(tmp_path / "diagnostic.json"),
        ]
    )
    assert status == 1
    result = json.loads((results / "acceptance-result.json").read_text())
    assert result["status"] == "incomplete"
    assert (results / "junit.xml").exists()
    capsys.readouterr()

    assert main(["why", str(results / "acceptance-result.json"), "--format", "markdown"]) == 0
    capsys.readouterr()

    metrics = inputs / "metrics.otlp.jsonl"
    metrics.write_bytes(metrics.read_bytes() + b"\n")
    rejected = tmp_path / "rejected"
    diagnostic = tmp_path / "refusal-diagnostic.json"
    status = main(
        [*evaluate_args, "--output", str(rejected), "--diagnostic-output", str(diagnostic)]
    )
    assert status == 2
    assert diagnostic.exists()
    assert not (rejected / "acceptance-result.json").exists()


def test_dagu_failure_handler_preserves_quoted_paths(tmp_path: Path) -> None:
    import yaml

    recipe = yaml.safe_load((ROOT / "examples/dagu/first-result.yaml").read_text())
    handler = recipe["handler_on"]["failure"]
    assert handler["action"] == "exec"
    assert "run" not in handler and "env" not in handler and "preconditions" not in handler
    assert handler["with"]["command"] == "${PYTHON}"
    arguments = handler["with"]["args"]
    assert arguments[0] == "-c"
    assert arguments[2:] == ["${HARNESS}", "${OUT}/results/acceptance-result.json"]

    executable = tmp_path / "harness space's double\"quote"
    executable.write_text(
        "#!" + sys.executable + "\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n"
    )
    executable.chmod(0o700)
    result = tmp_path / "result space's double\"quote.json"
    result.write_text("{}")
    completed = subprocess.run(
        [sys.executable, arguments[0], arguments[1], str(executable), str(result)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == ["why", str(result), "--format", "markdown"]
    result.unlink()
    completed = subprocess.run(
        [sys.executable, arguments[0], arguments[1], str(executable), str(result)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout == ""
