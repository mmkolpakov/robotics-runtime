from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from robotics_runtime_contracts import ContractError, load_mapping, validate_role
from robotics_runtime_contracts.cli import main
from robotics_runtime_contracts.writers import create_artifact_receipt


@pytest.fixture
def receipt_inputs(tmp_path: Path) -> dict[str, Any]:
    source = tmp_path / "recording.mcap"
    source.write_bytes(b"source bytes: this fixture does not claim MCAP validity")
    dependencies = []
    for name in ("statement", "trust-policy", "verification-evidence"):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps({"fixture": name}), encoding="utf-8")
        dependencies.append(path)
    digests = [sha256(path.read_bytes()).hexdigest() for path in dependencies]
    verification = {
        "schema_version": "artifact-verification.v1",
        "verification_id": "fixture.verification",
        "statement_sha256": digests[0],
        "artifact": {
            "uri": "s3://fixture-bucket/recording.mcap",
            "sha256": sha256(source.read_bytes()).hexdigest(),
            "size_bytes": source.stat().st_size,
            "media_type": "application/mcap",
            "immutable_revision": "fixture-version-1",
        },
        "producer_identity": "fixture-producer",
        "producer_implementation": "fixture-uploader",
        "trust_policy_sha256": digests[1],
        "verification_evidence_sha256": digests[2],
        "verifier": {"identity": "fixture-verifier", "implementation": "fixture", "version": "1"},
        "verified_at": "2026-09-08T10:00:00Z",
        "status": "passed",
    }
    path = tmp_path / "verification.json"
    # Whitespace is deliberate: the receipt must hash these bytes, not a reserialization.
    path.write_text(json.dumps(verification, indent=3) + "\n", encoding="utf-8")
    template = {
        "receipt_id": "receipt.fixture",
        "run_id": "run-00000000-0000-4000-8000-000000000001",
        "created_at": "2026-09-08T10:00:01Z",
    }
    return {
        "source": source,
        "verification": path,
        "dependencies": dependencies,
        "template": template,
    }


def produce(inputs: dict[str, Any]) -> dict[str, Any]:
    return create_artifact_receipt(
        inputs["template"], inputs["source"], inputs["verification"], inputs["dependencies"]
    )


def test_receipt_binds_exact_verification_source_and_dependency_bytes(
    receipt_inputs: dict[str, Any],
) -> None:
    template = deepcopy(receipt_inputs["template"])
    result = produce(receipt_inputs)
    validate_role(result, "artifact_receipt")
    assert (
        result["verification_sha256"]
        == sha256(receipt_inputs["verification"].read_bytes()).hexdigest()
    )
    assert result["artifact"] == load_mapping(receipt_inputs["verification"])["artifact"]
    assert result["producer"] == {
        "identity": "fixture-producer",
        "implementation": "fixture-uploader",
    }
    assert receipt_inputs["template"] == template


@pytest.mark.parametrize(
    "field", ["artifact", "producer", "statement_sha256", "verification_sha256"]
)
def test_receipt_rejects_supplied_fields_that_disagree_with_verification(
    receipt_inputs: dict[str, Any], field: str
) -> None:
    receipt_inputs["template"][field] = "different"
    with pytest.raises(ContractError, match=f"supplied {field} does not match"):
        produce(receipt_inputs)


def test_receipt_rejects_changed_source_bytes(
    receipt_inputs: dict[str, Any],
) -> None:
    receipt_inputs["source"].write_bytes(b"changed")
    with pytest.raises(ContractError, match="supplied sha256 does not match"):
        produce(receipt_inputs)


@pytest.mark.parametrize("operation", ["missing", "duplicate", "unreferenced", "changed"])
def test_receipt_requires_the_exact_provenance_dependency_set(
    receipt_inputs: dict[str, Any], tmp_path: Path, operation: str
) -> None:
    dependencies = receipt_inputs["dependencies"]
    if operation == "missing":
        dependencies.pop()
        reason = "dependencies are missing"
    elif operation == "duplicate":
        dependencies.append(dependencies[0])
        reason = "duplicate provenance"
    elif operation == "changed":
        dependencies[0].write_bytes(b"changed statement")
        reason = "dependencies are missing"
    else:
        extra = tmp_path / "extra.json"
        extra.write_bytes(b"unrelated")
        dependencies.append(extra)
        reason = "unreferenced provenance"
    with pytest.raises(ContractError, match=reason):
        produce(receipt_inputs)


def test_receipt_must_not_predate_external_verification(receipt_inputs: dict[str, Any]) -> None:
    receipt_inputs["template"]["created_at"] = "2026-09-08T09:59:59Z"
    with pytest.raises(ContractError, match="before its verification"):
        produce(receipt_inputs)


def test_receipt_cli_preserves_output_when_external_verification_is_not_passed(
    receipt_inputs: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    verification = load_mapping(receipt_inputs["verification"])
    verification["status"] = "failed"
    receipt_inputs["verification"].write_text(json.dumps(verification), encoding="utf-8")
    template = tmp_path / "template.json"
    template.write_text(json.dumps(receipt_inputs["template"]), encoding="utf-8")
    destination = tmp_path / "receipt.json"
    destination.write_bytes(b"previous")
    arguments = [
        "artifact-receipt",
        "create",
        "--template",
        str(template),
        "--source",
        str(receipt_inputs["source"]),
        "--verification",
        str(receipt_inputs["verification"]),
        "--output",
        str(destination),
    ]
    for path in receipt_inputs["dependencies"]:
        arguments.extend(["--dependency", str(path)])
    assert main(arguments) == 1
    assert "status" in capsys.readouterr().err
    assert destination.read_bytes() == b"previous"
    verification["status"] = "passed"
    receipt_inputs["verification"].write_text(json.dumps(verification), encoding="utf-8")
    assert main(arguments) == 0
    validate_role(load_mapping(destination), "artifact_receipt")
    arguments[arguments.index("--output") + 1] = str(receipt_inputs["source"])
    before = receipt_inputs["source"].read_bytes()
    assert main(arguments) == 1
    assert "output must not replace input" in capsys.readouterr().err
    assert receipt_inputs["source"].read_bytes() == before
