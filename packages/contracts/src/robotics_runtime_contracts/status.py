from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from robotics_runtime_contracts.errors import ContractError


class OutcomeStatus(StrEnum):
    PASSED = "passed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
    ERROR = "error"


_PRIORITY = {status: priority for priority, status in enumerate(OutcomeStatus)}


def worst_status(
    statuses: Iterable[str | OutcomeStatus],
    *,
    collapse_cancelled: bool = False,
) -> str:
    """Return the deterministic worst outcome from a non-empty collection."""

    try:
        values = tuple(OutcomeStatus(status) for status in statuses)
    except ValueError as error:
        raise ContractError(str(error), error_id="status.invalid") from error
    if not values:
        raise ContractError("at least one status is required", error_id="status.invalid")
    status = max(values, key=_PRIORITY.__getitem__)
    if collapse_cancelled and status is OutcomeStatus.CANCELLED:
        return OutcomeStatus.INCOMPLETE.value
    return status.value
