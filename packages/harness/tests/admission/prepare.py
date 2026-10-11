"""Prepare the actual GitHub-attested author fixture without ambient verifier credentials."""

import argparse
from dataclasses import asdict
from pathlib import Path

from tests.admission.fixture_inputs import bound_inputs, digest, write_json

from robotics_acceptance_harness.evaluator_trust import (
    GitHubVerifierProfile,
    GitHubWheelPolicy,
    authenticate_wheel,
    read_once,
    validate_evaluator_wheel,
)

GH_SHA256 = "7469124f706944133d6a169691dd1c6c3511b12e85878d255e044e2948df4c9b"
ROOT_SHA256 = "65ca537f6ed8a47fd0e560c421baa1f6c1efb8b25fc200d8c5c02c0e92eb2b9c"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("wheel", "bundle", "gh", "root", "destination"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("repository", "identity", "ref", "commit"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "auxiliary").mkdir(exist_ok=True)
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
    operator = write_json(
        destination / "profile.json",
        {
            "profile_version": 1,
            "verifier": {
                "kind": "github",
                "executable": "/opt/admission/verifier",
                "executable_sha256": GH_SHA256,
                "version": "2.102.0",
                "trusted_root": "/opt/admission/trusted-root.jsonl",
                "trusted_root_sha256": ROOT_SHA256,
            },
            "evaluators": [
                {
                    "namespace": "org.example.evidence-bytes",
                    "wheel": f"/opt/admission/wheels/{authenticated.filename}",
                    "bundle": "/opt/admission/bundle.json",
                    "publisher": asdict(policy),
                }
            ],
        },
    )
    operator.chmod(0o444)
    write_json(
        destination / "expectations.json",
        {
            **bound_inputs(authenticated, bundle_raw, destination),
            "source_digest": args.commit,
            "source_ref": args.ref,
            "certificate_identity": args.identity,
        },
    )


if __name__ == "__main__":
    main()
