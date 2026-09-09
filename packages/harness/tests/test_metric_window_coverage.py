from __future__ import annotations

import pytest

from robotics_acceptance_harness.metrics import (
    MetricAggregationError,
    MetricIntervalCoverage,
    MetricSeriesKey,
    MetricTemporality,
    require_window_coverage,
)

SECOND_NS = 1_000_000_000


def _coverage(
    intervals: tuple[tuple[int, int], ...], series: MetricSeriesKey = ()
) -> MetricIntervalCoverage:
    return tuple((series, start_ns, end_ns) for start_ns, end_ns in intervals)


@pytest.mark.parametrize("tolerance_ns", [SECOND_NS, 60 * SECOND_NS])
def test_rejects_58_missing_seconds_in_a_60_second_window(tolerance_ns: int) -> None:
    with pytest.raises(MetricAggregationError, match="does not cover enough"):
        require_window_coverage(
            _coverage(((0, SECOND_NS), (59 * SECOND_NS, 60 * SECOND_NS))),
            metric_name="latency",
            temporality="delta",
            window_start_ns=0,
            window_end_ns=60 * SECOND_NS,
            tolerance_ns=tolerance_ns,
        )


@pytest.mark.parametrize(
    ("window_ns", "tolerance_ns", "allowed_gap_ns"),
    [
        (60 * SECOND_NS, SECOND_NS, SECOND_NS),
        (10 * SECOND_NS, SECOND_NS, SECOND_NS // 2),
        (60 * SECOND_NS, SECOND_NS // 4, SECOND_NS // 4),
    ],
)
def test_interior_gap_accepts_exact_tolerance_but_rejects_one_ns_more(
    window_ns: int, tolerance_ns: int, allowed_gap_ns: int
) -> None:
    require_window_coverage(
        _coverage(((0, SECOND_NS), (SECOND_NS + allowed_gap_ns, window_ns))),
        metric_name="latency",
        temporality="delta",
        window_start_ns=0,
        window_end_ns=window_ns,
        tolerance_ns=tolerance_ns,
    )
    with pytest.raises(MetricAggregationError, match="does not cover enough"):
        require_window_coverage(
            _coverage(((0, SECOND_NS), (SECOND_NS + allowed_gap_ns + 1, window_ns))),
            metric_name="latency",
            temporality="delta",
            window_start_ns=0,
            window_end_ns=window_ns,
            tolerance_ns=tolerance_ns,
        )


def test_leading_interior_and_trailing_gaps_share_one_budget() -> None:
    intervals = ((200_000_000, 10 * SECOND_NS), (10_300_000_000, 20 * SECOND_NS))
    require_window_coverage(
        _coverage((*intervals, (20_300_000_000, 59_800_000_000))),
        metric_name="latency",
        temporality="delta",
        window_start_ns=0,
        window_end_ns=60 * SECOND_NS,
    )
    with pytest.raises(MetricAggregationError, match="does not cover enough"):
        require_window_coverage(
            _coverage((*intervals, (20_300_000_001, 59_800_000_000))),
            metric_name="latency",
            temporality="delta",
            window_start_ns=0,
            window_end_ns=60 * SECOND_NS,
        )


def test_multiple_small_interior_gaps_are_summed() -> None:
    with pytest.raises(MetricAggregationError, match="does not cover enough"):
        require_window_coverage(
            _coverage(
                (
                    (0, 10 * SECOND_NS),
                    (10_600_000_000, 20 * SECOND_NS),
                    (20_600_000_000, 60 * SECOND_NS),
                )
            ),
            metric_name="latency",
            temporality="delta",
            window_start_ns=0,
            window_end_ns=60 * SECOND_NS,
        )


@pytest.mark.parametrize("gap_series", ["camera", "lidar"])
def test_a_fully_covered_series_cannot_fill_another_series_gap(gap_series: str) -> None:
    coverage: MetricIntervalCoverage = ()
    for name in ("camera", "lidar"):
        intervals = (
            ((0, SECOND_NS), (59 * SECOND_NS, 60 * SECOND_NS))
            if name == gap_series
            else ((0, 60 * SECOND_NS),)
        )
        coverage += _coverage(intervals, (("sensor", "str", name),))
    with pytest.raises(MetricAggregationError, match="does not cover enough"):
        require_window_coverage(
            coverage,
            metric_name="latency",
            temporality="delta",
            window_start_ns=0,
            window_end_ns=60 * SECOND_NS,
        )


def test_each_series_has_its_own_uncovered_time_budget() -> None:
    intervals = ((0, SECOND_NS), (1_750_000_000, 60 * SECOND_NS))
    require_window_coverage(
        _coverage(intervals, (("sensor", "str", "camera"),))
        + _coverage(intervals, (("sensor", "str", "lidar"),)),
        metric_name="latency",
        temporality="delta",
        window_start_ns=0,
        window_end_ns=60 * SECOND_NS,
    )


@pytest.mark.parametrize("temporality", ["delta", "cumulative", "unspecified", None])
def test_unsorted_contiguous_intervals_need_no_tolerance(
    temporality: MetricTemporality | None,
) -> None:
    require_window_coverage(
        _coverage(((20, 60), (0, 10), (10, 20))),
        metric_name="latency",
        temporality=temporality,
        window_start_ns=0,
        window_end_ns=60,
        tolerance_ns=0,
    )


@pytest.mark.parametrize("temporality", ["cumulative", "unspecified", None])
def test_non_delta_interior_gaps_remain_strict(temporality: MetricTemporality | None) -> None:
    with pytest.raises(MetricAggregationError, match="gapped coverage intervals"):
        require_window_coverage(
            _coverage(((0, 30), (31, 60))),
            metric_name="latency",
            temporality=temporality,
            window_start_ns=0,
            window_end_ns=60,
        )


@pytest.mark.parametrize(
    "intervals",
    [((0, 0), (0, 60)), ((0, 60), (30, 30)), ((0, 60), (60, 60)), ((0, 60), (60, 59))],
)
def test_empty_or_reversed_intervals_cannot_supply_coverage(
    intervals: tuple[tuple[int, int], ...],
) -> None:
    with pytest.raises(MetricAggregationError, match="empty or reversed coverage intervals"):
        require_window_coverage(
            _coverage(intervals),
            metric_name="latency",
            temporality="delta",
            window_start_ns=0,
            window_end_ns=60,
        )


@pytest.mark.parametrize(
    "intervals", [((0, 40), (30, 60)), ((0, 60), (0, 60)), ((30, 60), (0, 40))]
)
def test_overlapping_or_duplicate_intervals_remain_invalid(
    intervals: tuple[tuple[int, int], ...],
) -> None:
    with pytest.raises(MetricAggregationError, match="overlapping coverage intervals"):
        require_window_coverage(
            _coverage(intervals),
            metric_name="latency",
            temporality="delta",
            window_start_ns=0,
            window_end_ns=60,
        )


@pytest.mark.parametrize(
    "intervals", [((-3, -2), (0, 30), (32, 60)), ((0, 30), (32, 60), (62, 63))]
)
def test_gaps_outside_the_window_do_not_consume_its_budget(
    intervals: tuple[tuple[int, int], ...],
) -> None:
    require_window_coverage(
        _coverage(intervals),
        metric_name="latency",
        temporality="delta",
        window_start_ns=0,
        window_end_ns=60,
    )


def test_empty_coverage_is_rejected() -> None:
    with pytest.raises(MetricAggregationError, match="no interval coverage"):
        require_window_coverage(
            (), metric_name="latency", temporality="delta", window_start_ns=0, window_end_ns=60
        )
