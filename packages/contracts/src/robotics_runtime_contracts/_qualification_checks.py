"""Independent link checks over individually validated artifact descriptors."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any

from robotics_runtime_contracts import _qualification as rules
from robotics_runtime_contracts._qualification_types import (
    QualificationArtifact,
    QualificationDiagnostic,
    QualificationReport,
)
from robotics_runtime_contracts.errors import ContractError


@dataclass(frozen=True, slots=True)
class _Context:
    grouped: Mapping[str, Sequence[QualificationArtifact]]
    scenario_artifact: QualificationArtifact
    run_artifact: QualificationArtifact
    aggregate_artifact: QualificationArtifact
    runtimes: Mapping[str, QualificationArtifact]
    results: Mapping[str, QualificationArtifact]
    evidence_indexes: Mapping[str, QualificationArtifact]
    recording_summaries: Mapping[str, QualificationArtifact]

    @property
    def scenario(self) -> Mapping[str, Any]:
        return rules._document(self.scenario_artifact)

    @property
    def run(self) -> Mapping[str, Any]:
        return rules._document(self.run_artifact)

    @property
    def aggregate(self) -> Mapping[str, Any]:
        return rules._document(self.aggregate_artifact)

    @property
    def domains(self) -> set[str]:
        return {item["domain_id"] for item in self.run["domains"]}


@dataclass(frozen=True, slots=True)
class _Check:
    name: str
    action: Callable[[], None]
    subject_name: str | None = None


def _run_check(check: _Check, diagnostics: list[QualificationDiagnostic]) -> bool:
    try:
        check.action()
    except ContractError as error:
        diagnostics.append(
            QualificationDiagnostic(
                error.error_id,
                str(error),
                check.name,
                check.subject_name,
                error.json_path,
            )
        )
        return False
    return True


def _context(
    artifacts: Sequence[QualificationArtifact],
    diagnostics: list[QualificationDiagnostic],
) -> _Context | None:
    grouped: dict[str, list[QualificationArtifact]] = defaultdict(list)
    for artifact in artifacts:
        grouped[artifact.kind].append(artifact)
    singles: dict[str, QualificationArtifact] = {}
    labeled: dict[str, dict[str, QualificationArtifact]] = {}
    for kind, name in (
        ("scenario", "scenario.json"),
        ("acceptance_run", "acceptance-run.json"),
        ("acceptance_aggregate", "acceptance-aggregate.json"),
    ):
        try:
            singles[kind] = rules._one(grouped, kind, name)
        except ContractError as error:
            diagnostics.append(
                QualificationDiagnostic(
                    error.error_id,
                    str(error),
                    "subjects.required",
                    name,
                    error.json_path,
                )
            )
    for kind, prefix in (
        ("runtime_manifest", "runtime-manifests/"),
        ("domain_result", "results/"),
        ("evidence_index", "evidence-indexes/"),
        ("recording_summary", "recording-summaries/"),
    ):
        try:
            labeled[kind] = rules._labeled(grouped, kind, prefix)
        except ContractError as error:
            diagnostics.append(
                QualificationDiagnostic(
                    error.error_id,
                    str(error),
                    "subjects.labels",
                    json_path=error.json_path,
                )
            )
    if diagnostics:
        return None
    return _Context(
        grouped,
        singles["scenario"],
        singles["acceptance_run"],
        singles["acceptance_aggregate"],
        labeled["runtime_manifest"],
        labeled["domain_result"],
        labeled["evidence_index"],
        labeled["recording_summary"],
    )


def _identity_checks(context: _Context) -> Iterator[_Check]:
    for label, expected, actual in (
        ("acceptance run scenario_id", context.scenario["scenario_id"], context.run["scenario_id"]),
        (
            "acceptance run scenario digest",
            context.scenario_artifact.sha256,
            context.run["scenario_sha256"],
        ),
        ("aggregate run_id", context.run["run_id"], context.aggregate["run_id"]),
        (
            "aggregate acceptance run digest",
            context.run_artifact.sha256,
            context.aggregate["acceptance_run_sha256"],
        ),
    ):
        yield _Check("run.identity", partial(rules._require_equal, label, expected, actual))


def _domain_sets(context: _Context) -> None:
    for name, values in (
        ("runtime manifest", context.runtimes),
        ("domain result", context.results),
        ("evidence index", context.evidence_indexes),
    ):
        if set(values) != context.domains:
            rules._fail(f"{name} set does not equal acceptance run domains")


def _domain_timeline(context: _Context, domain: str) -> None:
    result = rules._document(context.results[domain])
    rules._require_time_order(
        f"qualification timeline for {domain}",
        context.run["created_at"],
        rules._document(context.runtimes[domain])["generated_at"],
        result["started_at"],
        rules._document(context.evidence_indexes[domain])["generated_at"],
        result["finished_at"],
        context.aggregate["generated_at"],
    )


def _domain_identity(context: _Context, domain: str) -> None:
    result = rules._document(context.results[domain])
    for label, expected, actual in (
        ("run_id", context.run["run_id"], result["run_id"]),
        ("domain_id", domain, result["domain_id"]),
        ("scenario_id", context.scenario["scenario_id"], result["scenario_id"]),
        ("scenario digest", context.scenario_artifact.sha256, result["scenario_sha256"]),
        (
            "runtime manifest digest",
            context.runtimes[domain].sha256,
            result["runtime_manifest_sha256"],
        ),
    ):
        rules._require_equal(f"result {domain} {label}", expected, actual)


def _domain_assertions(context: _Context, domain: str) -> None:
    declared = {item["assertion_id"] for item in context.scenario["assertions"]}
    observed = {
        item["assertion_id"]
        for item in rules._document(context.results[domain])["assertion_results"]
    }
    if missing := declared - observed:
        rules._fail(f"result {domain} omits scenario assertions: {sorted(missing)}")


def _domain_evidence(context: _Context, domain: str) -> None:
    result = rules._document(context.results[domain])
    indexed = rules._document(context.evidence_indexes[domain])["artifacts"]
    fields = (
        "artifact_id",
        "kind",
        "uri",
        "immutable_revision",
        "receipt_sha256",
        "sha256",
        "size_bytes",
        "media_type",
        "retention_class",
    )
    actual = {
        item["artifact_id"]: rules._project_fields(item, fields) for item in result["evidence"]
    }
    expected = {item["artifact_id"]: rules._project_fields(item, fields) for item in indexed}
    segments = {item["artifact_id"]: item.get("segment_index") for item in indexed}
    if actual != expected or any(
        "segment_index" in item and item["segment_index"] != segments[item["artifact_id"]]
        for item in result["evidence"]
    ):
        rules._fail(f"result {domain} evidence does not exactly match its index")


def _domain_checks(context: _Context) -> Iterator[_Check]:
    for domain, artifact in context.results.items():
        for name, action in (
            ("timeline", partial(_domain_timeline, context, domain)),
            ("identity", partial(_domain_identity, context, domain)),
            (
                "execution",
                partial(
                    rules._validate_execution_alignment,
                    context.scenario,
                    context.run,
                    rules._document(context.runtimes[domain]),
                    rules._document(artifact),
                    domain,
                ),
            ),
            ("assertions", partial(_domain_assertions, context, domain)),
            ("evidence", partial(_domain_evidence, context, domain)),
        ):
            yield _Check(f"domain.{name}", action, artifact.subject_name)


def _aggregate_results(context: _Context) -> None:
    fields = ("result_id", "result_sha256", "status")
    expected = {
        domain: {
            "result_id": rules._document(artifact)["result_id"],
            "result_sha256": artifact.sha256,
            "status": rules._document(artifact)["status"],
        }
        for domain, artifact in context.results.items()
    }
    actual = {
        item["domain_id"]: rules._project_fields(item, fields)
        for item in context.aggregate["per_domain_results"]
    }
    if actual != expected:
        rules._fail("aggregate per_domain_results do not exactly match local results")


def _binding_checks(context: _Context) -> Iterator[_Check]:
    grouped, scenario = context.grouped, context.scenario
    run_id, created = context.run["run_id"], context.run["created_at"]
    generated = context.aggregate["generated_at"]
    yield _Check(
        "provider.bindings",
        partial(
            rules._validate_provider_bindings,
            grouped,
            scenario,
            run_id,
            context.runtimes,
            created,
        ),
    )
    yield _Check(
        "receipts",
        partial(
            rules._validate_receipts,
            grouped,
            scenario,
            run_id,
            context.evidence_indexes,
            created,
            generated,
        ),
    )
    yield _Check(
        "model.dataset",
        partial(
            rules._validate_model_and_dataset,
            grouped,
            scenario,
            context.runtimes,
            context.results,
        ),
    )
    yield _Check(
        "configuration",
        partial(
            rules._validate_retained_configuration,
            grouped,
            scenario,
            context.run,
            context.runtimes,
        ),
    )
    yield _Check(
        "authorization",
        partial(
            rules._validate_physical_authorization,
            grouped,
            context.scenario_artifact,
            context.runtimes,
            context.results,
        ),
    )
    yield _Check(
        "evidence.recordings",
        partial(
            rules._validate_evidence,
            grouped,
            context.evidence_indexes,
            context.recording_summaries,
        ),
    )
    yield _Check(
        "transport",
        partial(
            rules._validate_transport,
            grouped,
            run_id,
            context.domains,
            context.scenario_artifact,
            context.aggregate,
            context.evidence_indexes,
            context.results,
            created,
            generated,
        ),
    )


def _inspect_domains(context: _Context, diagnostics: list[QualificationDiagnostic]) -> bool:
    execution_valid = True
    for check in _domain_checks(context):
        passed = _run_check(check, diagnostics)
        if check.name == "domain.execution" and not passed:
            execution_valid = False
    return execution_valid


def inspect_links(artifacts: Sequence[QualificationArtifact]) -> QualificationReport:
    diagnostics: list[QualificationDiagnostic] = []
    names = [item.subject_name for item in artifacts]
    if len(names) != len(set(names)):
        diagnostics.append(
            QualificationDiagnostic(
                "qualification.invalid",
                "qualification subject names must be unique",
                "subjects.unique",
            )
        )
    context = _context(artifacts, diagnostics)
    if context is None:
        return QualificationReport(tuple(artifacts), tuple(diagnostics), blocked_checks=("links",))
    for check in _identity_checks(context):
        _run_check(check, diagnostics)
    domains_valid = _run_check(_Check("domains", partial(_domain_sets, context)), diagnostics)
    execution_valid = domains_valid and _inspect_domains(context, diagnostics)
    _run_check(_Check("aggregate.results", partial(_aggregate_results, context)), diagnostics)
    for domain, artifact in context.evidence_indexes.items():
        _run_check(
            _Check(
                "evidence.identity",
                partial(
                    rules._require_equal,
                    f"evidence index {domain} run_id",
                    context.run["run_id"],
                    rules._document(artifact)["run_id"],
                ),
                artifact.subject_name,
            ),
            diagnostics,
        )
    bindings = tuple(_binding_checks(context))
    if execution_valid:
        for check in bindings:
            _run_check(check, diagnostics)
    blocked: tuple[str, ...] = () if domains_valid else ("domain.links",)
    if not execution_valid:
        blocked += tuple(check.name for check in bindings)
    return QualificationReport(
        tuple(artifacts),
        tuple(diagnostics),
        context.run["run_id"],
        context.aggregate["generated_at"],
        blocked,
    )
