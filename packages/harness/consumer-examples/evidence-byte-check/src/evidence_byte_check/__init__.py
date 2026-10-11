"""A minimal byte-access example, not a robotics performance evaluator."""

import json
from collections.abc import Iterable

from robotics_acceptance_harness.evaluation import EvaluationContext
from robotics_acceptance_harness.metrics import AssertionEvaluation


def evaluate(context: EvaluationContext) -> Iterable[AssertionEvaluation]:
    candidates = [
        (path, link)
        for path, link in context.evidence.local_files.items()
        if link["artifact_id"] == "native-state" and link["media_type"] == "application/json"
    ]
    if len(candidates) != 1:
        raise ValueError("example profile requires indexed JSON artifact native-state")
    path, link = candidates[0]
    # The author profile must provide the public captured-byte API.
    reader = getattr(context.evidence, "read_local", None)
    if reader is None:
        raise ValueError("example requires an SDK profile with VerifiedEvidence.read_local")
    raw = reader(path, max_raw_evidence_bytes=1024 * 1024)
    yield AssertionEvaluation(
        assertion_id="org.example.evidence-bytes.nonempty",
        status="passed" if raw else "failed",
        observed_value=len(raw),
        unit="B",
        source="product",
        namespace="org.example.evidence-bytes",
        evidence_sha256=(str(link["sha256"]),),
    )
    calibrated = _calibrated_error(context, raw, str(link["sha256"]))
    if calibrated is not None:
        yield calibrated


def _calibrated_error(
    context: EvaluationContext, raw: bytes, raw_sha256: str
) -> AssertionEvaluation | None:
    controls = context.assessment_controls
    if controls is None or controls.data["calibration"]["state"] == "not_applicable":
        return None
    calibration = controls.data["calibration"]
    if calibration["state"] == "unobserved":
        return AssertionEvaluation(
            assertion_id="org.example.evidence-bytes.calibrated-error",
            unit="1",
            source="product",
            namespace="org.example.evidence-bytes",
            status="skipped",
            observed_value=None,
            message="this selected method has no observed offset calibration",
            evidence_sha256=(raw_sha256,),
        )
    references = calibration["artifacts"]
    if len(references) != 1:
        raise ValueError("this example method requires exactly one offset calibration")
    reference = references[0]
    # Use the captured public input; its URI is never reopened by the evaluator.
    captured = controls.read_input(reference)
    original = json.loads(raw)
    selected = json.loads(captured)
    evidence = (raw_sha256, str(reference["sha256"]))
    if (
        not isinstance(original, dict)
        or not isinstance(selected, dict)
        or type(original.get("counter")) is not int
        or type(selected.get("offset")) is not int
    ):
        return AssertionEvaluation(
            assertion_id="org.example.evidence-bytes.calibrated-error",
            unit="1",
            source="product",
            namespace="org.example.evidence-bytes",
            status="error",
            observed_value=None,
            message="raw counter and captured offset must be JSON integers",
            evidence_sha256=evidence,
        )
    corrected = original["counter"] - selected["offset"]
    return AssertionEvaluation(
        assertion_id="org.example.evidence-bytes.calibrated-error",
        unit="1",
        source="product",
        namespace="org.example.evidence-bytes",
        status="passed" if corrected == 0 else "failed",
        observed_value=corrected,
        message="captured raw counter minus captured calibration offset must equal zero",
        evidence_sha256=evidence,
    )
