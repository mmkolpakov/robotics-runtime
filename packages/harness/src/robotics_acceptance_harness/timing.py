from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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


def _windowed_realtime_factor(
    samples: Sequence[ClockSample],
    window_ns: int,
    issues: list[ReadinessIssue],
) -> float:
    """Take the worst integral or overlapping RTF over at least window_ns.

    Each callback ends a window whose first sample is the latest one at or
    before the requested boundary. This uses measured endpoints, without
    interpolating source time. Startup prefixes are not individual windows;
    a recording shorter than window_ns is assessed only by its integral RTF.
    """

    if len(samples) < 2:
        issues.append(ReadinessIssue("$.time_policy.min_realtime_factor", "need two clock samples"))
        return 0.0
    if any(
        current.observed_at_ns <= previous.observed_at_ns
        for previous, current in zip(samples, samples[1:], strict=False)
    ):
        issues.append(ReadinessIssue("$.time_policy", "clock observation times must increase"))
        return 0.0
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
) -> tuple[float, float]:
    real_time_factor = _windowed_realtime_factor(samples, window_ns, issues)
    deadline_values = _required_values(
        samples, "deadline_miss_ratio", "$.time_policy.max_deadline_miss_ratio", issues
    )
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
) -> TimingObservation:
    """Evaluate clock policy, with realtime RTF from timestamp windows and the full span."""

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
        current.source_time_ns >= previous.source_time_ns
        for previous, current in zip(samples, samples[1:], strict=False)
    )
    if not monotonic:
        issues.append(ReadinessIssue("$.time_policy", "source clock moved backwards"))

    elapsed_ns = samples[-1].observed_at_ns - samples[0].observed_at_ns
    clock_hz = (len(samples) - 1) * 1_000_000_000 / elapsed_ns if elapsed_ns > 0 else 0.0
    mode = execution["time_mode"]

    real_time_factor = 0.0
    deadline_miss_ratio = 0.0
    offset_ms = 0.0
    drift_ppm = 0.0
    max_message_age_ms = 0.0

    if mode == "simulation_realtime":
        real_time_factor, deadline_miss_ratio = _evaluate_realtime(
            time_policy, samples, issues, round(rtf_window_sec * 1_000_000_000)
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
        transitions = [
            current
            for previous, current in zip(samples, samples[1:], strict=False)
            if current.source_time_ns != previous.source_time_ns
        ]
        transition_sources = [samples[0], *transitions]
        deltas = [
            current.source_time_ns - previous.source_time_ns
            for previous, current in zip(
                transition_sources,
                transition_sources[1:],
                strict=False,
            )
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
