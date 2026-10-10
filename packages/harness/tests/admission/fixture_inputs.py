"""Shared public-writer inputs for the two explicit author fixture profiles."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from robotics_runtime_contracts.writers import create_artifact_receipt, write_document

from robotics_acceptance_harness.evaluator_trust import AuthenticatedWheel, GitHubWheelPolicy


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def bound_inputs(
    authenticated: AuthenticatedWheel, bundle_raw: bytes, destination: Path
) -> dict[str, Any]:
    if sha256(bundle_raw).hexdigest() != authenticated.bundle_sha256:
        raise ValueError("bundle changed between capture and actual verification")
    policy = authenticated.policy
    github = isinstance(policy, GitHubWheelPolicy)
    if isinstance(policy, GitHubWheelPolicy):
        producer = {"identity": policy.certificate_identity, "implementation": "actions/attest"}
        verifier = {"identity": "official-github-cli", "implementation": "gh", "version": "2.102.0"}
    else:
        producer = {
            "identity": f"key-sha256:{policy.public_key_sha256}",
            "implementation": "cosign-key-blob-attestation",
        }
        verifier = {
            "identity": f"key-sha256:{policy.public_key_sha256}",
            "implementation": "cosign",
            "version": "v3.1.3+dirty",
        }
    # Extract only the exact DSSE bytes the stock verifier just authenticated.
    statement_raw = base64.b64decode(
        json.loads(bundle_raw)["dsseEnvelope"]["payload"], validate=True
    )
    receipts = destination / "receipts"
    receipts.mkdir(exist_ok=True)
    statement = receipts / "statement.json"
    statement.write_bytes(statement_raw)
    expectations = write_json(receipts / "publisher.json", asdict(policy))
    report = receipts / "verified-report.txt"
    report.write_bytes(authenticated.verification_report)
    artifact = {
        "uri": f"file:///opt/admission/wheels/{authenticated.filename}",
        "sha256": authenticated.sha256,
        "size_bytes": len(authenticated.wheel_bytes),
        "media_type": "application/vnd.python.wheel",
        "immutable_revision": f"sha256:{authenticated.sha256}",
    }
    verified_at = datetime.now(UTC).isoformat()
    verification = receipts / "verification.json"
    write_document(
        {
            "schema_version": "artifact-verification.v1",
            "verification_id": "author-wheel-ci-verification",
            "artifact": artifact,
            "statement_sha256": digest(statement),
            "producer_identity": producer["identity"],
            "producer_implementation": producer["implementation"],
            "trust_policy_sha256": digest(expectations),
            "verification_evidence_sha256": digest(report),
            "verifier": verifier,
            "verified_at": verified_at,
            "status": "passed",
        },
        verification,
        schema="artifact-verification.v1",
    )
    receipt = receipts / "receipt.json"
    source = destination / "wheels" / authenticated.filename
    if source.read_bytes() != authenticated.wheel_bytes:
        raise ValueError("fixture installer input differs from authenticated captured wheel")
    write_document(
        create_artifact_receipt(
            {"receipt_id": "author-wheel-ci-receipt", "created_at": verified_at},
            source,
            verification,
            [statement, expectations, report],
        ),
        receipt,
        schema="artifact-receipt.v1",
    )
    binding = write_json(
        destination / "binding.json",
        {
            "namespace": "org.example.evidence-bytes",
            "entry_point": "evidence_byte_check:evaluate",
            "distribution": "example-evidence-byte-check",
            "version": "0.1.0",
            "artifact_sha256": authenticated.sha256,
            "receipt_sha256": digest(receipt),
        },
    )
    archive = destination / "archive"
    producer_path = (
        Path(__file__).parents[3] / "contracts/consumer-examples/minimal-native-archive/producer.py"
    )
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment["PATH"]
    completed = subprocess.run(
        [
            sys.executable,
            str(producer_path),
            "--output",
            str(archive),
            "--evaluator-binding",
            str(binding),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
        timeout=60,
    )
    write_json(destination / "inputs.json", json.loads(completed.stdout))
    return {
        "assertion_id": "org.example.evidence-bytes.nonempty",
        "raw_size_bytes": (archive / "native-state.json").stat().st_size,
        "raw_sha256": digest(archive / "native-state.json"),
        "wheel_sha256": authenticated.sha256,
        "bundle_sha256": authenticated.bundle_sha256,
        "publisher_kind": "github" if github else "cosign_key_no_tlog",
        "scope": "synthetic native input records; byte-access and captured offset method only",
        "archive_assessment": _archive_assessment_inputs(destination, binding),
    }


def _archive_assessment_inputs(destination: Path, binding: Path) -> dict[str, Any]:
    trial = destination / "archive" / "archived-trial"
    producer = (
        Path(__file__).parents[3] / "contracts/consumer-examples/minimal-native-archive/producer.py"
    )
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment["PATH"]
    recorded = subprocess.run(
        [sys.executable, str(producer), "--output", str(trial), "--error", "7"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
        timeout=60,
    )
    original_inputs = json.loads(recorded.stdout)
    original_output = trial / "original-assessment"
    arguments = ["robotics-acceptance", "evaluate"]
    for name, value in original_inputs.items():
        arguments.extend(("--" + name.replace("_", "-"), str(value)))
    arguments.extend(("--output", str(original_output)))
    original = subprocess.run(
        arguments,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=90,
    )
    if original.returncode != 1:
        raise ValueError(
            "uncalibrated error=7 trial must produce the actual failed original result"
        )
    baseline = original_output / "acceptance-result.json"
    if json.loads(baseline.read_bytes())["status"] != "failed":
        raise ValueError("fixture has no failed original outcome")
    method_root = destination / "archive" / "assessment-inputs"
    method_root.mkdir()
    scenario = json.loads(Path(original_inputs["scenario"]).read_bytes())
    controls = {
        "metric_definitions": [],
        "assertions": [],
        "evaluator_requirements": [json.loads(binding.read_bytes())],
        "evidence_policy": scenario["evidence_policy"],
    }
    paths = {}
    for name, offset in (("applied", 7), ("wrong-offset", 6), ("invalid-offset", "invalid")):
        calibration = write_json(method_root / f"{name}-offset.json", {"offset": offset})
        reference = {
            "uri": calibration.as_uri(),
            "sha256": digest(calibration),
            "size_bytes": calibration.stat().st_size,
            "media_type": "application/json",
        }
        path = write_json(
            method_root / f"{name}-controls.json",
            {
                **controls,
                "calibration": {"state": "selected", "artifacts": [reference]},
            },
        )
        paths[name] = str(path)
    path = write_json(
        method_root / "unobserved-controls.json",
        {
            **controls,
            "calibration": {
                "state": "unobserved",
                "reason": "no selected offset was captured for this assessment",
            },
        },
    )
    paths["unobserved"] = str(path)
    inputs = {name: value for name, value in original_inputs.items() if name != "otel_metrics"}
    inputs["original_result"] = str(baseline)
    return {
        "inputs": inputs,
        "controls": paths,
        "original_result_sha256": digest(baseline),
        "raw_sha256": digest(trial / "native-state.json"),
        "assertion_id": "org.example.evidence-bytes.calibrated-error",
        "original_error": 7,
        "original_status": "failed",
    }
