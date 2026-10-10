"""Archive assessments over one captured execution and two distinct result sets."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from robotics_runtime_contracts import _qualification as rules
from robotics_runtime_contracts._qualification_checks import _Context
from robotics_runtime_contracts._qualification_files import validate_descriptor
from robotics_runtime_contracts._qualification_native import (
    _NATIVE_POLICY_ASSERTIONS,
    _method_controls,
    _receipt_requirements,
    _require_native_time_order,
    inspect_native_links,
)
from robotics_runtime_contracts._qualification_types import QualificationArtifact
from robotics_runtime_contracts.canonical import dumps_canonical
from robotics_runtime_contracts.serialization import MAX_DOCUMENT_BYTES

Artifacts = Mapping[str, Sequence[QualificationArtifact]]


@dataclass(frozen=True, slots=True)
class _Archive:
    artifacts: tuple[QualificationArtifact, ...]
    original: _Context
    assessment: _Context


def _group(artifacts: Sequence[QualificationArtifact]) -> dict[str, list[QualificationArtifact]]:
    grouped: dict[str, list[QualificationArtifact]] = defaultdict(list)
    for artifact in artifacts:
        grouped[artifact.kind].append(artifact)
    return grouped


def _single(grouped: Artifacts, kind: str) -> QualificationArtifact:
    values = grouped.get(kind, ())
    if len(values) != 1:
        rules._fail(f"archive requires exactly one {kind}")
    return values[0]


def _aggregate_results(
    aggregate: QualificationArtifact, results: Mapping[str, QualificationArtifact]
) -> dict[str, QualificationArtifact]:
    selected: dict[str, QualificationArtifact] = {}
    for reference in rules._document(aggregate)["per_domain_results"]:
        domain, digest = reference["domain_id"], reference["result_sha256"]
        if domain in selected or digest not in results:
            rules._fail("archive aggregate has duplicate domains or an unknown result")
        artifact = results[digest]
        if rules._document(artifact)["domain_id"] != domain:
            rules._fail("archive aggregate result belongs to another domain")
        selected[domain] = artifact
    return selected


def _is_original_pair(
    original: Mapping[str, QualificationArtifact],
    assessment: Mapping[str, QualificationArtifact],
) -> bool:
    return set(original) == set(assessment) and all(
        rules._document(assessment[domain])["original_execution"].get("original_result_sha256")
        == artifact.sha256
        for domain, artifact in original.items()
    )


def _result_pair(
    grouped: Artifacts,
) -> tuple[
    QualificationArtifact,
    dict[str, QualificationArtifact],
    QualificationArtifact,
    dict[str, QualificationArtifact],
]:
    aggregates = grouped.get("acceptance_aggregate", ())
    supplied = grouped.get("domain_result", ())
    if any(
        rules._document(artifact)["schema_version"] != "acceptance-result.v2"
        for artifact in supplied
    ):
        rules._fail("archive domain results must all use acceptance-result.v2")
    results = {artifact.sha256: artifact for artifact in supplied}
    if len(aggregates) != 2 or len(results) != len(supplied):
        rules._fail("archive requires two aggregates and uniquely captured domain results")
    registries = [_aggregate_results(aggregate, results) for aggregate in aggregates]
    candidates = [
        (aggregates[a], registries[a], aggregates[b], registries[b])
        for a, b in ((0, 1), (1, 0))
        if _is_original_pair(registries[a], registries[b])
    ]
    if len(candidates) != 1:
        rules._fail("archive must identify exactly one original and one assessment per domain")
    original_aggregate, originals, aggregate, assessments = candidates[0]
    selected = [*originals.values(), *assessments.values()]
    if len(selected) != len(supplied) or len({item.sha256 for item in selected}) != len(selected):
        rules._fail("archive has unused or multiply selected results")
    return original_aggregate, originals, aggregate, assessments


def _context(
    grouped: Artifacts,
    aggregate: QualificationArtifact,
    results: Mapping[str, QualificationArtifact],
) -> _Context:
    selected = dict(grouped)
    selected["acceptance_aggregate"] = [aggregate]
    selected["domain_result"] = list(results.values())
    return _Context(
        selected,
        _single(grouped, "scenario"),
        _single(grouped, "acceptance_run"),
        aggregate,
        rules._labeled(grouped, "runtime_manifest", "runtime-manifests/"),
        results,
        rules._labeled(grouped, "evidence_index", "evidence-indexes/"),
        rules._labeled(grouped, "recording_summary", "recording-summaries/"),
    )


def _archive(artifacts: Sequence[QualificationArtifact]) -> _Archive:
    names = [artifact.subject_name for artifact in artifacts]
    if len(names) != len(set(names)):
        rules._fail("qualification subject names must be unique")
    grouped = _group(artifacts)
    if rules._document(_single(grouped, "scenario"))["schema_version"] != "acceptance-scenario.v2":
        rules._fail("archive assessment requires an original native v2 execution")
    original_aggregate, originals, aggregate, assessments = _result_pair(grouped)
    return _Archive(
        tuple(artifacts),
        _context(grouped, original_aggregate, originals),
        _context(grouped, aggregate, assessments),
    )


def _receipt_scope(context: _Context) -> tuple[_Context, set[str], set[str]]:
    receipts = {item["receipt_sha256"] for item in _receipt_requirements(context)}
    receipts.update(
        item["receipt_sha256"]
        for artifact in context.evidence_indexes.values()
        for item in rules._document(artifact)["artifacts"]
        if item["storage_state"] == "retained"
    )
    selected = dict(context.grouped)
    selected["artifact_receipt"] = [
        item for item in selected.get("artifact_receipt", ()) if item.sha256 in receipts
    ]
    verifications = {
        rules._document(item)["verification_sha256"] for item in selected["artifact_receipt"]
    }
    selected["artifact_verification"] = [
        item for item in selected.get("artifact_verification", ()) if item.sha256 in verifications
    ]
    return replace(context, grouped=selected), receipts, verifications


def _receipt_inventory(archive: _Archive) -> _Archive:
    original, old_receipts, old_verifications = _receipt_scope(archive.original)
    assessment, new_receipts, new_verifications = _receipt_scope(archive.assessment)
    grouped = _group(archive.artifacts)
    for kind, expected in (
        ("artifact_receipt", old_receipts | new_receipts),
        ("artifact_verification", old_verifications | new_verifications),
    ):
        actual = {item.sha256 for item in grouped.get(kind, ())}
        if actual != expected:
            rules._fail("archive receipts and verifications must match both captured methods")
    return replace(archive, original=original, assessment=assessment)


def _inspect_context(context: _Context) -> None:
    report = inspect_native_links(
        tuple(item for values in context.grouped.values() for item in values), context, []
    )
    report.raise_for_errors()


def _identity(reference: Mapping[str, Any]) -> tuple[str, int]:
    return reference["sha256"], reference["size_bytes"]


def _captured_context(context: _Context, domain: str) -> None:
    evaluation = rules._document(context.results[domain])["evaluation"]
    controls = _method_controls(context, domain)
    references = [
        evaluation["method"]["configuration"],
        evaluation["environment"],
        *evaluation.get("calibration", {}).get("artifacts", ()),
    ]
    identities = {_identity(reference) for reference in references}
    if sum(size for _, size in identities) > 2 * MAX_DOCUMENT_BYTES:
        rules._fail("archive assessment context exceeds its bounded control capture")
    for reference in references:
        artifact = rules._require_raw(
            context.grouped,
            reference["sha256"],
            "archive assessment context",
            kinds=("other_evidence",),
            size_bytes=reference["size_bytes"],
        )
        if artifact.native_metadata_bytes is None:
            rules._fail(
                "archive comparison requires captured method, environment and calibration bytes"
            )
    if "calibration" in evaluation:
        expected = controls.get("calibration", {"state": "unobserved"})
        if expected.get("state") != evaluation["calibration"]["state"]:
            rules._fail("archive calibration state differs from captured method controls")


def _source_binding(archive: _Archive, domain: str) -> None:
    original = rules._document(archive.original.results[domain])
    result = rules._document(archive.assessment.results[domain])
    if original["result_id"] == result["result_id"]:
        rules._fail("archive assessment must have a distinct result_id")
    if not {"calibration", "coverage"} <= set(result["evaluation"]):
        rules._fail("new archive assessment requires explicit calibration and coverage")
    _require_native_time_order(
        "archive assessment after original evaluation",
        original["evaluation"]["finished_at"],
        result["evaluation"]["started_at"],
    )
    for field in ("execution", "profile", "native_model"):
        rules._require_equal(f"archive original {field}", original.get(field), result.get(field))
    for field in (
        "acceptance_run_sha256",
        "observation_sha256",
        "evidence_index_sha256",
        "started_at",
        "finished_at",
    ):
        rules._require_equal(
            f"archive original execution {field}",
            original["original_execution"][field],
            result["original_execution"][field],
        )


def _criterion_results(result: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    selected = [
        item
        for item in result["assertion_results"]
        if item["source"] == "product" or item["assertion_id"] not in _NATIVE_POLICY_ASSERTIONS
    ]
    by_id = {item["assertion_id"]: item for item in selected}
    if len(by_id) != len(selected):
        rules._fail("archive coverage has ambiguous assertion identities")
    return by_id


def _coverage(
    context: _Context,
    domain: str,
) -> tuple[set[str], set[str], dict[str, Mapping[str, Any]]]:
    result = rules._document(context.results[domain])
    criteria = _criterion_results(result)
    coverage = result["evaluation"].get("coverage")
    if coverage is None:
        return set(), set(criteria), criteria
    covered = {item["assertion_id"]: item for item in coverage["covered_assertions"]}
    uncovered = {item["assertion_id"] for item in coverage["uncovered_assertions"]}
    if (
        len(covered) != len(coverage["covered_assertions"])
        or len(uncovered) != len(coverage["uncovered_assertions"])
        or set(covered) & uncovered
        or set(covered) | uncovered != set(criteria)
    ):
        rules._fail("archive coverage must classify each actual criterion exactly once")
    indexed = rules._document(context.evidence_indexes[domain])["artifacts"]
    raw_sources = {item["sha256"] for item in indexed if item["kind"] != "acceptance_observation"}
    metric_sources = {item["sha256"] for item in indexed if item["kind"] == "metrics"}
    for identifier, witness in covered.items():
        assertion = criteria[identifier]
        declared = set(witness["evidence_sha256"])
        if assertion["source"] == "core":
            if len(declared) != 1 or not declared <= metric_sources:
                rules._fail("archive metric coverage lacks its captured OTLP source")
            if assertion.get("observed_value") is None:
                rules._fail("archive covered metric has no measured value")
            actual = declared
            criteria[identifier] = {**assertion, "evidence_sha256": sorted(declared)}
        else:
            actual = set(assertion["evidence_sha256"]) & raw_sources
        if not actual or declared != actual or assertion["status"] == "skipped":
            rules._fail("archive covered criterion lacks its original raw source binding")
    return set(covered), set(criteria), criteria


def _calibration_identity(evaluation: Mapping[str, Any]) -> tuple[Any, ...] | None:
    selection = evaluation.get("calibration")
    if selection is None or selection["state"] == "unobserved":
        return None
    if selection["state"] == "selected":
        return ("selected", *sorted(_identity(item) for item in selection["artifacts"]))
    return ("not_applicable", selection["reason"])


def _comparison_reasons(original: Mapping[str, Any], assessment: Mapping[str, Any]) -> set[str]:
    reasons: set[str] = set()
    before, after = original["evaluation"], assessment["evaluation"]
    method_fields = ("implementation", "version")
    if any(
        before["method"][field] != after["method"][field] for field in method_fields
    ) or _identity(before["method"]["configuration"]) != _identity(
        after["method"]["configuration"]
    ):
        reasons.add("method_changed")
    if _identity(before["environment"]) != _identity(after["environment"]):
        reasons.add("environment_changed")
    if before.get("window") != after.get("window"):
        reasons.add("window_changed")
    calibrations = (_calibration_identity(before), _calibration_identity(after))
    if None in calibrations:
        reasons.add("calibration_unobserved")
    elif calibrations[0] != calibrations[1]:
        reasons.add("calibration_changed")
    if "coverage" not in before or "coverage" not in after:
        reasons.add("coverage_unobserved")
    return reasons


def _outcome(assertion: Mapping[str, Any]) -> dict[str, Any]:
    fields = ("source", "namespace", "status", "observed_value", "unit")
    return {
        **{field: assertion[field] for field in fields if field in assertion},
        "evidence_sha256": sorted(assertion["evidence_sha256"]),
    }


def _comparison(archive: _Archive, domain: str) -> dict[str, Any]:
    original_artifact = archive.original.results[domain]
    assessment_artifact = archive.assessment.results[domain]
    original, assessment = map(rules._document, (original_artifact, assessment_artifact))
    before, original_ids, original_results = _coverage(archive.original, domain)
    after, assessment_ids, assessment_results = _coverage(archive.assessment, domain)
    covered = before & after
    reasons = _comparison_reasons(original, assessment)
    if not covered:
        reasons.add("no_covered_assertions")
    compared = sorted(covered) if not reasons else []
    status = "not_comparable"
    if compared:
        different = any(
            dumps_canonical(_outcome(original_results[identifier]))
            != dumps_canonical(_outcome(assessment_results[identifier]))
            for identifier in compared
        )
        status = "different" if different else "matched"
        if different:
            reasons.add("assertion_outcome_changed")
    return {
        "domain_id": domain,
        "original_result": original_artifact.subject_name,
        "assessment_result": assessment_artifact.subject_name,
        "status": status,
        "compared_assertions": compared,
        "excluded_assertions": sorted((original_ids | assessment_ids) - set(compared)),
        "reasons": sorted(reasons),
    }


def _result_metadata(context: _Context, domain: str) -> dict[str, Any]:
    artifact = context.results[domain]
    result = rules._document(artifact)
    return {
        "domain_id": domain,
        "acceptance_result": artifact.subject_name,
        "result_id": result["result_id"],
        "status": result["status"],
        "evaluation": result["evaluation"],
    }


def _metadata(archive: _Archive) -> dict[str, Any]:
    original, assessment = archive.original, archive.assessment
    domains = sorted(original.domains)
    return {
        "schema_version": "qualification-bundle.v2",
        "run_id": original.run["run_id"],
        "generated_at": assessment.aggregate["generated_at"],
        "artifacts": [
            {"kind": item.kind, "subject_name": item.subject_name, "sha256": item.sha256}
            for item in sorted(archive.artifacts, key=lambda item: item.subject_name)
        ],
        "original_execution": {
            "scenario": original.scenario_artifact.subject_name,
            "acceptance_run": original.run_artifact.subject_name,
            "acceptance_aggregate": original.aggregate_artifact.subject_name,
            "domains": [
                {
                    **_result_metadata(original, domain),
                    "runtime_manifest": original.runtimes[domain].subject_name,
                    "acceptance_observation": next(
                        item.subject_name
                        for item in original.grouped["acceptance_observation"]
                        if rules._document(item)["domain_id"] == domain
                    ),
                    "evidence_index": original.evidence_indexes[domain].subject_name,
                }
                for domain in domains
            ],
        },
        "acceptance_aggregate": assessment.aggregate_artifact.subject_name,
        "assessments": [_result_metadata(assessment, domain) for domain in domains],
        "comparison": {
            "rule": "exact_assertion_outcome",
            "per_domain": [_comparison(archive, domain) for domain in domains],
        },
    }


def validate_archive_documents(
    artifacts: Sequence[QualificationArtifact],
    extension_schemas: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    """Inspect captured descriptors; file API alone binds them to actual local bytes."""
    for artifact in artifacts:
        validate_descriptor(artifact, extension_schemas)
    archive = _receipt_inventory(_archive(artifacts))
    _inspect_context(archive.original)
    _inspect_context(archive.assessment)
    for domain in sorted(archive.original.domains):
        _source_binding(archive, domain)
        _captured_context(archive.original, domain)
        _captured_context(archive.assessment, domain)
    return _metadata(archive)
