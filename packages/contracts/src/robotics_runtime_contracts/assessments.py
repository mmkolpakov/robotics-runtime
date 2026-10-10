"""Validation for captured native assessment controls, separate from execution inputs."""

from __future__ import annotations

from collections.abc import Mapping
from functools import cache
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import best_match

from robotics_runtime_contracts import ContractValidationError, schema_registry
from robotics_runtime_contracts.semantics import _validate_native_assessment_controls
from robotics_runtime_contracts.serialization import ensure_finite_numbers


@cache
def _controls_validator() -> Draft202012Validator:
    return Draft202012Validator(
        {
            "$ref": (
                "urn:robotics-runtime-contracts:v2:internal:native-execution"
                "#/$defs/assessmentControls"
            )
        },
        format_checker=FormatChecker(),
        registry=schema_registry(),
    )


def validate_assessment_controls(controls: Mapping[str, Any]) -> None:
    """Validate the controls payload using the existing offline schema registry.

    Absence of calibration in an older payload makes no calibration declaration.
    The archive input loader requires an explicit selection for a new assessment.
    """
    ensure_finite_numbers(controls)
    error = best_match(_controls_validator().iter_errors(controls))
    if error is not None:
        raise ContractValidationError("native-execution.v2", error)
    _validate_native_assessment_controls("acceptance-result.v2", controls)
