"""Authenticate the author artifact before ordinary pip sees its captured copy."""

import json
from pathlib import Path

from robotics_acceptance_harness.evaluator_trust import (
    CosignKeyVerifierProfile,
    CosignKeyWheelPolicy,
    GitHubVerifierProfile,
    GitHubWheelPolicy,
    authenticate_wheel,
    authenticate_wheel_with_cosign_key,
    validate_evaluator_wheel,
)

data = json.loads(Path("/opt/admission/profile.json").read_bytes())
verifier = dict(data["verifier"])
kind = verifier.pop("kind")
verifier["executable"] = Path(verifier["executable"])
verifier["trusted_root"] = Path(verifier["trusted_root"])
binding = data["evaluators"][0]
if kind == "github":
    wheel = authenticate_wheel(
        binding["wheel"],
        binding["bundle"],
        profile=GitHubVerifierProfile(**verifier),
        policy=GitHubWheelPolicy(**binding["publisher"]),
    )
elif kind == "cosign_key_no_tlog":
    verifier["public_key"] = Path(verifier["public_key"])
    wheel = authenticate_wheel_with_cosign_key(
        binding["wheel"],
        binding["bundle"],
        profile=CosignKeyVerifierProfile(**verifier),
        policy=CosignKeyWheelPolicy(**binding["publisher"]),
    )
else:
    raise ValueError("fixture requires one explicit admitted verifier kind")
validate_evaluator_wheel(wheel)
captured = Path("/opt/captured")
captured.mkdir()
(captured / wheel.filename).write_bytes(wheel.wheel_bytes)
