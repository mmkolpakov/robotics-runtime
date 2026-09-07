from __future__ import annotations

from datetime import datetime

from robotics_runtime_contracts.errors import ContractError


def parse_timestamp(value: str, *, json_path: str | None = None) -> datetime:
    """Parse an offset-bearing timestamp for comparisons after schema validation."""

    try:
        normalized = f"{value[:-1]}+00:00" if value.endswith(("Z", "z")) else value
        result = datetime.fromisoformat(normalized)
        if result.utcoffset() is None:
            raise ValueError("timestamp requires a UTC offset")
        return result
    except (AttributeError, TypeError, ValueError) as error:
        raise ContractError(
            f"invalid timestamp: {value!r}",
            error_id="input.invalid_timestamp",
            json_path=json_path,
        ) from error
