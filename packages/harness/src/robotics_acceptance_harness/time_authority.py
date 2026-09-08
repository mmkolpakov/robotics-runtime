from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from robotics_acceptance_harness._histogram_estimates import Comparison, Estimate
from robotics_acceptance_harness.metrics import (
    AssertionEvaluation,
    HistogramSample,
    MetricAggregationError,
    MetricInsufficientData,
    MetricPoint,
    histogram_statistic,
    histogram_window_aggregate,
)

DELIVERY_LATENCY_METRIC = "robotics.time_authority.delivery_latency"
RUN_ATTRIBUTE = "run.id"
DOMAIN_ATTRIBUTE = "domain.id"
SOURCE_ATTRIBUTE = "time.source.id"
METHOD_ATTRIBUTE = "time.measurement.method"
RMW_LATENCY_METHOD = "rmw_source_to_reception_latency"


@dataclass(frozen=True, slots=True)
class TimeAuthorityObservation:
    """Time evidence with explicit diagnostics for bounded or unavailable statistics."""

    source_id: str
    sample_count: int
    window_start_ns: int
    window_end_ns: int
    p50_ms: float
    p95_ms: float
    max_ms: float
    within_policy: bool
    evaluation: AssertionEvaluation | None = None


@dataclass(frozen=True, slots=True)
class _LatencyContext:
    run_id: str
    domain_id: str
    source_id: str
    start_ns: int
    end_ns: int

    def matches(self, sample: MetricPoint) -> bool:
        # Cumulative points before the boundary supply the baseline.
        return (
            sample.observed_at_ns <= self.end_ns
            and sample.attributes.get(RUN_ATTRIBUTE) == self.run_id
            and sample.attributes.get(DOMAIN_ATTRIBUTE) == self.domain_id
            and sample.attributes.get(SOURCE_ATTRIBUTE) == self.source_id
            and sample.attributes.get(METHOD_ATTRIBUTE) == RMW_LATENCY_METHOD
        )


def _latency_histogram(samples: Sequence[MetricPoint], context: _LatencyContext) -> HistogramSample:
    matching = [
        sample
        for sample in samples
        if sample.name == DELIVERY_LATENCY_METRIC and context.matches(sample)
    ]
    if not matching:
        raise MetricInsufficientData("no attributed delivery-latency histogram in the window")
    if any(not isinstance(sample, HistogramSample) or sample.unit != "ms" for sample in matching):
        raise MetricAggregationError("delivery latency requires explicit-bucket histograms in ms")
    selected = [sample for sample in matching if isinstance(sample, HistogramSample)]
    return histogram_window_aggregate(
        selected, window_start_ns=context.start_ns, window_end_ns=context.end_ns
    )


def _display_bound(estimate: Estimate) -> float:
    """Use a finite endpoint in legacy numeric slots; diagnostics retain both bounds."""
    return float(estimate.upper if math.isfinite(estimate.upper) else estimate.lower)


def _latency_policy(
    histogram: HistogramSample, policy: Mapping[str, Any]
) -> tuple[tuple[float, float, float], AssertionEvaluation]:
    if histogram.count == 0:
        return (0.0, 0.0, 0.0), AssertionEvaluation(
            assertion_id="time-authority-evidence",
            status="failed",
            observed_value=0,
            unit="samples",
            message=(
                f"count 0 < {policy['time_authority_min_samples']}; "
                "no latency events; numeric latency fields are unavailable placeholders"
            ),
        )
    estimates = tuple(
        histogram_statistic(histogram, aggregation, nonnegative=True)
        for aggregation in ("p50", "p95", "max")
    )
    thresholds = tuple(
        float(policy[key])
        for key in (
            "max_time_authority_delivery_latency_p50_ms",
            "max_time_authority_delivery_latency_p95_ms",
            "max_time_authority_delivery_latency_ms",
        )
    )
    outcomes = [
        estimate.compare("lte", threshold)
        for estimate, threshold in zip(estimates, thresholds, strict=True)
    ]
    outcomes.append(
        "passed" if histogram.count >= int(policy["time_authority_min_samples"]) else "failed"
    )
    status: Comparison = (
        "failed" if "failed" in outcomes else "skipped" if "skipped" in outcomes else "passed"
    )
    message = "; ".join(
        f"{name} bound {estimate.describe()} ms <= {threshold}"
        for name, estimate, threshold in zip(
            ("p50", "p95", "max"), estimates, thresholds, strict=True
        )
    )
    message += (
        f"; count {histogram.count} >= {policy['time_authority_min_samples']}"
        "; numeric fields are finite bounds, not recovered event values"
    )
    p50, p95, maximum = (_display_bound(estimate) for estimate in estimates)
    return (p50, p95, maximum), AssertionEvaluation(
        assertion_id="time-authority-evidence",
        status=status,
        observed_value=histogram.count,
        unit="samples",
        message=message,
    )


def _observe_latency(
    policy: Mapping[str, Any], samples: Sequence[MetricPoint], context: _LatencyContext
) -> TimeAuthorityObservation:
    count = 0
    p50 = p95 = maximum = 0.0
    try:
        histogram = _latency_histogram(samples, context)
        count = histogram.count
        (p50, p95, maximum), evaluation = _latency_policy(histogram, policy)
    except MetricAggregationError as error:
        evaluation = AssertionEvaluation(
            assertion_id="time-authority-evidence",
            status="skipped" if isinstance(error, MetricInsufficientData) else "error",
            observed_value=None,
            unit="samples",
            message=f"{error}; unavailable numeric fields use 0 placeholders, not measured zeros",
        )
    return TimeAuthorityObservation(
        source_id=context.source_id,
        sample_count=count,
        window_start_ns=context.start_ns,
        window_end_ns=context.end_ns,
        p50_ms=p50,
        p95_ms=p95,
        max_ms=maximum,
        within_policy=evaluation.status == "passed",
        evaluation=evaluation,
    )


def evaluate_time_authority(
    time_policy: Mapping[str, Any],
    samples: Sequence[MetricPoint],
    *,
    run_id: str,
    domain_id: str,
    source_id: str,
    window_start_ns: int,
    window_end_ns: int,
) -> TimeAuthorityObservation:
    """Evaluate latency bounds without confusing uncertainty with a proven breach."""
    return _observe_latency(
        time_policy,
        samples,
        _LatencyContext(run_id, domain_id, source_id, window_start_ns, window_end_ns),
    )
