from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from robotics_acceptance_harness.metrics import AssertionEvaluation
from robotics_acceptance_harness.readiness import GraphSnapshot, ReadinessIssue, evaluate_graph


def _assertion_id(existing: Sequence[AssertionEvaluation]) -> str:
    used = {assertion.assertion_id for assertion in existing}
    candidate = "expected-ros-graph"
    suffix = 0
    while candidate in used:
        suffix += 1
        candidate = f"expected-ros-graph-{suffix}"
    return candidate


def _issue_detail(issue: ReadinessIssue, observed_at_ns: int | None) -> str:
    detail = f"{issue.json_path}: {issue.message}"
    if observed_at_ns is None:
        return detail
    return f"{detail} (first observed at monotonic_ns={observed_at_ns})"


class ExpectedGraphMonitor:
    """Retain graph issues sampled in [start_ns, end_ns), excluding readiness.

    Missing nodes/endpoints or a wrong lifecycle state are failures. An unavailable
    observation is an error, including a window with no graph samples. Polling
    cannot certify changes that occur entirely between snapshots.
    """

    def __init__(self, expected_graph: Mapping[str, Any], start_ns: int, end_ns: int) -> None:
        if end_ns <= start_ns:
            raise ValueError("graph measurement window must have positive duration")
        self._expected_graph = expected_graph
        self._start_ns = start_ns
        self._end_ns = end_ns
        self._samples = 0
        self._issues: dict[ReadinessIssue, int] = {}

    def observe(self, snapshot: GraphSnapshot) -> None:
        if not self._start_ns <= snapshot.observed_at_ns < self._end_ns:
            return
        self._samples += 1
        for issue in evaluate_graph(self._expected_graph, snapshot):
            self._issues.setdefault(issue, snapshot.observed_at_ns)

    def assertions(
        self, existing: Sequence[AssertionEvaluation]
    ) -> tuple[AssertionEvaluation, ...]:
        issues: dict[ReadinessIssue, int | None] = dict(self._issues)
        if self._samples == 0 and any(self._expected_graph.values()):
            issues[
                ReadinessIssue(
                    "$.expected_ros_graph", "no graph snapshot inside measurement window", "error"
                )
            ] = None
        if not issues:
            return ()
        detail = "; ".join(
            _issue_detail(issue, observed_at_ns) for issue, observed_at_ns in issues.items()
        )
        return (
            AssertionEvaluation(
                assertion_id=_assertion_id(existing),
                status="error" if any(issue.status == "error" for issue in issues) else "failed",
                observed_value=None,
                unit="1",
                message=f"expected ROS graph during measurement: {detail}",
            ),
        )
