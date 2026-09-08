from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from robotics_runtime_contracts import SemanticValidationError, validate_document

LEGACY_SHORTFALL = Path(__file__).parent / "fixtures/campaign/valid/legacy-shortfall.json"


def campaign_summary(
    statuses: tuple[str, ...],
    minimum_passed: int,
    limits: tuple[int, int, int],
    verdict: str,
) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(LEGACY_SHORTFALL.read_text(encoding="utf-8"))
    document["runs"] = [
        {
            "run_id": f"run-{index}",
            "acceptance_run_sha256": f"{index * 2:064x}",
            "aggregate_sha256": f"{index * 2 + 1:064x}",
            "parameters": {},
            "status": status,
        }
        for index, status in enumerate(statuses, start=1)
    ]
    document["acceptance"] = {
        "minimum_passed_runs": minimum_passed,
        "maximum_failed_runs": limits[0],
        "maximum_incomplete_runs": limits[1],
        "maximum_error_runs": limits[2],
    }
    document["verdict"] = {
        "status": verdict,
        "total_runs": len(statuses),
        **{
            f"{status}_runs": statuses.count(status)
            for status in ("passed", "failed", "incomplete", "error")
        },
    }
    return document


def test_v1_legacy_failed_shortfall_remains_valid_without_mutation() -> None:
    # This exact fixture is also valid under the published contracts v0.16.0 reader.
    document = json.loads(LEGACY_SHORTFALL.read_text(encoding="utf-8"))
    original = deepcopy(document)

    validate_document(document)

    assert document == original
    assert document["verdict"]["status"] == "failed"


@pytest.mark.parametrize("verdict", ["passed", "failed", "incomplete", "error"])
@pytest.mark.parametrize(
    ("statuses", "minimum_passed", "limits", "allowed"),
    [
        (("passed", "passed"), 3, (0, 0, 0), {"failed", "incomplete"}),
        (("passed", "passed"), 2, (0, 0, 0), {"passed"}),
        (("passed", "incomplete"), 2, (0, 1, 0), {"incomplete"}),
        (("passed", "incomplete"), 1, (0, 0, 0), {"incomplete"}),
        (("passed", "incomplete"), 1, (0, 1, 0), {"passed"}),
        (("passed", "failed"), 2, (1, 0, 0), {"failed"}),
        (("passed", "failed"), 1, (0, 0, 0), {"failed"}),
        (("passed", "failed"), 1, (1, 0, 0), {"passed"}),
        (("passed", "error"), 2, (0, 0, 1), {"error"}),
        (("passed", "error"), 1, (0, 0, 0), {"error"}),
        (("passed", "error"), 1, (0, 0, 1), {"passed"}),
        (("passed", "failed", "error"), 2, (1, 0, 1), {"error"}),
        (("passed", "failed", "incomplete"), 1, (1, 0, 0), {"failed"}),
        (("passed", "error", "incomplete"), 1, (0, 0, 1), {"error"}),
    ],
)
def test_campaign_shortfall_relaxation_preserves_policy_thresholds(
    statuses: tuple[str, ...],
    minimum_passed: int,
    limits: tuple[int, int, int],
    allowed: set[str],
    verdict: str,
) -> None:
    document = campaign_summary(statuses, minimum_passed, limits, verdict)

    if verdict in allowed:
        validate_document(document)
    else:
        with pytest.raises(SemanticValidationError, match="campaign policy verdict") as caught:
            validate_document(document)
        assert caught.value.json_path == "$.verdict.status"


def test_incomplete_shortfall_still_requires_truthful_counts() -> None:
    document = campaign_summary(("passed", "passed"), 3, (0, 0, 0), "incomplete")
    document["verdict"]["passed_runs"] = 1

    with pytest.raises(SemanticValidationError) as caught:
        validate_document(document)

    assert caught.value.json_path == "$.verdict.passed_runs"
