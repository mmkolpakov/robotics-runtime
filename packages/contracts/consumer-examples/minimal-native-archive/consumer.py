"""Run the native example through the installed public document CLIs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def invoke(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, check=True, capture_output=True, text=True, timeout=60)


def qualify(archive: Path, assessment: Path) -> Path:
    specifications = [
        f"scenario:scenario.json={archive / 'scenario.json'}",
        f"acceptance_run:acceptance-run.json={archive / 'run.json'}",
        f"runtime_manifest:runtime-manifests/primary.json={archive / 'runtime.json'}",
        f"acceptance_observation:observations/primary.json={archive / 'observation.json'}",
        f"evidence_index:evidence-indexes/primary.json={archive / 'evidence-index.json'}",
        f"domain_result:results/primary.json={assessment / 'acceptance-result.json'}",
        "acceptance_aggregate:acceptance-aggregate.json="
        f"{assessment / 'acceptance-aggregate.json'}",
        f"junit:reports/junit.xml={assessment / 'junit.xml'}",
        f"other_evidence:evaluation/method.json={assessment / 'evaluation-method.json'}",
        f"other_evidence:evaluation/environment.json={assessment / 'evaluation-environment.json'}",
    ]
    specifications.extend(
        f"other_evidence:evidence/{name}={archive / name}"
        for name in (
            "configuration.json",
            "native-type.json",
            "model.json",
            "native-state.json",
            "metrics.jsonl",
        )
    )
    arguments = ["robotics-contracts", "validate-qualification"]
    arguments.extend(
        value for specification in specifications for value in ("--artifact", specification)
    )
    invoke(arguments)
    statement = assessment / "qualification-bundle.json"
    invoke(
        [
            "robotics-contracts",
            "qualification",
            "statement",
            *arguments[2:],
            "--output",
            str(statement),
        ]
    )
    invoke([*arguments, "--statement", str(statement)])
    return statement


def run(destination: Path, simulation: bool) -> dict[str, Any]:
    destination = destination.expanduser().resolve()
    archive = destination / "archive"
    assessment = destination / "assessment"
    producer = [
        sys.executable,
        str(Path(__file__).with_name("producer.py")),
        "--output",
        str(archive),
    ]
    if simulation:
        producer.append("--simulation")
    inputs = json.loads(invoke(producer).stdout)
    originals = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in archive.iterdir()
        if path.is_file()
    }
    validate = [
        "robotics-contracts",
        "validate",
        *(
            str(archive / name)
            for name in (
                "scenario.json",
                "runtime.json",
                "run.json",
                "observation.json",
                "evidence-index.json",
            )
        ),
    ]
    invoke(validate)
    arguments = ["robotics-acceptance", "evaluate"]
    arguments.extend(
        value
        for name, item in inputs.items()
        for value in ("--" + name.replace("_", "-"), str(item))
    )
    report = json.loads(invoke([*arguments, "--output", str(assessment)]).stdout)
    aggregate = assessment / "acceptance-aggregate.json"
    invoke(
        [
            "robotics-acceptance",
            "aggregate",
            "--scenario",
            str(archive / "scenario.json"),
            "--run-context",
            str(archive / "run.json"),
            "--result",
            str(assessment / "acceptance-result.json"),
            "--output",
            str(aggregate),
        ]
    )
    statement = qualify(archive, assessment)
    invoke(
        [
            "robotics-contracts",
            "validate",
            str(assessment / "acceptance-result.json"),
            str(aggregate),
        ]
    )
    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
    if after != originals:
        raise RuntimeError("assessment changed an original archive input")
    return {
        "status": report["status"],
        "run_id": inputs["run_id"],
        "archive": str(archive),
        "result": report["result"],
        "junit": report["junit"],
        "aggregate": str(aggregate),
        "qualification_bundle": str(statement),
        "original_inputs_unchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--simulation", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.output, arguments.simulation), sort_keys=True))


if __name__ == "__main__":
    main()
