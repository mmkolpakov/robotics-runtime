"""Prepare synthetic native input and a real publisher-bound evaluator CI witness."""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from robotics_runtime_contracts.writers import create_artifact_receipt, write_document

from robotics_acceptance_harness.evaluator_trust import (
    GitHubVerifierProfile,
    GitHubWheelPolicy,
    authenticate_wheel,
    read_once,
    validate_evaluator_wheel,
)

GH_SHA256 = "7469124f706944133d6a169691dd1c6c3511b12e85878d255e044e2948df4c9b"
ROOT_SHA256 = "65ca537f6ed8a47fd0e560c421baa1f6c1efb8b25fc200d8c5c02c0e92eb2b9c"


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--gh", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--identity", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    policy = GitHubWheelPolicy(
        args.repository,
        args.identity,
        digest(args.wheel),
        source_ref=args.ref,
        source_digest=args.commit,
        signer_digest=args.commit,
    )
    profile = GitHubVerifierProfile(args.gh, GH_SHA256, "2.102.0", args.root, ROOT_SHA256)
    bundle_raw = read_once(args.bundle, 16 * 1024 * 1024)
    authenticated = authenticate_wheel(args.wheel, args.bundle, policy=policy, profile=profile)
    validate_evaluator_wheel(authenticated)
    if sha256(bundle_raw).hexdigest() != authenticated.bundle_sha256:
        raise ValueError("bundle changed between capture and authentication")
    # Only extract provenance after the official verifier authenticated these
    # exact bundle/subject bytes. These JSON audit documents never issue admission.
    bundle = json.loads(bundle_raw)
    statement_raw = base64.b64decode(bundle["dsseEnvelope"]["payload"], validate=True)
    receipts = destination / "receipts"
    receipts.mkdir(exist_ok=True)
    statement = receipts / "statement.json"
    statement.write_bytes(statement_raw)
    expectations = write_json(receipts / "publisher.json", asdict(policy))
    report = receipts / "verified-report.json"
    report.write_bytes(authenticated.verification_report)
    artifact = {
        "uri": f"file:///opt/admission/wheels/{args.wheel.name}",
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
            "producer_identity": policy.certificate_identity,
            "producer_implementation": "actions/attest",
            "trust_policy_sha256": digest(expectations),
            "verification_evidence_sha256": digest(report),
            "verifier": {
                "identity": "official-github-cli",
                "implementation": "gh",
                "version": "2.102.0",
            },
            "verified_at": verified_at,
            "status": "passed",
        },
        verification,
        schema="artifact-verification.v1",
    )
    receipt = receipts / "receipt.json"
    write_document(
        create_artifact_receipt(
            {"receipt_id": "author-wheel-ci-receipt", "created_at": verified_at},
            args.wheel,
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
    operator = write_json(
        destination / "profile.json",
        {
            "profile_version": 1,
            "verifier": {
                "executable": "/opt/admission/gh",
                "executable_sha256": GH_SHA256,
                "version": "2.102.0",
                "trusted_root": "/opt/admission/trusted-root.jsonl",
                "trusted_root_sha256": ROOT_SHA256,
            },
            "evaluators": [
                {
                    "namespace": "org.example.evidence-bytes",
                    "wheel": f"/opt/admission/wheels/{args.wheel.name}",
                    "bundle": "/opt/admission/bundle.json",
                    "publisher": asdict(policy),
                }
            ],
        },
    )
    operator.chmod(0o444)
    archive = destination / "archive"
    producer = (
        Path(__file__).parents[3] / "contracts/consumer-examples/minimal-native-archive/producer.py"
    )
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment["PATH"]
    completed = subprocess.run(
        [
            sys.executable,
            str(producer),
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
    inputs = json.loads(completed.stdout)
    write_json(destination / "inputs.json", inputs)
    write_json(
        destination / "expectations.json",
        {
            "assertion_id": "org.example.evidence-bytes.nonempty",
            "raw_size_bytes": (archive / "native-state.json").stat().st_size,
            "raw_sha256": digest(archive / "native-state.json"),
            "wheel_sha256": authenticated.sha256,
            "bundle_sha256": authenticated.bundle_sha256,
            "source_digest": args.commit,
            "source_ref": args.ref,
            "certificate_identity": args.identity,
            "scope": "synthetic native input records; byte-access method only",
        },
    )


if __name__ == "__main__":
    main()
