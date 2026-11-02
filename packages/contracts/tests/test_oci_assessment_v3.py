from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from robotics_runtime_contracts import ContractError, schema_registry
from robotics_runtime_contracts.assessments import validate_assessment_controls
from robotics_runtime_contracts.semantics import _validate_native_assessment_coverage

DIGEST = "a" * 64
OCI: dict[str, Any] = {
    "kind": "oci",
    "namespace": "org.example.check",
    "execution_subject": {
        "kind": "oci_image",
        "locator": "oci://example.invalid/evaluator@sha256:" + DIGEST,
        "digest": "sha256:" + DIGEST,
    },
    "expected_assertion_ids": ["org.example.check.first"],
}


def controls() -> dict[str, Any]:
    return {
        "schema_version": "assessment-controls.v1",
        "metric_definitions": [],
        "assertions": [],
        "evaluator_requirements": [deepcopy(OCI)],
        "evidence_policy": {
            "max_artifact_size_bytes": 1024,
            "max_archive_size_bytes": 4096,
            "max_upload_lag_sec": 0,
            "upload_mode": "local_only",
            "retention_class": "qualification",
            "remote_sink_allowed": False,
        },
        "calibration": {"state": "not_applicable", "reason": "raw data"},
    }


def test_explicit_controls_and_legacy_dispatch() -> None:
    validate_assessment_controls(controls())
    empty = controls()
    empty["evaluator_requirements"] = []
    validate_assessment_controls(empty)
    legacy = deepcopy(empty)
    legacy.pop("schema_version")
    validate_assessment_controls(legacy)
    missing_marker = controls()
    missing_marker.pop("schema_version")
    with pytest.raises(ContractError):
        validate_assessment_controls(missing_marker)
    for version in (None, "", "assessment-controls.v2", 1):
        invalid = deepcopy(empty)
        invalid["schema_version"] = version
        with pytest.raises(ContractError, match="unsupported assessment controls"):
            validate_assessment_controls(invalid)


def test_closed_oci_declaration() -> None:
    schema = "urn:robotics-runtime-contracts:v1:internal:assessment"
    validator = Draft202012Validator(
        {"$ref": schema + "#/$defs/evaluatorRequirements"},
        registry=schema_registry(),
    )
    validator.validate([OCI])
    for field, value in (
        ("kind", "other"),
        ("distribution", "fake"),
        ("expected_assertion_ids", []),
        ("expected_assertion_ids", ["org.example.check.first"] * 2),
    ):
        bad = deepcopy(OCI)
        bad[field] = value
        assert list(validator.iter_errors([bad]))
    for field, value in (("kind", "native_process"), ("digest", "sha256:wrong")):
        bad = deepcopy(OCI)
        bad["execution_subject"][field] = value
        assert list(validator.iter_errors([bad]))
    bad_controls = controls()
    bad_controls["evaluator_requirements"][0]["expected_assertion_ids"] = ["org.other.first"]
    with pytest.raises(ContractError, match="namespace"):
        validate_assessment_controls(bad_controls)


def test_oci_coverage_requires_declared_ids_and_preserves_incomplete() -> None:
    result: dict[str, Any] = {
        "schema_version": "acceptance-result.v3",
        "evaluators": [deepcopy(OCI)],
        "assertion_results": [],
        "evidence": [],
        "unevaluated": ["$.assertions.org.example.check.first"],
        "evaluation": {
            "coverage": {
                "covered_assertions": [],
                "uncovered_assertions": [
                    {"assertion_id": "org.example.check.first", "reason": "unavailable"}
                ],
            }
        },
    }
    _validate_native_assessment_coverage(result)
    bad = deepcopy(result)
    bad["evaluation"]["coverage"]["uncovered_assertions"] = []
    with pytest.raises(ContractError, match="covered or uncovered"):
        _validate_native_assessment_coverage(bad)
    bad = deepcopy(result)
    bad["evaluation"]["coverage"]["uncovered_assertions"].append(
        {"assertion_id": "org.example.check.extra", "reason": "undeclared"}
    )
    with pytest.raises(ContractError, match="undeclared"):
        _validate_native_assessment_coverage(bad)
    bad = deepcopy(result)
    bad["assertion_results"] = [
        {
            "source": "product",
            "namespace": "org.example.check",
            "assertion_id": "org.example.check.extra",
        }
    ]
    with pytest.raises(ContractError, match="not assigned"):
        _validate_native_assessment_coverage(bad)
    bad = deepcopy(result)
    del bad["evaluation"]["coverage"]
    with pytest.raises(ContractError, match="requires declared coverage"):
        _validate_native_assessment_coverage(bad)
    bad = deepcopy(result)
    bad["unevaluated"] = []
    with pytest.raises(ContractError, match="must remain unevaluated"):
        _validate_native_assessment_coverage(bad)


def test_overlapping_namespaces_do_not_share_or_steal_assertion_ids() -> None:
    child = deepcopy(OCI)
    child["namespace"] = "org.example.check.child"
    child["expected_assertion_ids"] = ["org.example.check.child.first"]
    first = deepcopy(OCI)
    first["expected_assertion_ids"] = ["org.example.check.child.first"]
    result: dict[str, Any] = {
        "schema_version": "acceptance-result.v3",
        "evaluators": [first, child],
        "assertion_results": [],
        "evidence": [],
        "unevaluated": [],
        "evaluation": {"coverage": {"covered_assertions": [], "uncovered_assertions": []}},
    }
    with pytest.raises(ContractError, match="assigned to more than one evaluator"):
        _validate_native_assessment_coverage(result)

    first["expected_assertion_ids"] = ["org.example.check.first"]
    result["assertion_results"] = [
        {
            "source": "product",
            "namespace": "org.example.check",
            "assertion_id": "org.example.check.first",
        },
        {
            "source": "product",
            "namespace": "org.example.check",
            "assertion_id": "org.example.check.child.first",
        },
    ]
    with pytest.raises(ContractError, match="not assigned"):
        _validate_native_assessment_coverage(result)


def test_builtin_rows_cannot_satisfy_oci_ownership() -> None:
    from robotics_runtime_contracts.semantics import _validate_native_assessment_controls

    method = controls()
    method["assertions"] = [{"assertion_id": "org.example.check.first"}]
    with pytest.raises(
        ContractError, match="core and OCI evaluator assertion IDs must be disjoint"
    ):
        _validate_native_assessment_controls("acceptance-result.v3", method)

    result = {
        "schema_version": "acceptance-result.v3",
        "evaluators": [deepcopy(OCI)],
        "assertion_results": [
            {"source": "core", "assertion_id": "org.example.check.first", "status": "passed"}
        ],
        "evidence": [{"sha256": DIGEST}],
        "unevaluated": [],
        "evaluation": {
            "coverage": {
                "covered_assertions": [
                    {"assertion_id": "org.example.check.first", "evidence_sha256": [DIGEST]}
                ],
                "uncovered_assertions": [],
            }
        },
    }
    with pytest.raises(ContractError, match="require their product result"):
        _validate_native_assessment_coverage(result)
