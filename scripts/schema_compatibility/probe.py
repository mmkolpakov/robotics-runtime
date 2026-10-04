"""Execute frozen JSON requests through one explicitly selected public package."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.schema_compatibility.structure import token  # noqa: E402


def run_case(
    contracts: ModuleType, documents: dict[str, Any], case: dict[str, Any]
) -> dict[str, Any]:
    """Only native ContractError is an expected refusal; infrastructure errors escape."""
    result: dict[str, Any] = {}
    before = token(documents)
    try:
        operation = case["operation"]
        if operation == "document":
            contracts.validate_document(documents[case["document"]])
        elif operation == "role":
            contracts.validate_role(
                documents[case["document"]],
                case["role"],
                extension_schemas=case.get("extension_schemas"),
            )
        elif operation == "qualification":
            qualification = importlib.import_module("robotics_runtime_contracts.qualification")
            artifacts = [
                qualification.QualificationArtifact(
                    item["kind"],
                    item["subject_name"],
                    item["sha256"],
                    item["size_bytes"],
                    documents[item["document"]] if item["document"] is not None else None,
                )
                for item in case["artifacts"]
            ]
            report = qualification.inspect_qualification_documents(artifacts)
            result["inspection"] = {
                "valid": report.valid,
                "run_id": report.run_id,
                "generated_at": report.generated_at,
                "diagnostics": [item.as_dict() for item in report.diagnostics],
                "blocked_checks": list(report.blocked_checks),
            }
            qualification.validate_qualification_documents(artifacts)
        elif operation == "workload":
            scenario, runtime = documents[case["scenario"]], documents[case["runtime"]]
            contracts.validate_document(scenario)
            contracts.validate_document(runtime)
            contracts.validate_robot_description_binding(scenario, runtime)
        elif operation == "syntax":
            serialization = importlib.import_module("robotics_runtime_contracts.serialization")
            value = contracts.loads_mapping(case["raw"], source_name=case["source_name"])
            result["value"] = value
            result["roundtrip"] = contracts.loads_mapping(serialization.dumps_yaml(value))
        else:
            raise ValueError(f"Unknown corpus operation: {operation}")
        result["status"] = "accepted"
    except Exception as error:
        errors = importlib.import_module("robotics_runtime_contracts.errors")
        if not isinstance(error, errors.ContractError):
            raise
        result.update(
            status="rejected",
            exception=type(error).__name__,
            error_id=error.error_id,
            path=error.json_path,
            message=str(error),
        )
        if hasattr(error, "diagnostics"):
            result["diagnostics"] = [item.as_dict() for item in error.diagnostics]
            result["blocked_checks"] = list(error.blocked_checks)
    if token(documents) != before:
        raise ValueError(f"Validator mutated input: {case['id']}")
    return result


def validate(source: Path, request: dict[str, Any]) -> dict[str, Any]:
    sys.path.insert(0, str(source.resolve()))
    contracts = importlib.import_module("robotics_runtime_contracts")
    origin = contracts.__file__
    if origin is None or not Path(origin).resolve().is_relative_to(source.resolve()):
        raise ValueError("Validator import escaped the selected source tree")
    documents = request["documents"]
    cases = request["cases"]
    if not cases or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Corpus cases must be nonempty and uniquely identified")
    outcomes = {}
    for case in cases:
        try:
            outcomes[case["id"]] = run_case(contracts, documents, case)
        except Exception as error:
            raise ValueError(f"{case['id']}: {type(error).__name__}: {error}") from error
    return {"origin": origin, "documents": documents, "outcomes": outcomes}


def execute(source: Path, request: dict[str, Any]) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(Path(__file__).resolve()), str(source)],
        input=json.dumps(request, allow_nan=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=60,
    )
    if result.returncode:
        from scripts.schema_compatibility.structure import ReviewRequired

        raise ReviewRequired(result.stderr.strip())
    response: dict[str, Any] = json.loads(result.stdout)
    return response


def main() -> int:
    try:
        print(json.dumps(validate(Path(sys.argv[1]), json.load(sys.stdin)), allow_nan=False))
        return 0
    except Exception as error:
        print(f"Semantic regression failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
