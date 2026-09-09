from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from itertools import pairwise
from statistics import fmean
from types import MappingProxyType
from typing import Any, Literal

from robotics_acceptance_harness._histogram_estimates import Estimate, estimate_statistic
from robotics_acceptance_harness.errors import HarnessError, HarnessInputError

MetricAttribute = str | bool | int | float
MetricTemporality = Literal["delta", "cumulative", "unspecified"]
type MetricSeriesKey = tuple[tuple[str, str, MetricAttribute], ...]
type MetricIntervalCoverage = tuple[tuple[MetricSeriesKey, int, int], ...]
METRIC_WINDOW_COVERAGE_TOLERANCE_NS = 1_000_000_000
METRIC_WINDOW_MAX_UNCOVERED_FRACTION = 0.05


@dataclass(frozen=True, slots=True)
class MetricSample:
    name: str
    value: float
    unit: str
    observed_at_ns: int
    attributes: Mapping[str, MetricAttribute] = field(default_factory=dict)
    instrument_kind: Literal["gauge", "sum"] = "gauge"
    temporality: MetricTemporality | None = None
    start_time_ns: int = 0
    monotonic: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))
        if not math.isfinite(self.value):
            raise HarnessInputError("metric sample value must be finite")
        if self.instrument_kind not in {"gauge", "sum"}:
            raise HarnessInputError("unsupported scalar metric instrument kind")
        if self.temporality not in {None, "delta", "cumulative", "unspecified"}:
            raise HarnessInputError("unsupported metric aggregation temporality")
        if self.instrument_kind == "gauge" and self.temporality is not None:
            raise HarnessInputError("gauge samples cannot declare aggregation temporality")
        if self.instrument_kind == "sum" and self.temporality is None:
            raise HarnessInputError("sum samples require aggregation temporality")
        if self.start_time_ns < 0 or self.observed_at_ns < 0:
            raise HarnessInputError("metric timestamps cannot be negative")
        if self.start_time_ns and self.start_time_ns > self.observed_at_ns:
            raise HarnessInputError("metric start time cannot follow observation time")


@dataclass(frozen=True, slots=True)
class HistogramSample:
    name: str
    unit: str
    observed_at_ns: int
    count: int
    bucket_counts: tuple[int, ...]
    explicit_bounds: tuple[float, ...]
    attributes: Mapping[str, MetricAttribute] = field(default_factory=dict)
    temporality: MetricTemporality = "unspecified"
    start_time_ns: int = 0
    sum: float | None = None
    min: float | None = None
    max: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))
        if self.temporality not in {"delta", "cumulative", "unspecified"}:
            raise HarnessInputError("unsupported histogram aggregation temporality")
        if self.start_time_ns < 0 or self.observed_at_ns < 0:
            raise HarnessInputError("histogram timestamps cannot be negative")
        if self.start_time_ns and self.start_time_ns > self.observed_at_ns:
            raise HarnessInputError("histogram start time cannot follow observation time")
        if self.count < 0 or any(count < 0 for count in self.bucket_counts):
            raise HarnessInputError("histogram counts cannot be negative")
        if len(self.bucket_counts) != len(self.explicit_bounds) + 1:
            raise HarnessInputError("histogram requires one more bucket count than explicit bounds")
        if sum(self.bucket_counts) != self.count:
            raise HarnessInputError("histogram bucket counts must add up to count")
        if any(not math.isfinite(bound) for bound in self.explicit_bounds):
            raise HarnessInputError("histogram explicit bounds must be finite")
        if any(current >= following for current, following in pairwise(self.explicit_bounds)):
            raise HarnessInputError("histogram explicit bounds must be strictly increasing")
        if any(
            value is not None and not math.isfinite(value)
            for value in (self.sum, self.min, self.max)
        ):
            raise HarnessInputError("histogram summary values must be finite")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise HarnessInputError("histogram min cannot exceed max")


type MetricPoint = MetricSample | HistogramSample


class MetricAggregationError(HarnessError, ValueError):
    """Raised when metric points cannot form an unambiguous window aggregate."""

    error_id = "MetricAggregationError.failed"


class MetricInsufficientData(MetricAggregationError):
    """Valid observations do not determine the requested window statistic."""

    error_id = "MetricInsufficientData.failed"


@dataclass(frozen=True, slots=True)
class CounterWindowAggregate:
    total: float
    coverage: MetricIntervalCoverage
    temporality: MetricTemporality


@dataclass(frozen=True, slots=True)
class AssertionEvaluation:
    assertion_id: str
    status: Literal["passed", "failed", "error", "skipped"]
    observed_value: float | int | str | bool | None
    unit: str
    message: str = ""
    source: Literal["core", "product"] = "core"
    namespace: str | None = None
    evidence_sha256: tuple[str, ...] = ()


class MetricDefinitionError(HarnessError, ValueError):
    """Raised when observed OTLP instruments contradict their declarations."""

    error_id = "MetricDefinitionError.failed"


def percentile(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _aggregate(name: str, values: Sequence[float]) -> float | int:
    if name == "min":
        return min(values)
    if name == "max":
        return max(values)
    if name == "mean":
        return fmean(values)
    if name == "p50":
        return percentile(values, 0.50)
    if name == "p95":
        return percentile(values, 0.95)
    if name == "p99":
        return percentile(values, 0.99)
    if name == "count":
        return len(values)
    raise HarnessInputError(f"unsupported aggregation: {name}")


def _series_key(
    attributes: Mapping[str, MetricAttribute],
) -> MetricSeriesKey:
    return tuple(sorted((key, type(value).__name__, value) for key, value in attributes.items()))


def _validated_delta_points(
    samples: Sequence[MetricPoint],
    *,
    window_start_ns: int,
    window_end_ns: int,
    metric_name: str,
) -> list[MetricPoint]:
    selected = [
        sample
        for sample in samples
        if window_start_ns <= sample.observed_at_ns <= window_end_ns
        and sample.start_time_ns >= window_start_ns
    ]
    grouped: dict[MetricSeriesKey, list[MetricPoint]] = defaultdict(list)
    for sample in selected:
        if sample.start_time_ns >= sample.observed_at_ns:
            raise MetricAggregationError(
                f"{metric_name} contains an empty or reversed delta interval"
            )
        grouped[_series_key(sample.attributes)].append(sample)

    for series in grouped.values():
        previous_end_ns: int | None = None
        for sample in sorted(
            series,
            key=lambda point: (point.start_time_ns, point.observed_at_ns),
        ):
            if previous_end_ns is not None and sample.start_time_ns < previous_end_ns:
                raise MetricAggregationError(
                    f"{metric_name} contains duplicate or overlapping delta intervals"
                )
            previous_end_ns = sample.observed_at_ns
    return selected


def _interval_coverage(samples: Sequence[MetricPoint]) -> MetricIntervalCoverage:
    return tuple(
        sorted(
            (
                _series_key(sample.attributes),
                sample.start_time_ns,
                sample.observed_at_ns,
            )
            for sample in samples
        )
    )


def _interior_coverage_gap_ns(
    intervals: Sequence[tuple[int, int]],
    *,
    metric_name: str,
    temporality: MetricTemporality | None,
    window_start_ns: int,
    window_end_ns: int,
) -> int:
    """Validate ordered intervals and total their gaps inside the evaluation window."""

    uncovered_ns = 0
    previous_end_ns: int | None = None
    for start_ns, end_ns in intervals:
        if start_ns >= end_ns:
            raise MetricAggregationError(
                f"{metric_name} contains empty or reversed coverage intervals"
            )
        if previous_end_ns is not None:
            if start_ns < previous_end_ns:
                raise MetricAggregationError(
                    f"{metric_name} contains overlapping coverage intervals"
                )
            if start_ns > previous_end_ns and temporality != "delta":
                raise MetricAggregationError(f"{metric_name} contains gapped coverage intervals")
            uncovered_ns += max(
                0, min(start_ns, window_end_ns) - max(previous_end_ns, window_start_ns)
            )
        previous_end_ns = end_ns
    return uncovered_ns


def require_window_coverage(
    coverage: MetricIntervalCoverage,
    *,
    metric_name: str,
    temporality: MetricTemporality | None,
    window_start_ns: int,
    window_end_ns: int,
    tolerance_ns: int = METRIC_WINDOW_COVERAGE_TOLERANCE_NS,
) -> None:
    """Require each series' total uncovered window time to stay within tolerance."""

    if tolerance_ns < 0:
        raise HarnessInputError("metric coverage tolerance cannot be negative")
    window_duration_ns = window_end_ns - window_start_ns
    if window_duration_ns <= 0:
        raise HarnessInputError("metric evaluation window must have positive duration")
    effective_tolerance_ns = min(
        tolerance_ns,
        int(window_duration_ns * METRIC_WINDOW_MAX_UNCOVERED_FRACTION),
    )
    if not coverage:
        raise MetricAggregationError(f"{metric_name} has no interval coverage")
    by_series: dict[MetricSeriesKey, list[tuple[int, int]]] = defaultdict(list)
    for series_key, start_ns, end_ns in coverage:
        by_series[series_key].append((start_ns, end_ns))
    for intervals in by_series.values():
        ordered = sorted(intervals)
        interior_gap_ns = _interior_coverage_gap_ns(
            ordered,
            metric_name=metric_name,
            temporality=temporality,
            window_start_ns=window_start_ns,
            window_end_ns=window_end_ns,
        )
        first_start_ns = ordered[0][0]
        last_end_ns = ordered[-1][1]
        if abs(first_start_ns - window_start_ns) > effective_tolerance_ns:
            raise MetricAggregationError(
                f"{metric_name} starts outside the evaluation-window coverage tolerance"
            )
        if abs(last_end_ns - window_end_ns) > effective_tolerance_ns:
            raise MetricAggregationError(
                f"{metric_name} ends outside the evaluation-window coverage tolerance"
            )
        uncovered_ns = (
            max(0, first_start_ns - window_start_ns)
            + interior_gap_ns
            + max(0, window_end_ns - last_end_ns)
        )
        if uncovered_ns > effective_tolerance_ns:
            raise MetricAggregationError(
                f"{metric_name} does not cover enough of the evaluation window"
            )


def histogram_window_coverage(
    samples: Sequence[HistogramSample],
    *,
    window_start_ns: int,
    window_end_ns: int,
) -> MetricIntervalCoverage:
    """Return the contribution intervals used by a histogram window aggregate."""

    if not samples:
        raise MetricAggregationError("no histogram samples")
    coverage = _interval_coverage(
        _histogram_contributions(
            samples,
            window_start_ns=window_start_ns,
            window_end_ns=window_end_ns,
        )
    )
    return tuple(
        (
            series_key,
            max(start_ns, window_start_ns),
            min(end_ns, window_end_ns),
        )
        for series_key, start_ns, end_ns in coverage
        if max(start_ns, window_start_ns) < min(end_ns, window_end_ns)
    )


def _matching_window(
    samples: Sequence[MetricPoint],
    *,
    window_start_ns: int,
    window_end_ns: int,
) -> list[MetricPoint]:
    return [
        sample for sample in samples if window_start_ns <= sample.observed_at_ns <= window_end_ns
    ]


def _subtract_histograms(
    latest: HistogramSample,
    baseline: HistogramSample,
) -> HistogramSample:
    if (
        latest.name != baseline.name
        or latest.unit != baseline.unit
        or latest.attributes != baseline.attributes
    ):
        raise MetricAggregationError(
            "cumulative histogram identity changed between baseline and current point"
        )
    if latest.explicit_bounds != baseline.explicit_bounds:
        raise MetricAggregationError("cumulative histogram bucket boundaries changed")
    bucket_counts = tuple(
        current - previous
        for current, previous in zip(
            latest.bucket_counts,
            baseline.bucket_counts,
            strict=True,
        )
    )
    count = latest.count - baseline.count
    if count < 0 or any(value < 0 for value in bucket_counts):
        raise MetricAggregationError("cumulative histogram counters moved backwards")
    if baseline.count and (latest.sum is None) != (baseline.sum is None):
        raise MetricAggregationError("cumulative histogram sum availability changed")
    baseline_sum = 0.0 if baseline.count == 0 else baseline.sum
    sum_value = (
        latest.sum - baseline_sum if latest.sum is not None and baseline_sum is not None else None
    )
    return HistogramSample(
        name=latest.name,
        unit=latest.unit,
        observed_at_ns=latest.observed_at_ns,
        count=count,
        bucket_counts=bucket_counts,
        explicit_bounds=latest.explicit_bounds,
        attributes=latest.attributes,
        temporality="delta",
        start_time_ns=baseline.observed_at_ns,
        sum=sum_value,
        min=latest.min if baseline.count == 0 else None,
        max=latest.max if baseline.count == 0 else None,
    )


def _checked_cumulative_series(samples: Sequence[HistogramSample]) -> list[HistogramSample]:
    ordered = sorted(samples, key=lambda sample: sample.observed_at_ns)
    for previous, current in pairwise(ordered):
        if (current.name, current.unit) != (previous.name, previous.unit):
            raise MetricAggregationError("cumulative histogram identity changed")
        if current.observed_at_ns == previous.observed_at_ns:
            raise MetricAggregationError("duplicate cumulative histogram observations")
        if current.explicit_bounds != previous.explicit_bounds:
            raise MetricAggregationError("cumulative histogram bucket boundaries changed")
        if any(
            right < left
            for left, right in zip(previous.bucket_counts, current.bucket_counts, strict=True)
        ):
            raise MetricInsufficientData("cumulative histogram reset has no new start timestamp")
    return ordered


def _cumulative_window_sample(
    samples: Sequence[HistogramSample], window_start_ns: int
) -> HistogramSample | None:
    ordered = _checked_cumulative_series(samples)
    latest = ordered[-1]
    if latest.observed_at_ns <= window_start_ns:
        return None
    if latest.start_time_ns >= window_start_ns:
        if ordered[0].start_time_ns == ordered[0].observed_at_ns:
            # OTLP's unknown-start marker carries historical population, not
            # events observed since this start timestamp.
            return _subtract_histograms(latest, ordered[0])
        return latest
    baselines = [sample for sample in ordered if sample.observed_at_ns <= window_start_ns]
    if not baselines:
        raise MetricInsufficientData(
            "cumulative histogram has no baseline at the evaluation-window start"
        )
    baseline = baselines[-1]
    if baseline.observed_at_ns < window_start_ns:
        following = next(sample for sample in ordered if sample.observed_at_ns > window_start_ns)
        if baseline.bucket_counts != following.bucket_counts:
            raise MetricInsufficientData(
                "cumulative histogram baseline precedes the window; event times are unknown"
            )
        # Equal monotonic bucket counts prove that no event straddled this boundary.
        baseline = replace(baseline, observed_at_ns=window_start_ns)
    return _subtract_histograms(latest, baseline)


def _histogram_contributions(
    samples: Sequence[HistogramSample],
    *,
    window_start_ns: int,
    window_end_ns: int,
) -> list[HistogramSample]:
    if not samples:
        raise MetricInsufficientData("no histogram samples")
    temporalities = {sample.temporality for sample in samples}
    if len(temporalities) != 1:
        raise MetricAggregationError("mixed histogram aggregation temporalities")
    temporality = next(iter(temporalities))
    if temporality == "unspecified":
        raise MetricAggregationError("histogram aggregation temporality is unspecified")
    if temporality == "delta":
        return [
            sample
            for sample in _validated_delta_points(
                samples,
                window_start_ns=window_start_ns,
                window_end_ns=window_end_ns,
                metric_name=samples[0].name,
            )
            if isinstance(sample, HistogramSample)
        ]

    grouped: dict[
        tuple[tuple[tuple[str, str, MetricAttribute], ...], int],
        list[HistogramSample],
    ] = defaultdict(list)
    for sample in samples:
        if sample.observed_at_ns <= window_end_ns:
            grouped[(_series_key(sample.attributes), sample.start_time_ns)].append(sample)

    contributions: list[HistogramSample] = []
    for series in grouped.values():
        contribution = _cumulative_window_sample(series, window_start_ns)
        if contribution is not None:
            contributions.append(contribution)
    return contributions


def _merge_histograms(samples: Sequence[HistogramSample]) -> HistogramSample:
    if not samples:
        raise MetricInsufficientData("no histogram events in evaluation window")
    names = {sample.name for sample in samples}
    units = {sample.unit for sample in samples}
    if len(names) != 1 or len(units) != 1:
        raise MetricAggregationError("incompatible histogram names or units")
    bounds = samples[0].explicit_bounds
    if any(sample.explicit_bounds != bounds for sample in samples[1:]):
        raise MetricAggregationError("incompatible histogram bucket boundaries")
    bucket_counts = tuple(
        sum(sample.bucket_counts[index] for sample in samples) for index in range(len(bounds) + 1)
    )
    sums = [sample.sum for sample in samples if sample.count]
    minima = [sample.min for sample in samples if sample.count]
    maxima = [sample.max for sample in samples if sample.count]
    return HistogramSample(
        name=samples[0].name,
        unit=samples[0].unit,
        observed_at_ns=max(sample.observed_at_ns for sample in samples),
        count=sum(sample.count for sample in samples),
        bucket_counts=bucket_counts,
        explicit_bounds=bounds,
        attributes={},
        temporality="delta",
        sum=sum(value for value in sums if value is not None)
        if all(value is not None for value in sums)
        else None,
        min=min(value for value in minima if value is not None)
        if minima and all(value is not None for value in minima)
        else None,
        max=max(value for value in maxima if value is not None)
        if maxima and all(value is not None for value in maxima)
        else None,
    )


def histogram_window_aggregate(
    samples: Sequence[HistogramSample],
    *,
    window_start_ns: int,
    window_end_ns: int,
) -> HistogramSample:
    """Merge each contribution once and verify the intervals actually counted."""
    contributions = _histogram_contributions(
        samples, window_start_ns=window_start_ns, window_end_ns=window_end_ns
    )
    merged = _merge_histograms(contributions)
    try:
        require_window_coverage(
            _interval_coverage(contributions),
            metric_name=merged.name,
            temporality=samples[0].temporality,
            window_start_ns=window_start_ns,
            window_end_ns=window_end_ns,
        )
    except MetricAggregationError as error:
        raise MetricInsufficientData(str(error)) from error
    return merged


def histogram_statistic(
    histogram: HistogramSample, aggregation: str, *, nonnegative: bool = False
) -> Estimate:
    """Return a bound; absence of events or a recorded sum is insufficient data."""
    if aggregation != "count" and histogram.count == 0:
        raise MetricInsufficientData("histogram has no recorded events")
    if aggregation == "mean" and histogram.sum is None:
        raise MetricInsufficientData("histogram mean requires a recorded sum")
    try:
        return estimate_statistic(histogram, aggregation, nonnegative=nonnegative)
    except ValueError as error:
        raise MetricAggregationError(str(error)) from error


def aggregate_metric_points(
    samples: Sequence[MetricPoint],
    aggregation: str,
    *,
    window_start_ns: int,
    window_end_ns: int,
) -> float | int:
    """Aggregate scalar or explicit-bucket points without expanding histogram events."""

    if not samples:
        raise MetricAggregationError("no metric samples")
    if all(isinstance(sample, MetricSample) for sample in samples):
        window = _matching_window(
            samples,
            window_start_ns=window_start_ns,
            window_end_ns=window_end_ns,
        )
        if not window:
            raise MetricAggregationError("no scalar samples in evaluation window")
        if (
            len({sample.instrument_kind for sample in window if isinstance(sample, MetricSample)})
            != 1
        ):
            raise MetricAggregationError("mixed scalar metric instrument kinds")
        if any(
            sample.instrument_kind == "sum" for sample in window if isinstance(sample, MetricSample)
        ):
            raise MetricAggregationError(
                "OTLP Sum cannot use generic scalar aggregation; "
                "evaluate its temporality-aware counter delta instead"
            )
        return _aggregate(
            aggregation,
            [sample.value for sample in window if isinstance(sample, MetricSample)],
        )
    if not all(isinstance(sample, HistogramSample) for sample in samples):
        raise MetricAggregationError("mixed scalar and histogram points")

    histograms = [sample for sample in samples if isinstance(sample, HistogramSample)]
    merged = histogram_window_aggregate(
        histograms,
        window_start_ns=window_start_ns,
        window_end_ns=window_end_ns,
    )
    estimate = histogram_statistic(merged, aggregation)
    if estimate.lower != estimate.upper:
        raise MetricInsufficientData(f"{aggregation} is only bounded by {estimate.describe()}")
    return estimate.lower


def counter_window_aggregate(
    samples: Sequence[MetricPoint],
    metric_name: str,
    *,
    attribute_match: Mapping[str, MetricAttribute],
    expected_unit: str,
    window_start_ns: int,
    window_end_ns: int,
) -> CounterWindowAggregate:
    """Return a monotonic Sum increase and the exact intervals that produced it."""

    matching = [
        sample
        for sample in samples
        if sample.name == metric_name
        and all(sample.attributes.get(key) == value for key, value in attribute_match.items())
    ]
    if not matching:
        raise MetricAggregationError(f"no counter points for {metric_name}")
    units = {sample.unit for sample in matching}
    if units != {expected_unit}:
        raise MetricAggregationError(
            f"{metric_name} requires unit {expected_unit}; observed {sorted(units)}"
        )
    if not all(
        isinstance(sample, MetricSample) and sample.instrument_kind == "sum" and sample.monotonic
        for sample in matching
    ):
        raise MetricAggregationError(f"{metric_name} must be a monotonic OTLP Sum")
    counters = [sample for sample in matching if isinstance(sample, MetricSample)]
    if any(sample.value < 0 for sample in counters):
        raise MetricAggregationError(f"{metric_name} contains a negative counter value")
    temporalities = {sample.temporality for sample in counters}
    if len(temporalities) != 1:
        raise MetricAggregationError(f"{metric_name} mixes aggregation temporalities")
    temporality = next(iter(temporalities))
    if temporality in {None, "unspecified"}:
        raise MetricAggregationError(f"{metric_name} has unspecified aggregation temporality")
    if temporality == "delta":
        points = [
            sample
            for sample in _validated_delta_points(
                counters,
                window_start_ns=window_start_ns,
                window_end_ns=window_end_ns,
                metric_name=metric_name,
            )
            if isinstance(sample, MetricSample)
        ]
        if not points:
            raise MetricAggregationError(
                f"{metric_name} has no delta points in the evaluation window"
            )
        if any(sample.value < 0 for sample in points):
            raise MetricAggregationError(f"{metric_name} contains a negative delta")
        delta_coverage = _interval_coverage(points)
        return CounterWindowAggregate(
            total=sum(sample.value for sample in points),
            coverage=delta_coverage,
            temporality=temporality,
        )

    grouped: dict[
        tuple[MetricSeriesKey, int],
        list[MetricSample],
    ] = defaultdict(list)
    for sample in counters:
        if sample.observed_at_ns <= window_end_ns:
            grouped[(_series_key(sample.attributes), sample.start_time_ns)].append(sample)
    total = 0.0
    observed_series = 0
    cumulative_coverage: list[tuple[MetricSeriesKey, int, int]] = []
    for (series_key, _), series in grouped.items():
        ordered = sorted(series, key=lambda sample: sample.observed_at_ns)
        for previous, current in pairwise(ordered):
            if current.observed_at_ns == previous.observed_at_ns:
                raise MetricAggregationError(
                    f"{metric_name} contains duplicate cumulative observations"
                )
            if current.value < previous.value:
                raise MetricAggregationError(f"{metric_name} cumulative value moved backwards")
        latest = ordered[-1]
        if latest.observed_at_ns < window_start_ns:
            continue
        if latest.start_time_ns >= window_start_ns:
            increase = latest.value
            interval_start_ns = latest.start_time_ns
        else:
            baselines = [
                sample
                for sample in ordered
                if sample.start_time_ns == latest.start_time_ns
                and sample.observed_at_ns <= window_start_ns
                and sample.observed_at_ns < latest.observed_at_ns
            ]
            if not baselines:
                raise MetricAggregationError(
                    f"{metric_name} has no cumulative baseline at the evaluation-window start"
                )
            baseline = baselines[-1]
            increase = latest.value - baseline.value
            interval_start_ns = baseline.observed_at_ns
        if increase < 0:
            raise MetricAggregationError(f"{metric_name} cumulative value moved backwards")
        if interval_start_ns >= latest.observed_at_ns:
            raise MetricAggregationError(
                f"{metric_name} contains an empty or reversed cumulative interval"
            )
        total += increase
        cumulative_coverage.append((series_key, interval_start_ns, latest.observed_at_ns))
        observed_series += 1
    if observed_series == 0:
        raise MetricAggregationError(
            f"{metric_name} has no cumulative points in the evaluation window"
        )
    ordered_coverage = tuple(sorted(cumulative_coverage))
    by_series: dict[MetricSeriesKey, list[tuple[int, int]]] = defaultdict(list)
    for series_key, start_ns, end_ns in ordered_coverage:
        by_series[series_key].append((start_ns, end_ns))
    for intervals in by_series.values():
        previous_end_ns: int | None = None
        for start_ns, end_ns in intervals:
            if previous_end_ns is not None and start_ns < previous_end_ns:
                raise MetricAggregationError(
                    f"{metric_name} contains overlapping cumulative intervals"
                )
            previous_end_ns = end_ns
    return CounterWindowAggregate(total=total, coverage=ordered_coverage, temporality=temporality)


def _compare(operator: str, observed: float | int, threshold: float) -> bool:
    comparisons = {
        "lt": observed < threshold,
        "lte": observed <= threshold,
        "eq": observed == threshold,
        "gte": observed >= threshold,
        "gt": observed > threshold,
    }
    return comparisons[operator]


def _histogram_assertion(
    assertion: Mapping[str, Any],
    samples: Sequence[HistogramSample],
    *,
    window_start_ns: int,
    window_end_ns: int,
) -> AssertionEvaluation:
    merged = histogram_window_aggregate(
        samples,
        window_start_ns=window_start_ns,
        window_end_ns=window_end_ns,
    )
    estimate = histogram_statistic(merged, assertion["aggregation"])
    operator = assertion["operator"]
    status = estimate.compare(operator, assertion["threshold"])
    displayed_bound = estimate.lower if operator in {"gt", "gte"} else estimate.upper
    observed = displayed_bound if math.isfinite(displayed_bound) and status != "skipped" else None
    return AssertionEvaluation(
        assertion_id=assertion["assertion_id"],
        status=status,
        observed_value=observed,
        unit=assertion["unit"],
        message=(
            f"{assertion['aggregation']} bound {estimate.describe()}; threshold "
            f"{operator} {assertion['threshold']}"
        ),
    )


def validate_metric_definitions(
    definitions: Sequence[Mapping[str, Any]],
    samples: Sequence[MetricPoint],
) -> None:
    """Fail before assertion evaluation when OTLP instrument identity has drifted."""

    grouped: dict[str, list[MetricPoint]] = defaultdict(list)
    for sample in samples:
        grouped[sample.name].append(sample)
    for definition in definitions:
        name = str(definition["metric_name"])
        observed = grouped.get(name, [])
        if not observed:
            continue
        units = {sample.unit for sample in observed}
        if units != {definition["unit"]}:
            raise MetricDefinitionError(
                f"declared metric {name!r} expects unit {definition['unit']!r}; "
                f"observed {sorted(units)}"
            )
        kinds = {
            "histogram" if isinstance(sample, HistogramSample) else sample.instrument_kind
            for sample in observed
        }
        if kinds != {definition["instrument_kind"]}:
            raise MetricDefinitionError(
                f"declared metric {name!r} expects {definition['instrument_kind']}; "
                f"observed {sorted(kinds)}"
            )
        temporalities = {
            (
                sample.temporality
                if isinstance(sample, HistogramSample) or sample.instrument_kind == "sum"
                else "instantaneous"
            )
            for sample in observed
        }
        if temporalities != {definition["temporality"]}:
            raise MetricDefinitionError(
                f"declared metric {name!r} expects temporality "
                f"{definition['temporality']!r}; observed "
                f"{sorted(str(item) for item in temporalities)}"
            )
        if definition.get("monotonic", False) and not all(
            isinstance(sample, MetricSample)
            and sample.instrument_kind == "sum"
            and sample.monotonic
            for sample in observed
        ):
            raise MetricDefinitionError(f"declared metric {name!r} is not monotonic")


def _duration_evaluation(
    assertion: Mapping[str, Any],
    samples: Sequence[MetricPoint],
    *,
    window_start_ns: int,
    window_end_ns: int,
) -> tuple[float, bool]:
    gauges = sorted(
        (
            sample
            for sample in samples
            if isinstance(sample, MetricSample) and sample.instrument_kind == "gauge"
        ),
        key=lambda sample: sample.observed_at_ns,
    )
    if len(gauges) != len(samples):
        raise MetricAggregationError("duration predicates require gauge samples")
    series = {_series_key(sample.attributes) for sample in gauges}
    if len(series) != 1:
        raise MetricAggregationError(
            "duration predicate requires exactly one attribute series; narrow attribute_match"
        )
    max_gap_ns = int(float(assertion["max_sample_gap_sec"]) * 1_000_000_000)
    timestamps = [sample.observed_at_ns for sample in gauges]
    coverage_gaps = [
        gap
        for gap in (
            timestamps[0] - window_start_ns,
            *(right - left for left, right in pairwise(timestamps)),
            window_end_ns - timestamps[-1],
        )
        if gap > max_gap_ns
    ]
    if coverage_gaps:
        raise MetricAggregationError(
            "duration predicate has an uncovered sample gap of "
            f"{max(coverage_gaps) / 1_000_000_000:.6g}s"
        )

    longest_true_ns = 0
    longest_false_ns = 0
    current_value: bool | None = None
    current_duration_ns = 0
    for index, sample in enumerate(gauges):
        segment_start = max(sample.observed_at_ns, window_start_ns)
        segment_end = (
            min(gauges[index + 1].observed_at_ns, window_end_ns)
            if index + 1 < len(gauges)
            else window_end_ns
        )
        if segment_end <= segment_start:
            continue
        value = _compare(assertion["operator"], sample.value, assertion["threshold"])
        if value != current_value:
            current_value = value
            current_duration_ns = 0
        current_duration_ns += segment_end - segment_start
        if value:
            longest_true_ns = max(longest_true_ns, current_duration_ns)
        else:
            longest_false_ns = max(longest_false_ns, current_duration_ns)

    requirement = assertion["duration_requirement"]
    threshold_sec = float(requirement["duration_sec"])
    if requirement["kind"] == "minimum_contiguous":
        observed_sec = longest_true_ns / 1_000_000_000
        return observed_sec, observed_sec >= threshold_sec
    observed_sec = longest_false_ns / 1_000_000_000
    return observed_sec, observed_sec <= threshold_sec


def evaluate_metric_assertions(
    assertions: Sequence[Mapping[str, Any]],
    samples: Sequence[MetricPoint],
    *,
    window_start_ns: int | None = None,
    window_end_ns: int | None = None,
) -> tuple[AssertionEvaluation, ...]:
    """Evaluate contract metric assertions against canonical metric samples."""

    if (window_start_ns is None) != (window_end_ns is None):
        raise HarnessInputError("metric evaluation window requires both start and end")
    if (
        window_start_ns is not None
        and window_end_ns is not None
        and window_end_ns < window_start_ns
    ):
        raise HarnessInputError("metric evaluation window ends before it starts")

    grouped: dict[str, list[MetricPoint]] = defaultdict(list)
    for sample in samples:
        grouped[sample.name].append(sample)

    evaluations: list[AssertionEvaluation] = []
    for assertion in assertions:
        assertion_id = assertion["assertion_id"]
        metric_name = assertion["metric_name"]
        attribute_match = assertion.get("attribute_match", {})
        metric_samples = [
            sample
            for sample in grouped.get(metric_name, [])
            if all(sample.attributes.get(key) == value for key, value in attribute_match.items())
        ]
        if not metric_samples:
            evaluations.append(
                AssertionEvaluation(
                    assertion_id=assertion_id,
                    status="error",
                    observed_value=None,
                    unit=assertion["unit"],
                    message=(
                        f"no samples for {metric_name} matching "
                        f"{dict(sorted(attribute_match.items()))}"
                    ),
                )
            )
            continue

        end_ns = (
            window_end_ns
            if window_end_ns is not None
            else max(sample.observed_at_ns for sample in metric_samples)
        )
        start_ns = end_ns - int(float(assertion["window_sec"]) * 1_000_000_000)
        if window_start_ns is not None:
            start_ns = max(start_ns, window_start_ns)
        window = [
            sample for sample in metric_samples if start_ns <= sample.observed_at_ns <= end_ns
        ]
        if not window:
            evaluations.append(
                AssertionEvaluation(
                    assertion_id=assertion_id,
                    status="error",
                    observed_value=None,
                    unit=assertion["unit"],
                    message=(
                        f"no samples for {metric_name} in evaluation window [{start_ns}, {end_ns}]"
                    ),
                )
            )
            continue
        units = {sample.unit for sample in window}
        if units != {assertion["unit"]}:
            evaluations.append(
                AssertionEvaluation(
                    assertion_id=assertion_id,
                    status="error",
                    observed_value=None,
                    unit=assertion["unit"],
                    message=f"expected unit {assertion['unit']}; observed {sorted(units)}",
                )
            )
            continue

        try:
            if assertion.get("kind") == "metric_duration":
                observed, passed = _duration_evaluation(
                    assertion,
                    window,
                    window_start_ns=start_ns,
                    window_end_ns=end_ns,
                )
                requirement = assertion["duration_requirement"]
                message = "" if passed else f"{requirement['kind']} {requirement['duration_sec']}s"
                evaluations.append(
                    AssertionEvaluation(
                        assertion_id=assertion_id,
                        status="passed" if passed else "failed",
                        observed_value=observed,
                        unit="s",
                        message=message,
                    )
                )
                continue
            if all(isinstance(sample, HistogramSample) for sample in metric_samples):
                evaluations.append(
                    _histogram_assertion(
                        assertion,
                        [
                            sample
                            for sample in metric_samples
                            if isinstance(sample, HistogramSample)
                        ],
                        window_start_ns=start_ns,
                        window_end_ns=end_ns,
                    )
                )
                continue
            observed = aggregate_metric_points(
                metric_samples,
                assertion["aggregation"],
                window_start_ns=start_ns,
                window_end_ns=end_ns,
            )
            passed = _compare(assertion["operator"], observed, assertion["threshold"])
        except MetricAggregationError as error:
            evaluations.append(
                AssertionEvaluation(
                    assertion_id=assertion_id,
                    status="skipped" if isinstance(error, MetricInsufficientData) else "error",
                    observed_value=None,
                    unit=assertion["unit"],
                    message=str(error),
                )
            )
            continue
        message = "" if passed else f"threshold {assertion['operator']} {assertion['threshold']}"
        evaluations.append(
            AssertionEvaluation(
                assertion_id=assertion_id,
                status="passed" if passed else "failed",
                observed_value=observed,
                unit=assertion["unit"],
                message=message,
            )
        )
    return tuple(evaluations)
