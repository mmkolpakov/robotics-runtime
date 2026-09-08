from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from math import isfinite
from typing import Any

from robotics_acceptance_harness.readiness import ReadinessIssue

_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def utc_datetime_from_unix_ns(timestamp_ns: int) -> datetime:
    """Convert an integer Unix timestamp without passing through a float."""

    seconds, nanoseconds = divmod(timestamp_ns, 1_000_000_000)
    return _UNIX_EPOCH + timedelta(seconds=seconds, microseconds=nanoseconds // 1_000)


class TimingValidationError(ValueError):
    """Raised when observed clock behavior violates the selected time policy."""

    def __init__(
        self,
        issues: tuple[ReadinessIssue, ...],
        observation: TimingObservation,
    ) -> None:
        self.issues = issues
        self.observation = observation
        super().__init__("; ".join(f"{issue.json_path}: {issue.message}" for issue in issues))


@dataclass(frozen=True, slots=True)
class ClockSample:
    observed_at_ns: int
    source_time_ns: int
    real_time_factor: float | None = None  # Per-sample diagnostic, not the policy window RTF.
    deadline_miss_ratio: float | None = None


@dataclass(frozen=True, slots=True)
class ClockMeasurementWindow:
    """Monotonic measurement bounds and an explicit callback coverage allowance.

    The 250 ms default applies to each boundary and every adjacent callback gap.
    It is an evidence-availability allowance, never permission to extrapolate
    source-clock progress or lower the configured minimum RTF.
    """

    start_ns: int
    end_ns: int
    max_sample_gap_ns: int = 250_000_000

    def __post_init__(self) -> None:
        if self.start_ns < 0 or self.end_ns <= self.start_ns:
            raise ValueError("clock measurement requires increasing nonnegative bounds")
        if self.max_sample_gap_ns <= 0:
            raise ValueError("clock sample gap allowance must be positive")


@dataclass(frozen=True, slots=True)
class TimingObservation:
    monotonic: bool
    offset_ms: float
    drift_ppm: float
    real_time_factor: float
    deadline_miss_ratio: float
    max_message_age_ms: float
    clock_hz: float


def _required_values(
    samples: Sequence[ClockSample],
    attribute: str,
    path: str,
    issues: list[ReadinessIssue],
) -> list[float]:
    values = [getattr(sample, attribute) for sample in samples]
    if any(value is None for value in values):
        issues.append(ReadinessIssue(path, f"{attribute} was not observed for every sample"))
        return []
    return [float(value) for value in values if value is not None]


def _clock_coverage(
    samples: Sequence[ClockSample], window: ClockMeasurementWindow, issues: list[ReadinessIssue]
) -> bool:
    first, last = samples[0].observed_at_ns, samples[-1].observed_at_ns
    if first < window.start_ns or last > window.end_ns:
        issues.append(
            ReadinessIssue("$.time_policy", "clock samples fall outside measurement bounds")
        )
        return False
    maximum = max(
        first - window.start_ns,
        window.end_ns - last,
        max(
            (b.observed_at_ns - a.observed_at_ns for a, b in pairwise(samples)),
            default=0,
        ),
    )
    if maximum > window.max_sample_gap_ns:
        issues.append(
            ReadinessIssue(
                "$.time_policy.min_realtime_factor",
                f"clock coverage gap {maximum} ns exceeds allowance {window.max_sample_gap_ns} ns",
            )
        )
        return False
    return True


def _interval_realtime_factor(samples: Sequence[ClockSample], start_ns: int, end_ns: int) -> float:
    """Lower bound from recorded endpoints at or inside the requested interval."""
    first = bisect_left(samples, start_ns, key=lambda sample: sample.observed_at_ns)
    last = bisect_right(samples, end_ns, key=lambda sample: sample.observed_at_ns) - 1
    if first >= last:
        return 0.0
    return (samples[last].source_time_ns - samples[first].source_time_ns) / (end_ns - start_ns)


def _measurement_realtime_factor(
    samples: Sequence[ClockSample], window: ClockMeasurementWindow, window_ns: int
) -> float:
    minimum = _interval_realtime_factor(samples, window.start_ns, window.end_ns)
    if window.end_ns - window.start_ns < window_ns:
        return max(0.0, minimum)
    # Include both measurement edges even if neither coincides with a callback.
    minimum = min(
        minimum,
        _interval_realtime_factor(samples, window.start_ns, window.start_ns + window_ns),
        _interval_realtime_factor(samples, window.end_ns - window_ns, window.end_ns),
    )
    left = 0
    for index, current in enumerate(samples):
        # Between callbacks the last observed source stays fixed while the left
        # endpoint can only advance. Check just before each new callback too:
        # a catch-up jump must not conceal the pause immediately preceding it.
        for end_ns, right in (
            (current.observed_at_ns - 1, index - 1),
            (current.observed_at_ns, index),
        ):
            start_ns = end_ns - window_ns
            if start_ns < window.start_ns:
                continue
            while samples[left].observed_at_ns < start_ns:
                left += 1
            progress = (
                0 if left >= right else samples[right].source_time_ns - samples[left].source_time_ns
            )
            minimum = min(minimum, progress / window_ns)
    return max(0.0, minimum)


def _windowed_realtime_factor(
    samples: Sequence[ClockSample],
    window_ns: int,
    issues: list[ReadinessIssue],
    measurement_window: ClockMeasurementWindow | None,
) -> float:
    """Take the worst integral or overlapping RTF with recorded endpoints.

    Explicit bounds require callback coverage and use conservative exact-length
    windows including the measurement edges. Without bounds, preserve the
    historical observed-span diagnostic: each callback ends a window whose
    first sample is at or before the requested boundary, at least window_ns
    apart. Neither mode interpolates source time; short spans use integral RTF.
    """

    if len(samples) < 2:
        issues.append(ReadinessIssue("$.time_policy.min_realtime_factor", "need two clock samples"))
        return 0.0
    if any(
        current.observed_at_ns <= previous.observed_at_ns for previous, current in pairwise(samples)
    ):
        issues.append(ReadinessIssue("$.time_policy", "clock observation times must increase"))
        return 0.0
    if measurement_window is not None:
        if not _clock_coverage(samples, measurement_window, issues):
            return 0.0
        return _measurement_realtime_factor(samples, measurement_window, window_ns)
    elapsed_ns = samples[-1].observed_at_ns - samples[0].observed_at_ns
    minimum = (samples[-1].source_time_ns - samples[0].source_time_ns) / elapsed_ns
    left = 0
    for index, current in enumerate(samples):
        boundary_ns = current.observed_at_ns - window_ns
        while left + 1 < index and samples[left + 1].observed_at_ns <= boundary_ns:
            left += 1
        previous = samples[left]
        duration_ns = current.observed_at_ns - previous.observed_at_ns
        if duration_ns >= window_ns:
            minimum = min(minimum, (current.source_time_ns - previous.source_time_ns) / duration_ns)
    return max(0.0, minimum)


def _evaluate_realtime(
    time_policy: Mapping[str, Any],
    samples: Sequence[ClockSample],
    issues: list[ReadinessIssue],
    window_ns: int,
    measurement_window: ClockMeasurementWindow | None,
) -> tuple[float, float]:
    real_time_factor = _windowed_realtime_factor(samples, window_ns, issues, measurement_window)
    deadline_values = _required_values(
        samples, "deadline_miss_ratio", "$.time_policy.max_deadline_miss_ratio", issues
    )
    if any(not isfinite(value) or not 0 <= value <= 1 for value in deadline_values):
        issues.append(
            ReadinessIssue(
                "$.time_policy.max_deadline_miss_ratio",
                "all deadline ratios must be finite and in [0, 1]; statistic unavailable",
            )
        )
        deadline_values = []
    deadline_miss_ratio = max(deadline_values, default=0.0)
    if real_time_factor < time_policy["min_realtime_factor"]:
        issues.append(
            ReadinessIssue(
                "$.time_policy.min_realtime_factor",
                f"minimum window or integral RTF was {real_time_factor}",
            )
        )
    if deadline_miss_ratio > time_policy["max_deadline_miss_ratio"]:
        issues.append(
            ReadinessIssue(
                "$.time_policy.max_deadline_miss_ratio",
                f"maximum observed value was {deadline_miss_ratio}",
            )
        )
    return real_time_factor, deadline_miss_ratio


def evaluate_timing(
    execution: Mapping[str, Any],
    time_policy: Mapping[str, Any],
    samples: Sequence[ClockSample],
    *,
    rtf_window_sec: float = 1.0,
    measurement_window: ClockMeasurementWindow | None = None,
) -> TimingObservation:
    """Evaluate timing; full measurement claims require explicit monotonic bounds.

    Without measurement_window, the low-level API evaluates only the supplied
    observed span, retaining its historical endpoint-based diagnostic behavior.
    Application verification always supplies the actual measurement window.
    """

    if not isfinite(rtf_window_sec) or rtf_window_sec < 1.0:
        raise ValueError("RTF window must be finite and at least one second")

    if not samples:
        observation = TimingObservation(False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        raise TimingValidationError(
            (ReadinessIssue("$.time_policy", "no clock samples"),),
            observation,
        )

    issues: list[ReadinessIssue] = []
    monotonic = all(
        current.source_time_ns >= previous.source_time_ns for previous, current in pairwise(samples)
    )
    if not monotonic:
        issues.append(ReadinessIssue("$.time_policy", "source clock moved backwards"))

    elapsed_ns = samples[-1].observed_at_ns - samples[0].observed_at_ns
    transitions = sum(
        current.source_time_ns != previous.source_time_ns for previous, current in pairwise(samples)
    )
    clock_hz = transitions * 1_000_000_000 / elapsed_ns if elapsed_ns > 0 else 0.0
    mode = execution["time_mode"]

    real_time_factor = 0.0
    deadline_miss_ratio = 0.0
    offset_ms = 0.0
    drift_ppm = 0.0
    max_message_age_ms = 0.0

    if mode == "simulation_realtime":
        real_time_factor, deadline_miss_ratio = _evaluate_realtime(
            time_policy, samples, issues, round(rtf_window_sec * 1_000_000_000), measurement_window
        )
    elif mode == "playback_clocked":
        if clock_hz < time_policy["min_clock_hz"]:
            issues.append(
                ReadinessIssue(
                    "$.time_policy.min_clock_hz",
                    f"observed clock frequency was {clock_hz}",
                )
            )
        if samples[-1].source_time_ns <= samples[0].source_time_ns:
            issues.append(ReadinessIssue("$.time_policy", "playback clock did not advance"))
    elif mode == "simulation_stepped":
        step_ns = round(float(time_policy["step_size_sec"]) * 1_000_000_000)
        max_skipped_steps = int(time_policy["max_skipped_steps"])
        step_transitions = [
            current
            for previous, current in pairwise(samples)
            if current.source_time_ns != previous.source_time_ns
        ]
        transition_sources = [samples[0], *step_transitions]
        deltas = [
            current.source_time_ns - previous.source_time_ns
            for previous, current in pairwise(transition_sources)
        ]
        if not deltas or samples[-1].source_time_ns <= samples[0].source_time_ns:
            issues.append(ReadinessIssue("$.time_policy", "stepped clock did not advance"))
        for index, delta in enumerate(deltas):
            if delta <= 0:
                issues.append(
                    ReadinessIssue(
                        "$.time_policy.step_size_sec",
                        f"sample {index + 1} did not advance by a positive step",
                    )
                )
                continue
            observed_steps = max(1, round(delta / step_ns))
            residual_ns = abs(delta - observed_steps * step_ns)
            if residual_ns > 1:
                issues.append(
                    ReadinessIssue(
                        "$.time_policy.step_size_sec",
                        f"sample {index + 1} delta {delta} ns is not a step multiple",
                    )
                )
            skipped_steps = observed_steps - 1
            if skipped_steps > max_skipped_steps:
                issues.append(
                    ReadinessIssue(
                        "$.time_policy.max_skipped_steps",
                        f"sample {index + 1} skipped {skipped_steps} steps",
                    )
                )
    observation = TimingObservation(
        monotonic=monotonic,
        offset_ms=offset_ms,
        drift_ppm=drift_ppm,
        real_time_factor=real_time_factor,
        deadline_miss_ratio=deadline_miss_ratio,
        max_message_age_ms=max_message_age_ms,
        clock_hz=clock_hz,
    )
    if issues:
        raise TimingValidationError(tuple(issues), observation)
    return observation
