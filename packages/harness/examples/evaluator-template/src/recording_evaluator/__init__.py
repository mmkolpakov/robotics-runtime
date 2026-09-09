"""A product-owned MCAP assertion using only the harness's public SDK."""

from __future__ import annotations

from struct import error as StructError

from mcap.exceptions import McapError
from mcap.reader import NonSeekingReader
from robotics_acceptance_harness.sdk import (
    AssertionEvaluation,
    EvaluationContext,
    EvidenceAccessError,
    EvidenceValidationError,
    HarnessError,
)
from zstandard import ZstdError

NAMESPACE = "org.example.recording"


class InputError(HarnessError, ValueError):
    """A required recording is unavailable or cannot be read as MCAP."""

    error_id = "input.invalid"


def _message_count(context: EvaluationContext, digest: str) -> int:
    try:
        with context.evidence(digest) as stream:
            # Read every message in file order, including the end of the recording.
            # Sorting by time would buffer the entire recording in this reader.
            reader = NonSeekingReader(stream, validate_crcs=True)
            return sum(1 for _ in reader.iter_messages(log_time_order=False))
    except (
        EvidenceAccessError,
        EvidenceValidationError,
        McapError,
        ZstdError,
        RuntimeError,  # lz4.frame reports corrupt compressed frames with this built-in class.
        OSError,
        ValueError,
        EOFError,
        StructError,
    ) as error:
        raise InputError(f"cannot read verified MCAP {digest}: {error}") from error


def evaluate(context: EvaluationContext) -> tuple[AssertionEvaluation, ...]:
    """Count messages in each distinct verified application/mcap artifact."""
    digests = sorted(
        {
            str(link["sha256"])
            for link in context.evidence.links
            if link["media_type"] == "application/mcap"
        }
    )
    if not digests:
        # A product result without a verified evidence digest is not admissible.
        raise InputError("no application/mcap artifact is present in verified evidence")
    results: list[AssertionEvaluation] = []
    for digest in digests:
        assertion_id = f"{NAMESPACE}.nonempty.{digest}"
        try:
            count = _message_count(context, digest)
        except InputError as error:
            result = AssertionEvaluation(
                assertion_id,
                "error",
                None,
                "1",
                message=f"InputError: {error}",
                source="product",
                namespace=NAMESPACE,
                evidence_sha256=(digest,),
            )
        else:
            result = AssertionEvaluation(
                assertion_id,
                "passed" if count else "failed",
                count,
                "1",
                message=f"MCAP contains {count} message(s); at least one is required",
                source="product",
                namespace=NAMESPACE,
                evidence_sha256=(digest,),
            )
        results.append(result)
    return tuple(results)


__all__ = ["InputError", "NAMESPACE", "evaluate"]
