from __future__ import annotations

from datetime import UTC, datetime
from math import nextafter
from random import Random

import pytest

from robotics_acceptance_harness.errors import HarnessError, HarnessInputError
from robotics_acceptance_harness.readiness import ReadinessIssue
from robotics_acceptance_harness.timing import (
    ClockMeasurementWindow,
    ClockSample,
    TimingObservation,
    TimingValidationError,
    _evaluate_timing,
    _measurement_realtime_factor,
    _measurement_realtime_factor_upper,
    _TimingEvaluation,
    evaluate_timing,
    utc_datetime_from_unix_ns,
)


def test_unix_nanoseconds_are_converted_without_float_rounding() -> None:
    assert utc_datetime_from_unix_ns(1_785_067_200_123_456_789) == datetime(
        2026,
        7,
        26,
        12,
        0,
        0,
        123456,
        tzinfo=UTC,
    )


def test_realtime_timing_passes_at_policy_boundary() -> None:
    samples = [
        ClockSample(0, 0, real_time_factor=0.95, deadline_miss_ratio=0.01),
        ClockSample(1_000_000_000, 950_000_000, real_time_factor=0.96, deadline_miss_ratio=0),
    ]
    result = evaluate_timing(
        {"time_mode": "simulation_realtime"},
        {"min_realtime_factor": 0.95, "max_deadline_miss_ratio": 0.01},
        samples,
    )
    assert result.real_time_factor == 0.95
    assert result.deadline_miss_ratio == 0.01


def test_backwards_clock_is_rejected_in_every_mode() -> None:
    samples = [ClockSample(0, 10), ClockSample(1, 9)]
    with pytest.raises(TimingValidationError, match="moved backwards"):
        evaluate_timing(
            {"time_mode": "simulation_stepped"},
            {"step_size_sec": 0.001, "max_skipped_steps": 0},
            samples,
        )


def test_stepped_timing_accepts_declared_multiples() -> None:
    samples = [
        ClockSample(0, 0),
        ClockSample(1_000_000, 1_000_000),
        ClockSample(2_000_000, 2_000_000),
    ]

    result = evaluate_timing(
        {"time_mode": "simulation_stepped"},
        {"step_size_sec": 0.001, "max_skipped_steps": 0},
        samples,
    )

    assert result.monotonic


def test_stepped_timing_ignores_repeated_clock_publications() -> None:
    samples = [
        ClockSample(0, 0),
        ClockSample(100_000, 0),
        ClockSample(1_000_000, 1_000_000),
        ClockSample(1_100_000, 1_000_000),
        ClockSample(2_000_000, 2_000_000),
    ]

    result = evaluate_timing(
        {"time_mode": "simulation_stepped"},
        {"step_size_sec": 0.001, "max_skipped_steps": 0},
        samples,
    )

    assert result.monotonic


def test_stepped_timing_rejects_clock_that_only_repeats() -> None:
    samples = [
        ClockSample(0, 1_000_000),
        ClockSample(1_000_000, 1_000_000),
    ]

    with pytest.raises(TimingValidationError, match="stepped clock did not advance"):
        evaluate_timing(
            {"time_mode": "simulation_stepped"},
            {"step_size_sec": 0.001, "max_skipped_steps": 0},
            samples,
        )


def test_stepped_timing_rejects_large_jump() -> None:
    samples = [
        ClockSample(0, 0),
        ClockSample(1_000_000, 999_000_000_000),
    ]

    with pytest.raises(TimingValidationError) as caught:
        evaluate_timing(
            {"time_mode": "simulation_stepped"},
            {"step_size_sec": 0.001, "max_skipped_steps": 0},
            samples,
        )

    assert caught.value.observation.monotonic
    assert any(
        issue.json_path == "$.time_policy.max_skipped_steps" for issue in caught.value.issues
    )


def test_realtime_policy_rejects_slow_or_late_execution() -> None:
    samples = [
        ClockSample(0, 0, real_time_factor=0.7, deadline_miss_ratio=0.1),
        ClockSample(1_000_000_000, 700_000_000, real_time_factor=0.8, deadline_miss_ratio=0.2),
    ]
    with pytest.raises(TimingValidationError) as caught:
        evaluate_timing(
            {"time_mode": "simulation_realtime"},
            {"min_realtime_factor": 0.95, "max_deadline_miss_ratio": 0.01},
            samples,
        )
    paths = {issue.json_path for issue in caught.value.issues}
    assert "$.time_policy.min_realtime_factor" in paths
    assert "$.time_policy.max_deadline_miss_ratio" in paths


def test_playback_requires_clock_progress_and_frequency() -> None:
    samples = [ClockSample(0, 0), ClockSample(2_000_000_000, 1_000_000_000)]
    with pytest.raises(TimingValidationError) as caught:
        evaluate_timing(
            {"time_mode": "playback_clocked"},
            {"min_clock_hz": 1.0},
            samples,
        )
    assert caught.value.issues[0].json_path == "$.time_policy.min_clock_hz"


@pytest.mark.parametrize("cadence_ns", [100_000_000, 50_000_000])
def test_thirty_second_constant_clock_bound_is_not_a_proven_failure(cadence_ns: int) -> None:
    samples = [
        ClockSample(
            wall + (3_000_000 if cadence_ns == 50_000_000 and wall == 10_000_000_000 else 0),
            wall,
            deadline_miss_ratio=0,
        )
        for wall in range(0, 30_000_000_000, cadence_ns)
    ]
    with pytest.raises(TimingValidationError) as caught:
        evaluate_timing(
            {"time_mode": "simulation_realtime"},
            {"min_realtime_factor": 0.95, "max_deadline_miss_ratio": 0.01},
            samples,
            measurement_window=ClockMeasurementWindow(0, 30_000_000_000),
        )
    assert not caught.value.failed
    assert caught.value.observation.real_time_factor == 0.9
    assert caught.value.unevaluated == ("$.clock_observation.real_time_factor",)
    assert "lower bound, not a measured violation" in str(caught.value)


@pytest.mark.parametrize("threshold", [0.8, nextafter(0.8, 1.0)])
def test_rtf_upper_bound_must_be_strictly_below_the_threshold_to_prove_failure(
    threshold: float,
) -> None:
    samples = [
        ClockSample(wall, wall * 4 // 5, deadline_miss_ratio=0)
        for wall in range(0, 3_000_000_001, 50_000_000)
    ]
    with pytest.raises(TimingValidationError) as caught:
        evaluate_timing(
            {"time_mode": "simulation_realtime"},
            {"min_realtime_factor": threshold, "max_deadline_miss_ratio": 0.01},
            samples,
            measurement_window=ClockMeasurementWindow(0, 3_000_000_000),
        )
    assert caught.value.failed == (threshold > 0.8)
    assert bool(caught.value.unevaluated) == (threshold == 0.8)


@pytest.mark.parametrize("deadline", [0.0, 0.5])
def test_independent_deadline_gauge_is_evaluated_without_clock_samples(deadline: float) -> None:
    with pytest.raises(TimingValidationError) as caught:
        evaluate_timing(
            {"time_mode": "simulation_realtime"},
            {"min_realtime_factor": 0.95, "max_deadline_miss_ratio": 0.01},
            (),
            measurement_window=ClockMeasurementWindow(
                0, 30_000_000_000, deadline_miss_ratio=deadline
            ),
        )
    assert caught.value.failed == (deadline > 0.01)
    assert caught.value.observation.deadline_miss_ratio == deadline
    assert caught.value.unevaluated == (
        "$.clock_observation.monotonic",
        "$.clock_observation.real_time_factor",
    )


@pytest.mark.parametrize("carried", [0.5, -0.1, float("nan")])
def test_window_deadline_gauge_cannot_hide_other_deadline_evidence(carried: float) -> None:
    samples = [
        ClockSample(wall, wall, deadline_miss_ratio=carried)
        for wall in range(0, 2_000_000_001, 50_000_000)
    ]
    with pytest.raises(TimingValidationError) as caught:
        evaluate_timing(
            {"time_mode": "simulation_realtime"},
            {"min_realtime_factor": 0.9, "max_deadline_miss_ratio": 0.01},
            samples,
            measurement_window=ClockMeasurementWindow(0, 2_000_000_000, deadline_miss_ratio=0),
        )
    assert caught.value.failed
    assert {issue.json_path for issue in caught.value.issues} == {
        "$.time_policy.max_deadline_miss_ratio"
    }


def test_missing_deadline_is_uncertain_but_cannot_hide_a_clock_violation() -> None:
    for source_end, failed in [(1_000_000_000, False), (0, True)]:
        with pytest.raises(TimingValidationError) as caught:
            evaluate_timing(
                {"time_mode": "simulation_realtime"},
                {"min_realtime_factor": 0.95, "max_deadline_miss_ratio": 0.01},
                (ClockSample(0, 0), ClockSample(1_000_000_000, source_end)),
            )
        assert caught.value.failed is failed
        assert caught.value.unevaluated == ("$.clock_observation.deadline_miss_ratio",)


@pytest.mark.parametrize("reported", [0.0, 0.5])
@pytest.mark.parametrize("missing_first", [False, True])
@pytest.mark.parametrize("bounded", [False, True])
def test_partial_deadline_samples_preserve_a_known_exceedance(
    reported: float, missing_first: bool, bounded: bool
) -> None:
    values = (None, reported) if missing_first else (reported, None)
    samples = tuple(
        ClockSample(index * 1_000_000_000, index * 1_000_000_000, deadline_miss_ratio=value)
        for index, value in enumerate(values)
    )
    window = (
        ClockMeasurementWindow(0, 1_000_000_000, max_sample_gap_ns=1_000_000_000)
        if bounded
        else None
    )
    with pytest.raises(TimingValidationError) as caught:
        evaluate_timing(
            {"time_mode": "simulation_realtime"},
            {"min_realtime_factor": 0.95, "max_deadline_miss_ratio": 0.01},
            samples,
            measurement_window=window,
        )
    assert caught.value.failed is (reported > 0.01)
    assert caught.value.observation.deadline_miss_ratio == reported
    assert caught.value.unevaluated == ("$.clock_observation.deadline_miss_ratio",)


def test_rtf_bounds_match_an_exhaustive_integer_window_oracle() -> None:
    random = Random(30017)
    for _ in range(600):
        origin = random.choice([0, 1_785_067_200_123_456_789])
        duration = random.randint(4, 60)
        width = random.randint(2, 70)
        times = sorted(random.sample(range(duration + 1), random.randint(2, min(20, duration + 1))))
        source = 500_000_000_000
        samples = []
        for time in times:
            source += random.randrange(31)
            samples.append(ClockSample(origin + time, source))
        window = ClockMeasurementWindow(origin, origin + duration)
        intervals = [(origin, origin + duration)] + [
            (origin + end - width, origin + end) for end in range(width, duration + 1)
        ]
        lowers, uppers = [], []
        for start, end in intervals:
            inside = [s.source_time_ns for s in samples if start <= s.observed_at_ns <= end]
            before = [s.source_time_ns for s in samples if s.observed_at_ns <= start]
            after = [s.source_time_ns for s in samples if s.observed_at_ns >= end]
            lowers.append((inside[-1] - inside[0]) / (end - start) if len(inside) >= 2 else 0.0)
            uppers.append(
                (after[0] - before[-1]) / (end - start) if before and after else float("inf")
            )
        assert _measurement_realtime_factor(samples, window, width) == min(lowers)
        assert _measurement_realtime_factor_upper(samples, window, width) == min(uppers)


def test_timing_result_pass_preserves_public_observation() -> None:
    execution = {"time_mode": "simulation_realtime"}
    policy = {"min_realtime_factor": 0.95, "max_deadline_miss_ratio": 0.01}
    samples = (
        ClockSample(0, 0, deadline_miss_ratio=0.01),
        ClockSample(1_000_000_000, 950_000_000, deadline_miss_ratio=0),
    )
    expected = TimingObservation(True, 0.0, 0.0, 0.95, 0.01, 0.0, 1.0)
    evaluation = _evaluate_timing(execution, policy, samples)
    assert type(evaluation) is _TimingEvaluation
    assert evaluation.observation == expected
    assert evaluation.violations == evaluation.insufficient == evaluation.issues == ()
    assert evaluation.unevaluated == ()
    assert evaluation.message == ""
    assert evaluate_timing(execution, policy, samples) == expected


@pytest.mark.parametrize(
    ("source_end", "expected", "violations", "failed", "message"),
    [
        pytest.param(
            1_000_000_000,
            TimingObservation(True, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0),
            (),
            False,
            "$.time_policy.max_deadline_miss_ratio: "
            "deadline_miss_ratio was not observed for every sample",
            id="insufficient",
        ),
        pytest.param(
            0,
            TimingObservation(True, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            (
                ReadinessIssue(
                    "$.time_policy.min_realtime_factor",
                    "minimum window or integral RTF is at most 0.0; recorded lower bound is 0.0",
                ),
            ),
            True,
            "$.time_policy.min_realtime_factor: minimum window or integral RTF is at most 0.0; "
            "recorded lower bound is 0.0; $.time_policy.max_deadline_miss_ratio: "
            "deadline_miss_ratio was not observed for every sample",
            id="mixed",
        ),
    ],
)
def test_timing_result_preserves_uncertainty_and_proven_failure(
    source_end: int,
    expected: TimingObservation,
    violations: tuple[ReadinessIssue, ...],
    failed: bool,
    message: str,
) -> None:
    execution = {"time_mode": "simulation_realtime"}
    policy = {"min_realtime_factor": 0.95, "max_deadline_miss_ratio": 0.01}
    samples = (ClockSample(0, 0), ClockSample(1_000_000_000, source_end))
    insufficient = (
        ReadinessIssue(
            "$.time_policy.max_deadline_miss_ratio",
            "deadline_miss_ratio was not observed for every sample",
        ),
    )
    evaluation = _evaluate_timing(execution, policy, samples)
    assert evaluation.observation == expected
    assert evaluation.violations == violations
    assert evaluation.insufficient == insufficient
    assert evaluation.unevaluated == ("$.clock_observation.deadline_miss_ratio",)
    assert evaluation.message == message
    with pytest.raises(TimingValidationError) as caught:
        evaluate_timing(execution, policy, samples)
    assert caught.value.observation == expected
    assert caught.value.issues == (*violations, *insufficient)
    assert caught.value.failed is failed
    assert caught.value.unevaluated == ("$.clock_observation.deadline_miss_ratio",)
    assert caught.value.args == (message,)


def test_timing_result_preserves_a_proven_step_violation() -> None:
    execution = {"time_mode": "simulation_stepped"}
    policy = {"step_size_sec": 0.001, "max_skipped_steps": 0}
    samples = (ClockSample(0, 0), ClockSample(1_000_000, 3_000_000))
    expected = TimingObservation(True, 0.0, 0.0, 0.0, 0.0, 0.0, 1000.0)
    issues = (ReadinessIssue("$.time_policy.max_skipped_steps", "sample 1 skipped 2 steps"),)
    evaluation = _evaluate_timing(execution, policy, samples)
    assert evaluation.observation == expected
    assert evaluation.violations == issues
    assert evaluation.insufficient == ()
    assert evaluation.unevaluated == ()
    with pytest.raises(TimingValidationError) as caught:
        evaluate_timing(execution, policy, samples)
    assert caught.value.observation == expected
    assert caught.value.issues == issues
    assert caught.value.failed is True
    assert caught.value.unevaluated == ()
    assert caught.value.args == ("$.time_policy.max_skipped_steps: sample 1 skipped 2 steps",)


@pytest.mark.parametrize("mode", ["playback_clocked", "simulation_stepped"])
def test_empty_non_realtime_result_preserves_early_failure(mode: str) -> None:
    expected = TimingObservation(False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    issues = (ReadinessIssue("$.time_policy", "no clock samples"),)
    evaluation = _evaluate_timing({"time_mode": mode}, {}, ())
    assert evaluation.observation == expected
    assert evaluation.violations == issues
    assert evaluation.insufficient == ()
    assert evaluation.unevaluated == ()
    with pytest.raises(TimingValidationError) as caught:
        evaluate_timing({"time_mode": mode}, {}, ())
    assert caught.value.observation == expected
    assert caught.value.issues == issues
    assert caught.value.failed is True
    assert caught.value.unevaluated == ()
    assert caught.value.args == ("$.time_policy: no clock samples",)


def test_empty_realtime_result_retains_independent_deadline_and_uncertainty() -> None:
    execution = {"time_mode": "simulation_realtime"}
    policy = {"min_realtime_factor": 0.95, "max_deadline_miss_ratio": 0.01}
    window = ClockMeasurementWindow(0, 30_000_000_000, deadline_miss_ratio=0)
    expected = TimingObservation(False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    insufficient = (
        ReadinessIssue(
            "$.clock_observation.monotonic", "no clock samples; monotonicity unavailable"
        ),
        ReadinessIssue("$.time_policy.min_realtime_factor", "need two clock samples"),
        ReadinessIssue(
            "$.time_policy.min_realtime_factor",
            "RTF bound [0.0, inf] does not determine whether the minimum 0.95 is met; "
            "numeric RTF is a lower bound, not a measured violation",
        ),
    )
    message = (
        "$.clock_observation.monotonic: no clock samples; monotonicity unavailable; "
        "$.time_policy.min_realtime_factor: need two clock samples; "
        "$.time_policy.min_realtime_factor: RTF bound [0.0, inf] does not determine whether "
        "the minimum 0.95 is met; numeric RTF is a lower bound, not a measured violation"
    )
    evaluation = _evaluate_timing(execution, policy, (), measurement_window=window)
    assert evaluation.observation == expected
    assert evaluation.violations == ()
    assert evaluation.insufficient == insufficient
    assert evaluation.message == message
    with pytest.raises(TimingValidationError) as caught:
        evaluate_timing(execution, policy, (), measurement_window=window)
    assert caught.value.failed is False
    assert caught.value.observation == expected
    assert caught.value.issues == insufficient
    assert caught.value.unevaluated == (
        "$.clock_observation.monotonic",
        "$.clock_observation.real_time_factor",
    )
    assert caught.value.args == (message,)


def test_timing_error_constructor_keeps_public_diagnostics_and_issue_order() -> None:
    observation = TimingObservation(False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    error = TimingValidationError(
        (ReadinessIssue("$.time_policy", "first"),),
        observation,
        insufficient_issues=(
            ReadinessIssue("$.time_policy.min_realtime_factor", "second"),
            ReadinessIssue("$.time_policy.max_deadline_miss_ratio", "third"),
            ReadinessIssue("$.time_policy.min_realtime_factor", "fourth"),
            ReadinessIssue("$.clock_observation.monotonic", "fifth"),
        ),
    )
    expected_message = (
        "$.time_policy: first; $.time_policy.min_realtime_factor: second; "
        "$.time_policy.max_deadline_miss_ratio: third; $.time_policy.min_realtime_factor: fourth; "
        "$.clock_observation.monotonic: fifth"
    )
    assert type(error) is TimingValidationError
    assert isinstance(error, HarnessError)
    assert isinstance(error, ValueError)
    assert error.error_id == "TimingValidationError.failed"
    assert error.failed is True
    assert error.observation is observation
    assert error.issues == (
        ReadinessIssue("$.time_policy", "first"),
        ReadinessIssue("$.time_policy.min_realtime_factor", "second"),
        ReadinessIssue("$.time_policy.max_deadline_miss_ratio", "third"),
        ReadinessIssue("$.time_policy.min_realtime_factor", "fourth"),
        ReadinessIssue("$.clock_observation.monotonic", "fifth"),
    )
    assert error.unevaluated == (
        "$.clock_observation.deadline_miss_ratio",
        "$.clock_observation.monotonic",
        "$.clock_observation.real_time_factor",
    )
    assert error.diagnostic_issues == (
        ("$.time_policy", "first"),
        ("$.time_policy.min_realtime_factor", "second"),
        ("$.time_policy.max_deadline_miss_ratio", "third"),
        ("$.time_policy.min_realtime_factor", "fourth"),
        ("$.clock_observation.monotonic", "fifth"),
    )
    assert str(error) == expected_message
    assert error.args == (expected_message,)


@pytest.mark.parametrize("window_sec", [0.5, float("nan"), float("inf")])
@pytest.mark.parametrize("internal", [False, True])
def test_invalid_rtf_window_remains_an_input_error(internal: bool, window_sec: float) -> None:
    evaluate = _evaluate_timing if internal else evaluate_timing
    with pytest.raises(HarnessInputError) as caught:
        evaluate({"time_mode": "simulation_realtime"}, {}, (), rtf_window_sec=window_sec)
    assert type(caught.value) is HarnessInputError
    assert caught.value.error_id == "input.invalid"
    assert caught.value.args == ("RTF window must be finite and at least one second",)
