from __future__ import annotations

import math
from random import Random

import pytest

from robotics_acceptance_harness._histogram_estimates import Estimate, estimate_statistic
from robotics_acceptance_harness.metrics import HistogramSample


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
    assert estimate_statistic(sample, "p50") == Estimate(1.0, 2.0)
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
    assert estimate_statistic(sample, "max") == Estimate(0.0, 0.1)
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
