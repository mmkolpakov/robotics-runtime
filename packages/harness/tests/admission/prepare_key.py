"""Prepare an explicitly local no-log publisher; its private key never enters artifacts."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.admission.fixture_inputs import bound_inputs, digest, write_json

from robotics_acceptance_harness.evaluator_trust import (
    CosignKeyVerifierProfile,
    CosignKeyWheelPolicy,
    authenticate_wheel_with_cosign_key,
    read_once,
    validate_evaluator_wheel,
)

COSIGN_SHA256 = "9deba5b08d25e35d107abd491f8f6c774a880d986ecfddc6761c1f9593bdaa81"
COSIGN_VERSION = "v3.1.3+dirty"
PREDICATE = "urn:org.example:evaluator-byte-method:v1"


def command(tool: Path, root: Path, *arguments: str) -> None:
    environment = {
        "HOME": str(root),
        "XDG_CONFIG_HOME": str(root / "config"),
        "COSIGN_PASSWORD": "",
        "LC_ALL": "C.UTF-8",
    }
    result = subprocess.run(
        [str(tool), *arguments],
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode:
        raise ValueError("stock temporary publisher operation refused")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("wheel", "cosign", "destination"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    destination = args.destination.resolve()
    auxiliary = destination / "auxiliary"
    auxiliary.mkdir(parents=True, exist_ok=True)
    tool = args.cosign.resolve()
    if digest(tool) != COSIGN_SHA256:
        raise ValueError("Cosign differs from approved executable SHA-256")
    with TemporaryDirectory(prefix="local-evaluator-publisher-") as private:
        root = Path(private)
        command(tool, root, "signing-config", "create", "--out", "signing.json")
        command(tool, root, "trusted-root", "create", "--out", "roots.json")
        command(tool, root, "generate-key-pair", "--output-key-prefix", "publisher")
        command(tool, root, "generate-key-pair", "--output-key-prefix", "other")
        predicate = write_json(
            root / "predicate.json",
            {
                "method": "synthetic input byte count",
                "scope": "local signature; no build-origin claim",
            },
        )
        command(
            tool,
            root,
            "attest-blob",
            "--yes",
            "--key",
            "publisher.key",
            "--signing-config",
            "signing.json",
            "--trusted-root",
            "roots.json",
            "--type",
            PREDICATE,
            "--predicate",
            str(predicate),
            "--bundle",
            "wheel.sigstore.json",
            str(args.wheel.resolve()),
        )
        # Copy public verification material only; private files stay in this temporary directory.
        key, other = auxiliary / "publisher.pub", auxiliary / "other.pub"
        key.write_bytes((root / "publisher.pub").read_bytes())
        other.write_bytes((root / "other.pub").read_bytes())
        trusted_root = destination / "trusted-root.jsonl"
        trusted_root.write_bytes((root / "roots.json").read_bytes())
        bundle = destination / "bundle.json"
        bundle.write_bytes((root / "wheel.sigstore.json").read_bytes())
    profile = CosignKeyVerifierProfile(
        tool, COSIGN_SHA256, COSIGN_VERSION, key, digest(key), trusted_root, digest(trusted_root)
    )
    policy = CosignKeyWheelPolicy(digest(args.wheel), PREDICATE, digest(key), "key_only_no_tlog")
    bundle_raw = read_once(bundle, 16 * 1024 * 1024)
    authenticated = authenticate_wheel_with_cosign_key(
        args.wheel, bundle, profile=profile, policy=policy
    )
    validate_evaluator_wheel(authenticated)
    operator = write_json(
        destination / "profile.json",
        {
            "profile_version": 1,
            "verifier": {
                "kind": "cosign_key_no_tlog",
                "executable": "/opt/admission/verifier",
                "executable_sha256": COSIGN_SHA256,
                "version": COSIGN_VERSION,
                "public_key": "/opt/admission/auxiliary/publisher.pub",
                "public_key_sha256": digest(key),
                "trusted_root": "/opt/admission/trusted-root.jsonl",
                "trusted_root_sha256": digest(trusted_root),
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
            "public_key_sha256": digest(key),
            "other_key_sha256": digest(other),
            "oidc_build_origin_timestamp_claimed": False,
        },
    )


if __name__ == "__main__":
    main()
