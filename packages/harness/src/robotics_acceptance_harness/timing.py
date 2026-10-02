from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from math import isfinite
from typing import Any

from robotics_acceptance_harness.errors import HarnessError, HarnessInputError
from robotics_acceptance_harness.readiness import ReadinessIssue

_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def utc_datetime_from_unix_ns(timestamp_ns: int) -> datetime:
    """Convert an integer Unix timestamp without passing through a float."""

    seconds, nanoseconds = divmod(timestamp_ns, 1_000_000_000)
    return _UNIX_EPOCH + timedelta(seconds=seconds, microseconds=nanoseconds // 1_000)


class TimingValidationError(HarnessError, ValueError):
    """Carry proven violations separately from unavailable timing conclusions."""

    error_id = "TimingValidationError.failed"

    def __init__(
        self,
        issues: tuple[ReadinessIssue, ...],
        observation: TimingObservation,
        *,
        insufficient_issues: tuple[ReadinessIssue, ...] = (),
    ) -> None:
        self.failed = bool(issues)
        self.issues = (*issues, *insufficient_issues)
        self.observation = observation
        fields = {
            "$.time_policy.min_realtime_factor": "$.clock_observation.real_time_factor",
            "$.time_policy.max_deadline_miss_ratio": "$.clock_observation.deadline_miss_ratio",
        }
        self.unevaluated = tuple(
            sorted({fields.get(issue.json_path, issue.json_path) for issue in insufficient_issues})
        )
        super().__init__("; ".join(f"{issue.json_path}: {issue.message}" for issue in self.issues))

    @property
    def diagnostic_issues(self) -> tuple[tuple[str, str], ...]:
        return tuple((issue.json_path, issue.message) for issue in self.issues)


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
    The optional deadline gauge is independent evidence for this same window,
    including when no clock callback arrived.
    """

    start_ns: int
    end_ns: int
    max_sample_gap_ns: int = 250_000_000
    deadline_miss_ratio: float | None = None

    def __post_init__(self) -> None:
        if self.start_ns < 0 or self.end_ns <= self.start_ns:
            raise HarnessInputError("clock measurement requires increasing nonnegative bounds")
        if self.max_sample_gap_ns <= 0:
            raise HarnessInputError("clock sample gap allowance must be positive")


@dataclass(frozen=True, slots=True)
class TimingObservation:
    monotonic: bool
    offset_ms: float
    drift_ppm: float
    real_time_factor: float
    deadline_miss_ratio: float
    max_message_age_ms: float
    clock_hz: float


@dataclass
class _TimingIssues:
    violations: list[ReadinessIssue] = field(default_factory=list)
    insufficient: list[ReadinessIssue] = field(default_factory=list)


def _required_values(
    samples: Sequence[ClockSample],
    attribute: str,
    path: str,
    issues: list[ReadinessIssue],
) -> list[float]:
    values = [getattr(sample, attribute) for sample in samples]
    if not values or any(value is None for value in values):
        issues.append(ReadinessIssue(path, f"{attribute} was not observed for every sample"))
    # Missing samples make the full statistic uncertain, but known values can
    # still prove a policy violation and must remain available to the evaluator.
    return [float(value) for value in values if value is not None]


def _clock_coverage(
    samples: Sequence[ClockSample],
    window: ClockMeasurementWindow,
    issues: _TimingIssues,
) -> bool:
    first, last = samples[0].observed_at_ns, samples[-1].observed_at_ns
    if first < window.start_ns or last > window.end_ns:
        issues.violations.append(
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
        issues.insufficient.append(
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


def _measurement_realtime_factor_upper(
    samples: Sequence[ClockSample], window: ClockMeasurementWindow, window_ns: int
) -> float:
    """Bound the worst RTF from above using source progress enclosing each window.

    At a recorded window end, the last sample at or before its start supplies
    an upper bound on progress, divided by the requested window length. Between
    recorded ends its minimum is attained at the next recorded end.
    An unobserved measurement edge has no finite upper bound: do not extrapolate.
    """

    first, last = samples[0], samples[-1]
    upper = (
        (last.source_time_ns - first.source_time_ns) / (window.end_ns - window.start_ns)
        if first.observed_at_ns == window.start_ns and last.observed_at_ns == window.end_ns
        else float("inf")
    )
    left = 0
    for index, current in enumerate(samples):
        start_ns = current.observed_at_ns - window_ns
        if start_ns < window.start_ns:
            continue
        while left + 1 < index and samples[left + 1].observed_at_ns <= start_ns:
            left += 1
        if samples[left].observed_at_ns <= start_ns:
            upper = min(upper, (current.source_time_ns - samples[left].source_time_ns) / window_ns)
    return max(0.0, upper)


def _windowed_realtime_factor(
    samples: Sequence[ClockSample],
    window_ns: int,
    issues: _TimingIssues,
    measurement_window: ClockMeasurementWindow | None,
) -> tuple[float, float]:
    """Take the worst integral or overlapping RTF with recorded endpoints.

    Explicit bounds require callback coverage and use conservative exact-length
    windows including the measurement edges. Without bounds, preserve the
    historical observed-span diagnostic: each callback ends a window whose
    first sample is at or before the requested boundary, at least window_ns
    apart. Neither mode interpolates source time; short spans use integral RTF.
    """

    if len(samples) < 2:
        issues.insufficient.append(
            ReadinessIssue("$.time_policy.min_realtime_factor", "need two clock samples")
        )
        return 0.0, float("inf")
    if any(
        current.observed_at_ns <= previous.observed_at_ns for previous, current in pairwise(samples)
    ):
        issues.violations.append(
            ReadinessIssue("$.time_policy", "clock observation times must increase")
        )
        return 0.0, float("inf")
    if measurement_window is not None:
        covered = _clock_coverage(samples, measurement_window, issues)
        lower = (
            _measurement_realtime_factor(samples, measurement_window, window_ns) if covered else 0.0
        )
        # A missing part of the recording must not hide a violation proved in
        # another observed interval, even though the full statistic is unavailable.
        upper = _measurement_realtime_factor_upper(samples, measurement_window, window_ns)
        return lower, upper
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
    return max(0.0, minimum), max(0.0, minimum)


def _evaluate_realtime(
    time_policy: Mapping[str, Any],
    samples: Sequence[ClockSample],
    issues: _TimingIssues,
    window_ns: int,
    measurement_window: ClockMeasurementWindow | None,
) -> tuple[float, float]:
    real_time_factor, upper = _windowed_realtime_factor(
        samples, window_ns, issues, measurement_window
    )
    deadline_miss_ratio = measurement_window.deadline_miss_ratio if measurement_window else None
    deadline_values = (
        [deadline_miss_ratio]
        if deadline_miss_ratio is not None
        else _required_values(
            samples,
            "deadline_miss_ratio",
            "$.time_policy.max_deadline_miss_ratio",
            issues.insufficient,
        )
    )
    if deadline_miss_ratio is not None:
        # Independent evidence must not hide an invalid or higher carried gauge.
        deadline_values.extend(
            sample.deadline_miss_ratio
            for sample in samples
            if sample.deadline_miss_ratio is not None
        )
    if any(not isfinite(value) or not 0 <= value <= 1 for value in deadline_values):
        issues.violations.append(
            ReadinessIssue(
                "$.time_policy.max_deadline_miss_ratio",
                "all deadline ratios must be finite and in [0, 1]; statistic unavailable",
            )
        )
        deadline_values = []
    deadline_miss_ratio = max(deadline_values, default=0.0)
    if upper < time_policy["min_realtime_factor"]:
        issues.violations.append(
            ReadinessIssue(
                "$.time_policy.min_realtime_factor",
                f"minimum window or integral RTF is at most {upper}; "
                f"recorded lower bound is {real_time_factor}",
            )
        )
    elif real_time_factor < time_policy["min_realtime_factor"]:
        issues.insufficient.append(
            ReadinessIssue(
                "$.time_policy.min_realtime_factor",
                f"RTF bound [{real_time_factor}, {upper}] does not determine whether "
                f"the minimum {time_policy['min_realtime_factor']} is met; "
                "numeric RTF is a lower bound, not a measured violation",
            )
        )
    if deadline_miss_ratio > time_policy["max_deadline_miss_ratio"]:
        issues.violations.append(
            ReadinessIssue(
                "$.time_policy.max_deadline_miss_ratio",
                f"maximum observed value was {deadline_miss_ratio}",
            )
        )
    return real_time_factor, deadline_miss_ratio


def _clock_progress(samples: Sequence[ClockSample], issues: _TimingIssues) -> tuple[bool, float]:
    monotonic = bool(samples) and all(
        current.source_time_ns >= previous.source_time_ns for previous, current in pairwise(samples)
    )
    if not samples:
        issues.insufficient.append(
            ReadinessIssue(
                "$.clock_observation.monotonic", "no clock samples; monotonicity unavailable"
            )
        )
    elapsed_ns = samples[-1].observed_at_ns - samples[0].observed_at_ns if samples else 0
    transitions = sum(
        current.source_time_ns != previous.source_time_ns for previous, current in pairwise(samples)
    )
    return monotonic, transitions * 1_000_000_000 / elapsed_ns if elapsed_ns > 0 else 0.0


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
    Its independent deadline gauge can be supplied even when no clock callback
    arrived. Uncertain bounds raise an error with failed=False and unevaluated
    paths; legacy numeric slots retain bounds or explicitly unavailable zeros.
    """

    if not isfinite(rtf_window_sec) or rtf_window_sec < 1.0:
        raise HarnessInputError("RTF window must be finite and at least one second")

    mode = execution["time_mode"]
    if not samples and mode != "simulation_realtime":
        observation = TimingObservation(False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        raise TimingValidationError(
            (ReadinessIssue("$.time_policy", "no clock samples"),),
            observation,
        )

    issues = _TimingIssues()
    monotonic, clock_hz = _clock_progress(samples, issues)
    if samples and not monotonic:
        issues.violations.append(ReadinessIssue("$.time_policy", "source clock moved backwards"))

    real_time_factor = 0.0
    observed_deadline_miss_ratio = 0.0
    offset_ms = 0.0
    drift_ppm = 0.0
    max_message_age_ms = 0.0

    if mode == "simulation_realtime":
        real_time_factor, observed_deadline_miss_ratio = _evaluate_realtime(
            time_policy,
            samples,
            issues,
            round(rtf_window_sec * 1_000_000_000),
            measurement_window,
        )
    elif mode == "playback_clocked":
        if clock_hz < time_policy["min_clock_hz"]:
            issues.violations.append(
                ReadinessIssue(
                    "$.time_policy.min_clock_hz",
                    f"observed clock frequency was {clock_hz}",
                )
            )
        if samples[-1].source_time_ns <= samples[0].source_time_ns:
            issues.violations.append(
                ReadinessIssue("$.time_policy", "playback clock did not advance")
            )
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
            issues.violations.append(
                ReadinessIssue("$.time_policy", "stepped clock did not advance")
            )
        for index, delta in enumerate(deltas):
            if delta <= 0:
                issues.violations.append(
                    ReadinessIssue(
                        "$.time_policy.step_size_sec",
                        f"sample {index + 1} did not advance by a positive step",
                    )
                )
                continue
            observed_steps = max(1, round(delta / step_ns))
            residual_ns = abs(delta - observed_steps * step_ns)
            if residual_ns > 1:
                issues.violations.append(
                    ReadinessIssue(
                        "$.time_policy.step_size_sec",
                        f"sample {index + 1} delta {delta} ns is not a step multiple",
                    )
                )
            skipped_steps = observed_steps - 1
            if skipped_steps > max_skipped_steps:
                issues.violations.append(
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
        deadline_miss_ratio=observed_deadline_miss_ratio,
        max_message_age_ms=max_message_age_ms,
        clock_hz=clock_hz,
    )
    if issues.violations or issues.insufficient:
        raise TimingValidationError(
            tuple(issues.violations), observation, insufficient_issues=tuple(issues.insufficient)
        )
    return observation
