from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import pytest
from junitparser import JUnitXml

from robotics_acceptance_harness.metrics import (
    AssertionEvaluation,
    HistogramSample,
    MetricAggregationError,
    MetricInsufficientData,
    evaluate_metric_assertions,
    histogram_statistic,
    histogram_window_aggregate,
)
from robotics_acceptance_harness.otel import load_otlp_json_metrics
from robotics_acceptance_harness.result import build_acceptance_result, write_junit_xml
from robotics_acceptance_harness.time_authority import (
    DELIVERY_LATENCY_METRIC,
    METHOD_ATTRIBUTE,
    RMW_LATENCY_METHOD,
    TimeAuthorityObservation,
    evaluate_time_authority,
)
from tests.test_result import RUN_ID, result_inputs
from tests.test_time_authority import policy


@pytest.mark.parametrize("name", ["delta", "cumulative-baseline", "cumulative-reset"])
def test_golden_otlp_histograms_recover_the_same_window_distribution(name: str) -> None:
    points = load_otlp_json_metrics(
        Path(__file__).parent / "fixtures" / "histograms" / f"{name}.jsonl"
    )
    assert all(isinstance(sample, HistogramSample) for sample in points)
    merged = histogram_window_aggregate(
        [sample for sample in points if isinstance(sample, HistogramSample)],
        window_start_ns=10,
        window_end_ns=40,
    )
    assert merged.count == 30
    assert merged.bucket_counts == (15, 14, 1, 0)
    assert merged.sum == pytest.approx(20.4)
    for statistic, exact in (("min", 0.4), ("p50", 0.4), ("p95", 0.9), ("max", 1.8)):
        estimate = histogram_statistic(merged, statistic, nonnegative=True)
        assert estimate.lower <= exact <= estimate.upper


def point(values: list[float], observed: int, *, start: int = 0) -> HistogramSample:
    bounds = (0.5, 1.0, 2.0)
    counts = [0] * (len(bounds) + 1)
    for value in values:
        bucket = next((index for index, bound in enumerate(bounds) if value <= bound), len(bounds))
        counts[bucket] += 1
    return HistogramSample(
        name=DELIVERY_LATENCY_METRIC,
        unit="ms",
        observed_at_ns=observed,
        start_time_ns=start,
        temporality="cumulative",
        count=len(values),
        bucket_counts=tuple(counts),
        explicit_bounds=bounds,
        sum=sum(values),
        min=min(values) if values else None,
        max=max(values) if values else None,
        attributes={
            "run.id": RUN_ID,
            "domain.id": "camera-domain",
            "time.source.id": "simulation-clock",
            METHOD_ATTRIBUTE: RMW_LATENCY_METHOD,
        },
    )


def test_cumulative_baseline_preserves_window_buckets_and_discards_lifetime_extrema() -> None:
    history = [0.1, 100]
    events = [0.4] * 15 + [0.9] * 14 + [1.8]
    merged = histogram_window_aggregate(
        [point(history, 10), point(history + events, 40)], window_start_ns=10, window_end_ns=40
    )
    delta = point(events, 40, start=10)
    assert merged.count == delta.count == 30
    assert merged.bucket_counts == delta.bucket_counts
    assert merged.sum == pytest.approx(delta.sum)
    assert merged.min is None and merged.max is None
    for aggregation, value in (("p50", 0.4), ("p95", 0.9), ("min", 0.4), ("max", 1.8)):
        estimate = histogram_statistic(merged, aggregation, nonnegative=True)
        assert estimate.lower <= value <= estimate.upper
    assert histogram_statistic(merged, "mean").lower == pytest.approx(sum(events) / len(events))


def test_zero_baseline_retains_exact_extrema_even_without_recorded_baseline_sum() -> None:
    merged = histogram_window_aggregate(
        [replace(point([], 10), sum=None), point([0.1, 1.5], 40)],
        window_start_ns=10,
        window_end_ns=40,
    )
    assert (merged.count, merged.sum, merged.min, merged.max) == (2, 1.6, 0.1, 1.5)


def test_empty_delta_interval_does_not_erase_extrema() -> None:
    merged = histogram_window_aggregate(
        [
            replace(point([], 10), temporality="delta", sum=None),
            replace(point([0.1, 1.5], 40, start=10), temporality="delta"),
        ],
        window_start_ns=0,
        window_end_ns=40,
    )
    assert (merged.min, merged.max, merged.sum) == (0.1, 1.5, 1.6)


def test_unaligned_baseline_cannot_attribute_events_to_the_window() -> None:
    with pytest.raises(MetricInsufficientData, match="event times are unknown"):
        histogram_window_aggregate(
            [point([0.1], 9), point([0.1, 1.5], 40)], window_start_ns=10, window_end_ns=40
        )


def test_unchanged_point_across_boundary_proves_an_empty_prefix() -> None:
    merged = histogram_window_aggregate(
        [point([0.1], 9), point([0.1], 12), point([0.1, 1.5], 40)],
        window_start_ns=10,
        window_end_ns=40,
    )
    assert merged.count == 1
    assert merged.sum == pytest.approx(1.5)


def test_unmarked_reset_is_detected_even_if_last_count_recovers() -> None:
    with pytest.raises(MetricInsufficientData, match="reset has no new start"):
        histogram_window_aggregate(
            [point([0.1] * 4, 10), point([0.1], 20), point([0.1] * 7, 40)],
            window_start_ns=10,
            window_end_ns=40,
        )


def test_reset_start_is_never_inferred_from_an_observation_time() -> None:
    with pytest.raises(MetricInsufficientData, match="gapped coverage"):
        histogram_window_aggregate(
            [point([0.1], 10), point([0.5], 40, start=20)], window_start_ns=0, window_end_ns=40
        )


def test_declared_reset_preserves_adjacent_intervals() -> None:
    merged = histogram_window_aggregate(
        [point([0.1], 10), point([0.5], 40, start=10)], window_start_ns=0, window_end_ns=40
    )
    assert merged.count == 2
    assert merged.sum == pytest.approx(0.6)


def test_duplicate_cumulative_timestamp_is_malformed() -> None:
    with pytest.raises(MetricAggregationError, match="duplicate cumulative"):
        histogram_window_aggregate(
            [point([0.1], 10), point([0.1, 0.5], 10)], window_start_ns=0, window_end_ns=10
        )


@pytest.mark.parametrize(("threshold", "status"), [(2, "passed"), (1, "skipped"), (0.4, "failed")])
def test_missing_maximum_uses_a_bound_for_both_threshold_directions(
    threshold: float, status: str
) -> None:
    sample = replace(point([1.5], 40), temporality="delta", min=None, max=None)
    assertion = {
        "assertion_id": "bounded-max",
        "metric_name": sample.name,
        "unit": "ms",
        "aggregation": "max",
        "operator": "lte",
        "threshold": threshold,
        "window_sec": 1,
    }
    result = evaluate_metric_assertions([assertion], [sample], window_start_ns=0, window_end_ns=40)[
        0
    ]
    assert result.status == status
    assert "bound [1.0, 2.0]" in result.message


def time_observation(events: list[float]) -> TimeAuthorityObservation:
    history = [0.1, 100.0]
    return evaluate_time_authority(
        policy(),
        [point(history, 10), point(history + events, 40)],
        run_id=RUN_ID,
        domain_id="camera-domain",
        source_id="simulation-clock",
        window_start_ns=10,
        window_end_ns=40,
    )


def test_time_authority_uses_cumulative_baseline_and_window_count() -> None:
    observation = time_observation([0.4] * 15 + [0.9] * 14 + [1.8])
    assert observation.sample_count == 30
    assert observation.within_policy
    assert (observation.p50_ms, observation.p95_ms, observation.max_ms) == (0.5, 1.0, 2.0)
    assert observation.evaluation is not None
    assert "bound" in observation.evaluation.message


def test_overflow_uncertainty_keeps_count_and_builds_incomplete_result(tmp_path: Path) -> None:
    observation = time_observation([0.4] * 29 + [3.0])
    assert observation.sample_count == 30
    assert observation.evaluation is not None and observation.evaluation.status == "skipped"
    assert "[2.0, inf]" in observation.evaluation.message
    assert all(
        math.isfinite(value)
        for value in (observation.p50_ms, observation.p95_ms, observation.max_ms)
    )
    inputs = result_inputs(tmp_path)
    inputs["time_authority"] = observation
    result = build_acceptance_result(**inputs)
    assert result["status"] == "incomplete"
    assert result["time_authority_observation"]["sample_count"] == 30
    assert "$.time_authority_observation" in result["unevaluated"]
    junit = JUnitXml.fromfile(str(write_junit_xml(result, tmp_path / "result.xml")))
    assert junit.failures == 0 and junit.errors == 0 and junit.skipped >= 1


def test_empty_but_covered_histogram_proves_sample_count_failure() -> None:
    observation = evaluate_time_authority(
        policy(),
        [point([], 40)],
        run_id=RUN_ID,
        domain_id="camera-domain",
        source_id="simulation-clock",
        window_start_ns=0,
        window_end_ns=40,
    )
    assert observation.sample_count == 0
    assert observation.evaluation is not None and observation.evaluation.status == "failed"
    assert "count 0 < 30" in observation.evaluation.message


def test_absent_evidence_is_not_a_zero_measurement() -> None:
    observation = evaluate_time_authority(
        policy(),
        [],
        run_id=RUN_ID,
        domain_id="camera-domain",
        source_id="simulation-clock",
        window_start_ns=0,
        window_end_ns=40,
    )
    assert observation.evaluation is not None and observation.evaluation.status == "skipped"
    assert observation.evaluation.observed_value is None
    assert "placeholders" in observation.evaluation.message


def test_diagnostic_identifier_preserves_existing_assertions(tmp_path: Path) -> None:
    inputs = result_inputs(tmp_path)
    inputs["time_authority"] = time_observation([0.4] * 30)
    inputs["assertions"] = (
        AssertionEvaluation("time-authority-evidence", "passed", 1, "1"),
        AssertionEvaluation("time-authority-evidence-2", "passed", 2, "1"),
    )
    result = build_acceptance_result(**inputs)
    assert result["status"] == "passed"
    results = result["assertion_results"]
    assert [item["assertion_id"] for item in results] == [
        "time-authority-evidence",
        "time-authority-evidence-2",
        "time-authority-evidence-3",
    ]
    assert results[0]["observed_value"] == 1 and results[1]["observed_value"] == 2
