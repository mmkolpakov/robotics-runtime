from __future__ import annotations

import json
import math
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from random import Random

import pytest

from robotics_acceptance_harness._histogram_estimates import Estimate, estimate_statistic
from robotics_acceptance_harness.metrics import HistogramSample, evaluate_metric_assertions
from robotics_acceptance_harness.otel import load_otlp_json_metrics


def histogram(values: list[float], *, extrema: bool) -> HistogramSample:
    bounds = (-10.0, 0.0, 0.1, 1.0, 10.0)
    counts = [0] * (len(bounds) + 1)
    for value in values:
        index = next((i for i, bound in enumerate(bounds) if value <= bound), len(bounds))
        counts[index] += 1
    return HistogramSample(
        name="distribution",
        unit="ms",
        observed_at_ns=2,
        start_time_ns=1,
        temporality="delta",
        count=len(values),
        bucket_counts=tuple(counts),
        explicit_bounds=bounds,
        sum=sum(values),
        min=min(values) if extrema else None,
        max=max(values) if extrema else None,
    )


@pytest.mark.parametrize("extrema", [False, True])
def test_intervals_contain_exact_empirical_statistics(extrema: bool) -> None:
    random = Random(28)
    for _ in range(100):
        values = sorted(random.uniform(-20, 20) for _ in range(random.randint(1, 100)))
        sample = histogram(values, extrema=extrema)
        exact = {"min": values[0], "max": values[-1]}
        for aggregation, quantile in (("p50", 0.5), ("p95", 0.95), ("p99", 0.99)):
            exact[aggregation] = values[math.ceil(quantile * len(values)) - 1]
        for aggregation, value in exact.items():
            estimate = estimate_statistic(sample, aggregation)
            assert estimate.lower <= value <= estimate.upper
            if estimate.lower_exclusive:
                assert estimate.lower < value
        assert estimate_statistic(sample, "count") == Estimate(len(values), len(values))
        mean = sum(values) / len(values)
        assert estimate_statistic(sample, "mean") == Estimate(mean, mean)


def test_large_integer_counts_choose_the_exact_rank() -> None:
    sample = HistogramSample(
        name="distribution",
        unit="1",
        observed_at_ns=2,
        count=9007199254740993,
        bucket_counts=(4503599627370496, 4503599627370497),
        explicit_bounds=(1.0,),
        min=0.0,
        max=2.0,
    )
    assert estimate_statistic(sample, "p50") == Estimate(1.0, 2.0, lower_exclusive=True)
    count = estimate_statistic(sample, "count")
    assert type(count.lower) is int
    assert count.lower == sample.count


@pytest.mark.parametrize(
    ("operator", "threshold", "status"),
    [
        ("lte", 10, "passed"),
        ("lte", 1, "failed"),
        ("lte", 5, "skipped"),
        ("lt", 10, "skipped"),
        ("lt", 2, "failed"),
        ("lt", 11, "passed"),
        ("gte", 2, "passed"),
        ("gte", 11, "failed"),
        ("gte", 5, "skipped"),
        ("gt", 2, "skipped"),
        ("gt", 10, "failed"),
        ("gt", 1, "passed"),
        ("eq", 1, "failed"),
        ("eq", 11, "failed"),
        ("eq", 5, "skipped"),
    ],
)
def test_threshold_requires_proof_for_the_entire_interval(
    operator: str, threshold: float, status: str
) -> None:
    assert Estimate(2, 10).compare(operator, threshold) == status


def test_exact_equality_and_unbounded_estimates() -> None:
    assert Estimate(2, 2).compare("eq", 2) == "passed"
    assert Estimate(2, math.inf).compare("lte", 1) == "failed"
    assert Estimate(2, math.inf).compare("lte", 5) == "skipped"
    assert Estimate(-math.inf, 2).compare("gte", 3) == "failed"
    assert Estimate(-math.inf, math.inf).compare("eq", 2) == "skipped"


def test_unit_alone_does_not_establish_nonnegative_values() -> None:
    sample = histogram([0.05], extrema=False)
    assert estimate_statistic(sample, "max") == Estimate(0.0, 0.1, lower_exclusive=True)
    underflow = histogram([-20.0], extrema=False)
    assert estimate_statistic(underflow, "min") == Estimate(-math.inf, -10.0)
    with pytest.raises(ValueError, match="negative value"):
        estimate_statistic(underflow, "min", nonnegative=True)


def test_nonnegative_domain_bounds_first_bucket_without_recorded_minimum() -> None:
    sample = HistogramSample(
        name="latency",
        unit="ms",
        observed_at_ns=2,
        count=2,
        bucket_counts=(2, 0),
        explicit_bounds=(1.0,),
    )
    assert estimate_statistic(sample, "min") == Estimate(-math.inf, 1)
    assert estimate_statistic(sample, "min", nonnegative=True) == Estimate(0, 1)


def test_empty_histogram_has_a_count_but_no_quantile() -> None:
    sample = HistogramSample(
        name="latency", unit="ms", observed_at_ns=2, count=0, bucket_counts=(0,), explicit_bounds=()
    )
    assert estimate_statistic(sample, "count") == Estimate(0, 0)
    with pytest.raises(ValueError, match="no recorded events"):
        estimate_statistic(sample, "p50")


def occupied_bucket(bounds: tuple[float, ...], index: int) -> HistogramSample:
    return HistogramSample(
        name="latency",
        unit="ms",
        observed_at_ns=1_000_000_001,
        start_time_ns=1,
        temporality="delta",
        count=1,
        bucket_counts=tuple(int(bucket == index) for bucket in range(len(bounds) + 1)),
        explicit_bounds=bounds,
    )


@pytest.mark.parametrize(
    ("operator", "threshold", "status"),
    [
        ("lte", 5, "failed"),
        ("lte", 10, "passed"),
        ("gt", 5, "passed"),
        ("eq", 5, "failed"),
        ("lt", 5, "failed"),
        ("gte", 5, "passed"),
        ("lt", 10, "skipped"),
        ("gt", 10, "failed"),
        ("eq", 10, "skipped"),
        ("lte", 7, "skipped"),
    ],
)
def test_explicit_bucket_preserves_the_exclusive_lower_edge(
    operator: str, threshold: float, status: str
) -> None:
    estimate = estimate_statistic(occupied_bucket((5.0, 10.0), 1), "p95")
    assert estimate == Estimate(5.0, 10.0, lower_exclusive=True)
    assert estimate.describe() == "(5.0, 10.0]"
    assert estimate.compare(operator, threshold) == status


def test_explicit_bucket_upper_edge_and_overflow_lower_edge() -> None:
    upper = estimate_statistic(occupied_bucket((2.5, 5.0), 1), "p95")
    assert upper.compare("lte", 5) == "passed"
    overflow = estimate_statistic(occupied_bucket((5.0,), 1), "p95")
    assert overflow == Estimate(5.0, math.inf, lower_exclusive=True)
    assert overflow.compare("lte", 5) == "failed"
    assert overflow.compare("gt", 5) == "passed"


def test_nonnegative_floor_preserves_only_the_original_excluded_edge() -> None:
    positive = estimate_statistic(occupied_bucket((0.0, 0.1), 1), "p95", nonnegative=True)
    assert positive == Estimate(0.0, 0.1, lower_exclusive=True)
    assert positive.compare("lte", 0) == "failed"
    underflow = estimate_statistic(occupied_bucket((0.0,), 0), "p95", nonnegative=True)
    assert underflow == Estimate(0.0, 0.0)
    assert underflow.compare("eq", 0) == "passed"
    straddling = estimate_statistic(occupied_bucket((-1.0, 1.0), 1), "p95", nonnegative=True)
    assert straddling == Estimate(0.0, 1.0)
    assert straddling.compare("gt", 0) == "skipped"


def test_recorded_minimum_inside_a_bucket_closes_the_tightened_lower_bound() -> None:
    sample = replace(occupied_bucket((5.0, 10.0), 1), min=6.0)
    estimate = estimate_statistic(sample, "p95")
    assert estimate == Estimate(6.0, 10.0)
    assert estimate.compare("gt", 6) == "skipped"
    assert estimate.compare("eq", 6) == "skipped"
    assert estimate.describe() == "[6.0, 10.0]"


def test_recorded_extrema_at_inclusive_edges_use_the_previous_bucket() -> None:
    sample = replace(
        occupied_bucket((5.0, 10.0), 1),
        count=2,
        bucket_counts=(1, 1, 0),
        min=5.0,
        max=10.0,
    )
    assert estimate_statistic(sample, "min") == Estimate(5.0, 5.0)
    assert estimate_statistic(sample, "max") == Estimate(10.0, 10.0)
    assert estimate_statistic(sample, "p95") == Estimate(5.0, 10.0, lower_exclusive=True)


@pytest.mark.parametrize("aggregation", ["min", "max", "mean", "p50", "p95", "p99"])
@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [(None, 5.0), (5.0, None), (None, 11.0), (11.0, None), (5.0, 5.0)],
)
def test_extrema_must_match_the_first_and_last_occupied_buckets(
    aggregation: str, minimum: float | None, maximum: float | None
) -> None:
    sample = replace(occupied_bucket((5.0, 10.0), 1), min=minimum, max=maximum, sum=6.0)
    with pytest.raises(ValueError, match="contradicts occupied buckets"):
        estimate_statistic(sample, aggregation)


@pytest.mark.parametrize("lower", [5.0, 6.0])
def test_empty_open_or_reversed_statistic_intervals_are_rejected(lower: float) -> None:
    with pytest.raises(ValueError, match="bounds are inconsistent"):
        Estimate(lower, 5.0, lower_exclusive=True)


@pytest.mark.parametrize(
    ("aggregation", "minimum", "maximum", "status"),
    [
        ("p95", None, None, "failed"),
        ("p95", None, 5.0, "error"),
        ("p95", 5.0, 5.0, "error"),
        ("max", None, 5.0, "error"),
        ("min", 5.0, None, "error"),
        ("mean", None, 5.0, "error"),
        ("count", None, 10.0, "passed"),
        ("count", None, 5.0, "error"),
    ],
)
def test_public_otlp_bucket_edge_is_a_failure_and_contradictory_extrema_are_errors(
    tmp_path: Path,
    aggregation: str,
    minimum: float | None,
    maximum: float | None,
    status: str,
) -> None:
    point = {
        "startTimeUnixNano": "1",
        "timeUnixNano": "1000000001",
        "count": "30",
        "bucketCounts": ["0", "30", "0"],
        "explicitBounds": [5.0, 10.0],
        "sum": 180.0,
    }
    if minimum is not None:
        point["min"] = minimum
    if maximum is not None:
        point["max"] = maximum
    request = {
        "resourceMetrics": [
            {
                "scopeMetrics": [
                    {
                        "metrics": [
                            {
                                "name": "latency",
                                "unit": "ms",
                                "histogram": {"aggregationTemporality": 1, "dataPoints": [point]},
                            }
                        ]
                    }
                ]
            }
        ]
    }
    path = tmp_path / "metrics.jsonl"
    raw = (json.dumps(request) + "\n").encode()
    path.write_bytes(raw)
    samples = load_otlp_json_metrics(path, expected_sha256=sha256(raw).hexdigest())
    result = evaluate_metric_assertions(
        [
            {
                "assertion_id": "bucket-edge",
                "metric_name": "latency",
                "unit": "ms",
                "window_sec": 1,
                "aggregation": aggregation,
                "operator": "lte",
                "threshold": 30 if aggregation == "count" else 5,
            }
        ],
        samples,
        window_start_ns=1,
        window_end_ns=1_000_000_001,
    )[0]
    assert result.status == status
    if status == "error":
        assert result.observed_value is None
        assert "contradicts occupied buckets" in result.message
    elif aggregation == "count":
        assert result.observed_value == 30
    else:
        assert "(5.0, 10.0]" in result.message
