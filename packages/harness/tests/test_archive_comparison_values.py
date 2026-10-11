from __future__ import annotations

from typing import Any

import pytest
from robotics_runtime_contracts._qualification_archive import _Archive, _comparison
from robotics_runtime_contracts._qualification_checks import _Context
from robotics_runtime_contracts._qualification_types import QualificationArtifact

RAW_SHA = "a" * 64
CONTROL_SHA = "b" * 64


def _artifact(kind: str, name: str, document: dict[str, Any]) -> QualificationArtifact:
    return QualificationArtifact(kind, name, CONTROL_SHA, 128, document)


def _context(value: int | bool | float, name: str) -> _Context:
    result = _artifact(
        "domain_result",
        name,
        {
            "evaluation": {
                "method": {
                    "implementation": "sample-evaluator",
                    "version": "1",
                    "configuration": {"sha256": CONTROL_SHA, "size_bytes": 128},
                },
                "environment": {"sha256": CONTROL_SHA, "size_bytes": 128},
                "calibration": {"state": "not_applicable", "reason": "software count"},
                "coverage": {
                    "covered_assertions": [
                        {"assertion_id": "sample.count", "evidence_sha256": [RAW_SHA]}
                    ],
                    "uncovered_assertions": [],
                },
            },
            "assertion_results": [
                {
                    "source": "product",
                    "namespace": "sample",
                    "assertion_id": "sample.count",
                    "status": "passed",
                    "observed_value": value,
                    "unit": "count",
                    "evidence_sha256": [RAW_SHA],
                }
            ],
        },
    )
    index = _artifact(
        "evidence_index",
        "evidence-indexes/native.json",
        {"artifacts": [{"kind": "other_evidence", "sha256": RAW_SHA}]},
    )
    return _Context(
        grouped={},
        scenario_artifact=_artifact("scenario", "scenario.json", {}),
        run_artifact=_artifact("acceptance_run", "run.json", {}),
        aggregate_artifact=_artifact("acceptance_aggregate", "aggregate.json", {}),
        runtimes={},
        results={"native": result},
        evidence_indexes={"native": index},
        recording_summaries={},
    )


@pytest.mark.parametrize(("number", "boolean"), [(1, True), (0, False)])
def test_exact_archive_comparison_distinguishes_numeric_and_boolean_outcomes(
    number: int, boolean: bool
) -> None:
    archive = _Archive(
        (),
        _context(number, "original-results/native.json"),
        _context(boolean, "results/native.json"),
    )
    result = _comparison(archive, "native")
    assert result["status"] == "different"
    assert result["compared_assertions"] == ["sample.count"]
    assert result["excluded_assertions"] == []
    assert result["reasons"] == ["assertion_outcome_changed"]


@pytest.mark.parametrize("number", [0, 1, 1.25])
def test_exact_archive_comparison_matches_stable_numeric_outcomes(
    number: int | float,
) -> None:
    archive = _Archive(
        (),
        _context(number, "original-results/native.json"),
        _context(number, "results/native.json"),
    )
    result = _comparison(archive, "native")
    assert result["status"] == "matched"
    assert result["compared_assertions"] == ["sample.count"]
    assert result["excluded_assertions"] == []
    assert result["reasons"] == []
