"""Authenticate the author artifact before ordinary pip sees its captured copy."""

import json
from pathlib import Path

from robotics_acceptance_harness.evaluator_trust import (
    GitHubVerifierProfile,
    GitHubWheelPolicy,
    authenticate_wheel,
    validate_evaluator_wheel,
)

data = json.loads(Path("/opt/admission/profile.json").read_bytes())
verifier = data["verifier"]
verifier["executable"] = Path(verifier["executable"])
verifier["trusted_root"] = Path(verifier["trusted_root"])
binding = data["evaluators"][0]
wheel = authenticate_wheel(
    binding["wheel"],
    binding["bundle"],
    profile=GitHubVerifierProfile(**verifier),
    policy=GitHubWheelPolicy(**binding["publisher"]),
)
validate_evaluator_wheel(wheel)
captured = Path("/opt/captured")
captured.mkdir()
(captured / wheel.filename).write_bytes(wheel.wheel_bytes)
