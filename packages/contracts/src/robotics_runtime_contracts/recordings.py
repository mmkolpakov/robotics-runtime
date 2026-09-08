"""Optional MCAP producer; importing contracts does not require MCAP."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from robotics_runtime_contracts import validate_role
from robotics_runtime_contracts.writers import WriterError


def recording_summary_from_mcap(source: str | Path) -> dict[str, Any]:
    """Read a finalized MCAP through the upstream library and bind its exact bytes."""
    try:
        from robotics_runtime_contracts._mcap_summary import summarize
    except ModuleNotFoundError as error:
        raise WriterError(
            "recording-summary requires robotics-runtime-contracts[mcap]",
            error_id="writer.missing_dependency",
        ) from error
    document = summarize(Path(source).expanduser())
    validate_role(document, "recording_summary")
    return document


__all__ = ["recording_summary_from_mcap"]
