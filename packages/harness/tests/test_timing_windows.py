from __future__ import annotations

from collections.abc import Sequence

import pytest

from robotics_acceptance_harness.timing import (
    ClockSample,
    TimingObservation,
    TimingValidationError,
    evaluate_timing,
)

SECOND = 1_000_000_000


def realtime(samples: Sequence[ClockSample], window_sec: float = 1.0) -> TimingObservation:
    return evaluate_timing(
        {"time_mode": "simulation_realtime"},
        {"min_realtime_factor": 0.8, "max_deadline_miss_ratio": 0.01},
        samples,
        rtf_window_sec=window_sec,
    )


def test_callback_jitter_does_not_become_a_sustained_rtf_failure() -> None:
    samples = [
        ClockSample(
            index * 10_000_000 + (3_000_000 if index == 100 else 0),
            index * 10_000_000,
            real_time_factor=0.7,  # Per-callback diagnostics must not decide the window policy.
            deadline_miss_ratio=0,
        )
        for index in range(301)
    ]

    observation = realtime(samples)

    assert observation.real_time_factor == pytest.approx(1 / 1.003)
    assert observation.monotonic


def test_integral_rtf_replaces_startup_prefixes_for_short_recordings() -> None:
    samples = [
        ClockSample(wall, source, deadline_miss_ratio=0)
        for wall, source in (
            (0, 0),
            (10_000_000, 10_000_000),
            (23_000_000, 20_000_000),
            (30_000_000, 30_000_000),
        )
    ]

    assert realtime(samples).real_time_factor == 1


def test_integral_rtf_still_rejects_short_slow_recordings() -> None:
    samples = [
        ClockSample(0, 0, deadline_miss_ratio=0),
        ClockSample(100_000_000, 50_000_000, deadline_miss_ratio=0),
    ]

    with pytest.raises(TimingValidationError) as caught:
        realtime(samples)

    assert caught.value.observation.real_time_factor == 0.5


def test_sustained_slowdown_survives_later_catch_up() -> None:
    samples = [
        ClockSample(
            wall,
            wall
            - min(max(wall - SECOND, 0), SECOND) // 2
            + min(max(wall - 2 * SECOND, 0), SECOND) // 2,
            deadline_miss_ratio=0,
        )
        for wall in range(0, 4 * SECOND + 1, 10_000_000)
    ]
    assert samples[-1].source_time_ns == samples[-1].observed_at_ns

    with pytest.raises(TimingValidationError) as caught:
        realtime(samples)

    assert caught.value.observation.real_time_factor == 0.5
    assert {issue.json_path for issue in caught.value.issues} == {
        "$.time_policy.min_realtime_factor"
    }


def boundary_slowdown() -> tuple[ClockSample, ...]:
    # Slow from 0.75s to 1.25s, then recover the lost 0.4s between 2s and 3s.
    return tuple(
        ClockSample(
            wall,
            wall
            - 4 * min(max(wall - 750_000_000, 0), 500_000_000) // 5
            + 2 * min(max(wall - 2 * SECOND, 0), SECOND) // 5,
            deadline_miss_ratio=0,
        )
        for wall in range(0, 3 * SECOND + 1, 10_000_000)
    )


def test_sliding_windows_detect_a_slowdown_between_fixed_bucket_boundaries() -> None:
    samples = boundary_slowdown()
    assert samples[100].source_time_ns == 800_000_000
    assert samples[200].source_time_ns == 1_600_000_000
    assert samples[-1].source_time_ns == 3 * SECOND

    with pytest.raises(TimingValidationError) as caught:
        realtime(samples)

    assert caught.value.observation.real_time_factor == pytest.approx(0.6)


def test_larger_window_is_an_explicit_evaluation_parameter() -> None:
    assert realtime(boundary_slowdown(), window_sec=2).real_time_factor == pytest.approx(0.8)


@pytest.mark.parametrize("origin_ns", [0, 1_785_067_200_123_456_789])
def test_irregular_sample_spacing_and_large_clock_origins_preserve_constant_rate(
    origin_ns: int,
) -> None:
    samples = [
        ClockSample(origin_ns + offset, 4 * SECOND + offset * 9 // 10, deadline_miss_ratio=0)
        for offset in (0, 120_000_000, 510_000_000, 1_130_000_000, 2_250_000_000, 3 * SECOND)
    ]

    assert realtime(samples).real_time_factor == pytest.approx(0.9)


@pytest.mark.parametrize("times", [(0,), (0, 0), (10, 9)])
def test_rtf_requires_a_measurable_increasing_observation_interval(times: tuple[int, ...]) -> None:
    samples = [ClockSample(wall, index, deadline_miss_ratio=0) for index, wall in enumerate(times)]

    with pytest.raises(TimingValidationError) as caught:
        realtime(samples)

    assert caught.value.observation.real_time_factor == 0


@pytest.mark.parametrize("window_sec", [0, 0.5, float("nan"), float("inf")])
def test_window_cannot_reintroduce_per_callback_policy(window_sec: float) -> None:
    with pytest.raises(ValueError, match="at least one second"):
        realtime((), window_sec=window_sec)


def test_missing_deadline_evidence_does_not_pass_with_valid_rtf() -> None:
    with pytest.raises(TimingValidationError) as caught:
        realtime((ClockSample(0, 0), ClockSample(SECOND, SECOND)))

    assert caught.value.observation.real_time_factor == 1
    assert caught.value.issues[0].json_path == "$.time_policy.max_deadline_miss_ratio"
