from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from robotics_acceptance_harness.campaign import aggregate_campaign
from robotics_acceptance_harness.documents import BundleValidationError
from robotics_acceptance_harness.result import write_contract_json
from tests.test_aggregate import base_aggregate, run_context, write_json

SCENARIO = Path(__file__).parent / "fixtures" / "simulation" / "scenario.yaml"


def test_campaign_aggregates_digest_linked_run_verdicts(tmp_path: Path) -> None:
    context = run_context(tmp_path)
    aggregate = base_aggregate(tmp_path, context)
    output = aggregate_campaign(
        scenario_path=SCENARIO,
        run_context_paths=(context,),
        aggregate_paths=(aggregate,),
        output_path=tmp_path / "campaign.json",
        minimum_passed_runs=1,
    )

    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["schema_version"] == "campaign-summary.v1"
    assert document["verdict"]["status"] == "passed"
    assert document["scenario_sha256"]
    assert document["runs"][0]["acceptance_run_sha256"]
    assert document["runs"][0]["aggregate_sha256"]


def test_campaign_rejects_aggregate_for_another_run_context(tmp_path: Path) -> None:
    context = run_context(tmp_path)
    aggregate_path = base_aggregate(tmp_path, context)
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    aggregate["acceptance_run_sha256"] = "f" * 64
    write_json(aggregate_path, aggregate)

    with pytest.raises(BundleValidationError, match="another run context"):
        aggregate_campaign(
            scenario_path=SCENARIO,
            run_context_paths=(context,),
            aggregate_paths=(aggregate_path,),
            output_path=tmp_path / "campaign.json",
            minimum_passed_runs=1,
        )


def test_campaign_preserves_incomplete_as_the_policy_verdict(tmp_path: Path) -> None:
    context = run_context(tmp_path)
    aggregate_path = base_aggregate(tmp_path, context)
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    aggregate["per_domain_results"][0]["status"] = "incomplete"
    aggregate["per_domain_aggregate"] = "incomplete"
    write_json(aggregate_path, aggregate)

    output = aggregate_campaign(
        scenario_path=SCENARIO,
        run_context_paths=(context,),
        aggregate_paths=(aggregate_path,),
        output_path=tmp_path / "campaign.json",
        minimum_passed_runs=2,
    )

    assert json.loads(output.read_text(encoding="utf-8"))["verdict"]["status"] == "incomplete"


@pytest.mark.parametrize(
    ("statuses", "minimum_passed", "limits", "expected"),
    [
        (("passed", "passed"), 3, (0, 0, 0), "incomplete"),
        (("passed", "passed"), 2, (0, 0, 0), "passed"),
        (("passed", "incomplete"), 2, (0, 1, 0), "incomplete"),
        (("passed", "incomplete"), 1, (0, 0, 0), "incomplete"),
        (("passed", "incomplete"), 1, (0, 1, 0), "passed"),
        (("passed", "failed"), 2, (1, 0, 0), "failed"),
        (("passed", "failed"), 1, (0, 0, 0), "failed"),
        (("passed", "failed"), 1, (1, 0, 0), "passed"),
        (("passed", "error"), 2, (0, 0, 1), "error"),
        (("passed", "error"), 1, (0, 0, 0), "error"),
        (("passed", "error"), 1, (0, 0, 1), "passed"),
        (("passed", "failed", "error"), 2, (1, 0, 1), "error"),
        (("passed", "failed", "incomplete"), 1, (1, 0, 0), "failed"),
        (("passed", "error", "incomplete"), 1, (0, 0, 1), "error"),
    ],
)
def test_campaign_writes_shortfall_without_changing_tolerated_run_policy(
    tmp_path: Path,
    statuses: tuple[str, ...],
    minimum_passed: int,
    limits: tuple[int, int, int],
    expected: str,
) -> None:
    context_path = run_context(tmp_path)
    aggregate_path = base_aggregate(tmp_path, context_path)
    context_template = json.loads(context_path.read_text(encoding="utf-8"))
    aggregate_template = json.loads(aggregate_path.read_text(encoding="utf-8"))
    contexts: list[Path] = []
    aggregates: list[Path] = []
    for index, status in enumerate(statuses):
        context = deepcopy(context_template)
        context["run_id"] = f"run-00000000-0000-4000-8000-{index:012d}"
        context_path = write_contract_json(context, tmp_path / f"run-{index}.json")
        aggregate = deepcopy(aggregate_template)
        aggregate["run_id"] = context["run_id"]
        aggregate["aggregate_id"] = f"aggregate-00000000-0000-4000-8000-{index:012d}"
        aggregate["acceptance_run_sha256"] = sha256(context_path.read_bytes()).hexdigest()
        aggregate["per_domain_results"][0]["status"] = status
        aggregate["per_domain_aggregate"] = status
        contexts.append(context_path)
        aggregates.append(write_contract_json(aggregate, tmp_path / f"aggregate-{index}.json"))

    output = aggregate_campaign(
        scenario_path=SCENARIO,
        run_context_paths=contexts,
        aggregate_paths=aggregates,
        output_path=tmp_path / "campaign.json",
        minimum_passed_runs=minimum_passed,
        maximum_failed_runs=limits[0],
        maximum_incomplete_runs=limits[1],
        maximum_error_runs=limits[2],
    )

    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["verdict"]["status"] == expected
    assert document["verdict"]["total_runs"] == len(statuses)
    for status in ("passed", "failed", "incomplete", "error"):
        assert document["verdict"][f"{status}_runs"] == statuses.count(status)
