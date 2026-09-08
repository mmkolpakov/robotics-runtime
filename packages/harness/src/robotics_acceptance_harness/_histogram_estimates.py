"""Conservative statistics for explicit-bucket histograms without event expansion."""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from robotics_acceptance_harness.metrics import HistogramSample

type Comparison = Literal["passed", "failed", "skipped"]


@dataclass(frozen=True, slots=True)
class Estimate:
    """A closed interval containing a statistic, possibly with infinite bounds."""

    lower: float | int
    upper: float | int

    def __post_init__(self) -> None:
        if any(
            isinstance(value, float) and math.isnan(value) for value in (self.lower, self.upper)
        ):
            raise ValueError("histogram statistic bounds cannot be NaN")
        if self.lower > self.upper:
            raise ValueError("histogram statistic bounds are inconsistent")

    def compare(self, operator: str, threshold: float) -> Comparison:
        if not math.isfinite(threshold):
            raise ValueError("histogram threshold must be finite")
        outcomes = {
            "lt": (self.upper < threshold, self.lower >= threshold),
            "lte": (self.upper <= threshold, self.lower > threshold),
            "gt": (self.lower > threshold, self.upper <= threshold),
            "gte": (self.lower >= threshold, self.upper < threshold),
            "eq": (
                self.lower == self.upper == threshold,
                threshold < self.lower or threshold > self.upper,
            ),
        }
        passed, failed = outcomes[operator]
        if passed:
            return "passed"
        return "failed" if failed else "skipped"

    def describe(self) -> str:
        return f"[{self.lower}, {self.upper}]"


def _bucket_estimate(histogram: HistogramSample, index: int, *, nonnegative: bool) -> Estimate:
    lower = histogram.explicit_bounds[index - 1] if index else -math.inf
    upper = histogram.explicit_bounds[index] if index < len(histogram.explicit_bounds) else math.inf
    if nonnegative:
        lower = max(0.0, lower)
    if histogram.min is not None:
        lower = max(histogram.min, lower)
    if histogram.max is not None:
        upper = min(histogram.max, upper)
    return Estimate(lower, upper)


def _rank_bucket(histogram: HistogramSample, rank: int) -> int:
    cumulative = 0
    for index, count in enumerate(histogram.bucket_counts):
        cumulative += count
        if cumulative >= rank:
            return index
    raise ValueError("histogram bucket counts do not cover the requested rank")


def _has_negative_event(histogram: HistogramSample) -> bool:
    return (
        (histogram.min is not None and histogram.min < 0)
        or (histogram.sum is not None and histogram.sum < 0)
        or any(
            upper < 0 and count > 0
            for upper, count in zip(
                histogram.explicit_bounds, histogram.bucket_counts, strict=False
            )
        )
    )


def estimate_statistic(
    histogram: HistogramSample, aggregation: str, *, nonnegative: bool = False
) -> Estimate:
    """Bound the inverse empirical CDF and extrema; retain exact count and recorded mean.

    Quantile rank is ceil(p * count), computed with integer arithmetic. Missing extrema
    leave the first/overflow buckets unbounded; a nonnegative domain must be declared
    by the caller rather than inferred from a time unit alone.
    """
    if aggregation == "count":
        return Estimate(histogram.count, histogram.count)
    if histogram.count == 0:
        raise ValueError("histogram has no recorded events")
    if nonnegative and _has_negative_event(histogram):
        raise ValueError("histogram records a negative value in a nonnegative domain")
    if aggregation == "mean":
        if histogram.sum is None:
            raise ValueError("histogram mean requires a recorded sum")
        mean = histogram.sum / histogram.count
        return Estimate(mean, mean)
    return _rank_estimate(histogram, aggregation, nonnegative=nonnegative)


def _rank_estimate(histogram: HistogramSample, aggregation: str, *, nonnegative: bool) -> Estimate:
    if aggregation == "min":
        if histogram.min is not None:
            return Estimate(histogram.min, histogram.min)
        rank = 1
    elif aggregation == "max":
        if histogram.max is not None:
            return Estimate(histogram.max, histogram.max)
        rank = histogram.count
    else:
        quantile = {"p50": Fraction(1, 2), "p95": Fraction(19, 20), "p99": Fraction(99, 100)}[
            aggregation
        ]
        rank = (histogram.count * quantile.numerator + quantile.denominator - 1) // (
            quantile.denominator
        )
    return _bucket_estimate(histogram, _rank_bucket(histogram, rank), nonnegative=nonnegative)
