"""A minimal byte-access example, not a robotics performance evaluator."""

from collections.abc import Iterable

from robotics_acceptance_harness.evaluation import EvaluationContext
from robotics_acceptance_harness.metrics import AssertionEvaluation


def evaluate(context: EvaluationContext) -> Iterable[AssertionEvaluation]:
    candidates = [
        (path, link)
        for path, link in context.evidence.local_files.items()
        if link["media_type"] == "application/json"
    ]
    if len(candidates) != 1:
        raise ValueError("example profile requires exactly one indexed JSON artifact")
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
