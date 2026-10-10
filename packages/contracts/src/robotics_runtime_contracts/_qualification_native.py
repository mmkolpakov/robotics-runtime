from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from functools import partial
from typing import TYPE_CHECKING, Any

from robotics_runtime_contracts import _qualification as rules
from robotics_runtime_contracts._qualification_types import (
    QualificationArtifact,
    QualificationDiagnostic,
    QualificationReport,
)
from robotics_runtime_contracts._timestamps import parse_timestamp_ns
from robotics_runtime_contracts.assessments import validate_assessment_controls
from robotics_runtime_contracts.errors import ContractError
from robotics_runtime_contracts.serialization import loads_mapping
from robotics_runtime_contracts.status import worst_status

if TYPE_CHECKING:
    from robotics_runtime_contracts._qualification_checks import _Context


def _identity(reference: Mapping[str, Any] | None) -> tuple[str, int] | None:
    if reference is None:
        return None
    return str(reference["sha256"]), int(reference["size_bytes"])


def _retained_reference(
    context: _Context, reference: Mapping[str, Any], label: str
) -> QualificationArtifact:
    return rules._require_raw(
        context.grouped,
        reference["sha256"],
        label,
        size_bytes=reference["size_bytes"],
    )


def _observations(context: _Context) -> dict[str, QualificationArtifact]:
    return rules._labeled(context.grouped, "acceptance_observation", "observations/")


def _domains(context: _Context, observations: Mapping[str, QualificationArtifact]) -> None:
    from robotics_runtime_contracts._qualification_checks import _domain_sets

    _domain_sets(context)
    if set(observations) != context.domains:
        rules._fail("observation set does not equal acceptance run domains")
    for kind, artifacts, schema in (
        ("runtime", context.runtimes, "runtime-manifest.v2"),
        ("result", context.results, "acceptance-result.v2"),
        ("observation", observations, "acceptance-observation.v2"),
    ):
        if any(
            rules._document(artifact)["schema_version"] != schema for artifact in artifacts.values()
        ):
            rules._fail(f"native qualification requires one v2 {kind} registry")
    if context.scenario["execution"]["target_environment"] in {"hil", "real_robot"}:
        rules._fail(
            "native v2 physical qualification requires native permit and authority semantics; "
            "hil and real_robot qualification are not supported"
        )


def _resolved_observations(
    profile: Mapping[str, Any], observation: Mapping[str, Any]
) -> dict[str, Any]:
    declared = profile["observations"]
    supplied = observation["observations"]
    if set(supplied) - set(declared):
        rules._fail("source observation includes names outside its declared profile")
    resolved = {}
    for name, requirement in declared.items():
        value = supplied.get(name)
        if requirement["requirement"] == "not_applicable":
            value = value or {
                "state": "not_applicable",
                "reason": requirement["reason"],
            }
            if value["state"] != "not_applicable" or value["reason"] != requirement["reason"]:
                rules._fail(
                    f"source observation {name} must preserve declared non-applicability and reason"
                )
        else:
            value = value or {"state": "unobserved", "reason": "producer supplied no observation"}
            if value["state"] == "not_applicable":
                rules._fail(f"source observation {name} is applicable under its profile")
        resolved[name] = value
    return resolved


def _domain(context: _Context, domain: str, observation_artifact: QualificationArtifact) -> None:
    controls = _method_controls(context, domain)
    _domain_bindings(context, domain, observation_artifact, controls)
    _domain_window(context, domain, observation_artifact, controls)
    _domain_assertion_registry(context, domain, controls)
    _domain_coverage(context, domain, observation_artifact, controls)
    _domain_observation_evidence(context, domain, observation_artifact)
    _domain_assessment_retention(context, domain)


def _method_controls(context: _Context, domain: str) -> Mapping[str, Any]:
    assessment = rules._document(context.results[domain])["evaluation"]
    reference = assessment["method"]["configuration"]
    artifact = rules._require_raw(
        context.grouped,
        reference["sha256"],
        f"domain {domain} method controls",
        kinds=("other_evidence",),
        size_bytes=reference["size_bytes"],
    )
    if artifact.native_metadata_bytes is None:
        rules._fail(f"domain {domain} method controls require captured metadata bytes")
    controls = loads_mapping(artifact.native_metadata_bytes, source_name=artifact.subject_name)
    validate_assessment_controls(controls)
    expected = controls.get("calibration")
    supplied = assessment.get("calibration")
    if expected is not None and supplied is not None:
        rules._require_equal(f"domain {domain} selected calibration", expected, supplied)
    elif expected is None and supplied is not None and supplied["state"] != "unobserved":
        rules._fail(f"domain {domain} original method makes no calibration declaration")
    return controls


def _domain_bindings(
    context: _Context,
    domain: str,
    observation_artifact: QualificationArtifact,
    controls: Mapping[str, Any],
) -> None:
    from robotics_runtime_contracts._qualification_checks import (
        _domain_evidence,
        _domain_identity,
    )

    _domain_identity(context, domain)
    _domain_evidence(context, domain)
    scenario = context.scenario
    runtime = rules._document(context.runtimes[domain])
    result = rules._document(context.results[domain])
    observation = rules._document(observation_artifact)
    index = rules._document(context.evidence_indexes[domain])
    original = result["original_execution"]
    assessment = result["evaluation"]
    for label, expected, actual in (
        ("runtime scenario digest", context.scenario_artifact.sha256, runtime["scenario_sha256"]),
        ("original run digest", context.run_artifact.sha256, original["acceptance_run_sha256"]),
        (
            "original observation digest",
            observation_artifact.sha256,
            original["observation_sha256"],
        ),
        (
            "original evidence index",
            context.evidence_indexes[domain].sha256,
            original["evidence_index_sha256"],
        ),
        ("index run_id", context.run["run_id"], index["run_id"]),
        ("observation run_id", context.run["run_id"], observation["run_id"]),
        ("observation domain_id", domain, observation["domain_id"]),
        ("observation scenario_id", scenario["scenario_id"], observation["scenario_id"]),
        (
            "observation scenario digest",
            context.scenario_artifact.sha256,
            observation["scenario_sha256"],
        ),
        (
            "observation runtime digest",
            context.runtimes[domain].sha256,
            observation["runtime_manifest_sha256"],
        ),
        ("original start", observation["started_at"], original["started_at"]),
        ("original finish", observation["finished_at"], original["finished_at"]),
        (
            "runtime evaluator bindings",
            scenario["evaluator_requirements"],
            runtime["evaluator_bindings"],
        ),
        (
            "result evaluator bindings",
            controls["evaluator_requirements"],
            result["evaluators"],
        ),
    ):
        rules._require_equal(f"domain {domain} {label}", expected, actual)
    for field in ("execution", "profile"):
        for label, document in (("runtime", runtime), ("result", result)):
            rules._require_equal(f"{label} {domain} {field}", scenario[field], document[field])
    for label, document in (("runtime", runtime), ("result", result), ("observation", observation)):
        rules._require_equal(
            f"{label} {domain} native model",
            _identity(scenario.get("native_model")),
            _identity(document.get("native_model")),
        )
    clock = scenario["profile"].get("clock")
    if clock is not None:
        rules._require_fields(
            f"domain {domain} clock authority",
            context.run["time_authority"],
            clock,
            ("kind", "source_id"),
        )
    for label, prepared_at in (
        ("run context", context.run["created_at"]),
        ("runtime manifest", runtime["generated_at"]),
    ):
        _require_native_time_order(
            f"{label} {domain} before execution", prepared_at, observation["started_at"]
        )
    _require_native_time_order(
        f"original execution {domain}",
        observation["started_at"],
        observation["finished_at"],
        index["generated_at"],
        assessment["started_at"],
        assessment["finished_at"],
        context.aggregate["generated_at"],
    )


def _require_native_time_order(label: str, *values: str) -> None:
    timestamps = [parse_timestamp_ns(value) for value in values]
    if timestamps != sorted(timestamps):
        rules._fail(f"{label} is not chronologically ordered")


def _domain_window(
    context: _Context,
    domain: str,
    observation_artifact: QualificationArtifact,
    controls: Mapping[str, Any],
) -> None:
    window = rules._document(context.results[domain])["evaluation"].get("window")
    if window is None:
        if controls["metric_definitions"]:
            rules._fail(f"domain {domain} metric assessment has no captured measurement window")
        return
    if controls["metric_definitions"] and window["timestamp_encoding"] != "unix_ns":
        rules._fail(f"domain {domain} OTLP metric assessment requires unix_ns timestamps")
    observation = rules._document(observation_artifact)
    source_window = observation.get("measurement_window")
    if source_window is None:
        rules._fail(f"domain {domain} assessment window has no captured measurement window")
    rules._require_equal(
        f"domain {domain} assessment clock", source_window["clock"], window["clock"]
    )
    rules._require_equal(
        f"domain {domain} timestamp encoding",
        source_window["timestamp_encoding"],
        window["timestamp_encoding"],
    )
    rules._require_equal(
        f"domain {domain} captured measurement clock",
        context.run["time_authority"],
        source_window["clock"],
    )
    if not (
        source_window["start_ns"]
        <= window["start_ns"]
        < window["end_ns"]
        <= source_window["end_ns"]
    ):
        rules._fail(f"domain {domain} assessment window exceeds its actual source interval")


_NATIVE_POLICY_ASSERTIONS = frozenset(
    f"policy-native-{name}"
    for name in (
        "artifact-size",
        "archive-size",
        "upload-lag",
        "upload-mode",
        "retention",
        "remote-sink",
        "required-sink",
    )
)


def _domain_assertion_registry(context: _Context, domain: str, controls: Mapping[str, Any]) -> None:
    result = rules._document(context.results[domain])
    core = {
        item["assertion_id"] for item in result["assertion_results"] if item["source"] == "core"
    }
    expected = {item["assertion_id"] for item in controls["assertions"]}
    if core != expected | _NATIVE_POLICY_ASSERTIONS:
        rules._fail(
            f"result {domain} core assertions differ from declared metrics and native policy"
        )
    namespaces = {item["namespace"] for item in controls["evaluator_requirements"]}
    evidence = {item["sha256"] for item in result["evidence"]}
    evidence.update(item["sha256"] for item in controls.get("calibration", {}).get("artifacts", ()))
    for assertion in result["assertion_results"]:
        if assertion["source"] == "product":
            namespace = assertion["namespace"]
            if namespace not in namespaces or not assertion["assertion_id"].startswith(
                f"{namespace}."
            ):
                rules._fail(f"result {domain} product assertion is outside its evaluator namespace")
            if not set(assertion["evidence_sha256"]) <= evidence:
                rules._fail(
                    f"result {domain} product assertion references unknown original evidence"
                )


def _missing_observation_coverage(
    scenario: Mapping[str, Any], expected: Mapping[str, Any]
) -> set[str]:
    missing = {
        f"$.observations.{name}"
        for name, requirement in scenario["profile"]["observations"].items()
        if requirement["requirement"] == "required" and expected[name]["state"] != "measured"
    }
    if not any(value["state"] == "measured" for value in expected.values()):
        missing.add("$.observations")
    return missing


def _missing_criterion_coverage(scenario: Mapping[str, Any], result: Mapping[str, Any]) -> set[str]:
    missing: set[str] = set()
    if not scenario["assertions"] and not any(
        item["source"] == "product" for item in result["assertion_results"]
    ):
        missing.add("$.assertions")
    missing.update(
        f"$.assertions.{item['assertion_id']}"
        for item in result["assertion_results"]
        if item["status"] == "skipped"
    )
    return missing


def _domain_coverage(
    context: _Context,
    domain: str,
    observation_artifact: QualificationArtifact,
    controls: Mapping[str, Any],
) -> None:
    scenario = context.scenario
    result = rules._document(context.results[domain])
    observation = rules._document(observation_artifact)
    expected = _resolved_observations(scenario["profile"], observation)
    rules._require_equal(f"result {domain} observations", expected, result["observations"])
    missing = _missing_observation_coverage(scenario, expected) | _missing_criterion_coverage(
        controls, result
    )
    if not missing <= set(result["unevaluated"]):
        rules._fail(f"result {domain} omits unevaluated source and criterion coverage")
    if missing and worst_status((result["status"], "incomplete")) != result["status"]:
        rules._fail(f"result {domain} is passing despite missing source or criterion coverage")


def _domain_observation_evidence(
    context: _Context, domain: str, observation_artifact: QualificationArtifact
) -> None:
    observation = rules._document(observation_artifact)
    index = rules._document(context.evidence_indexes[domain])
    indexed_observations = [
        item for item in index["artifacts"] if item["kind"] == "acceptance_observation"
    ]
    if len(indexed_observations) != 1 or _identity(indexed_observations[0]) != (
        observation_artifact.sha256,
        observation_artifact.size_bytes,
    ):
        rules._fail(
            f"evidence index {domain} must identify exactly its captured source observation"
        )
    indexed = {
        _identity(item) for item in index["artifacts"] if item["kind"] != "acceptance_observation"
    }
    if (
        observation.get("native_model") is not None
        and _identity(observation["native_model"]) not in indexed
    ):
        rules._fail(f"source observation {domain} loaded model is absent from its original index")
    referenced = {_identity(item) for item in observation["evidence"]}
    if not referenced <= indexed:
        rules._fail(f"source observation {domain} evidence is absent from its original index")
    for name, value in observation["observations"].items():
        if "evidence" in value and _identity(value["evidence"]) not in referenced:
            rules._fail(f"source observation {domain} {name} evidence is not declared")
    for reference in observation["evidence"]:
        _retained_reference(context, reference, f"observation {domain} evidence")


def _domain_assessment_retention(context: _Context, domain: str) -> None:
    assessment = rules._document(context.results[domain])["evaluation"]
    for reference, label in (
        (assessment["method"]["configuration"], "method configuration"),
        (assessment["environment"], "assessment environment"),
        *(
            (item, "selected calibration")
            for item in assessment.get("calibration", {}).get("artifacts", ())
        ),
    ):
        artifact = rules._require_raw(
            context.grouped,
            reference["sha256"],
            f"domain {domain} {label}",
            kinds=("other_evidence",),
            size_bytes=reference["size_bytes"],
        )
        if label != "selected calibration" and (artifact.sha256, artifact.size_bytes) in {
            _identity(item)
            for index_artifact in context.evidence_indexes.values()
            for item in rules._document(index_artifact)["artifacts"]
        }:
            rules._fail(f"domain {domain} {label} must be separate from original evidence")


def _assessment_registry(context: _Context) -> None:
    results = [rules._document(artifact) for artifact in context.results.values()]
    first = results[0]["evaluation"]
    for result in results[1:]:
        assessment = result["evaluation"]
        for field in ("implementation", "version"):
            rules._require_equal(
                f"assessment method {field}", first["method"][field], assessment["method"][field]
            )
        for label, expected, actual in (
            (
                "method configuration",
                first["method"]["configuration"],
                assessment["method"]["configuration"],
            ),
            ("environment", first["environment"], assessment["environment"]),
        ):
            rules._require_equal(f"assessment {label}", _identity(expected), _identity(actual))


def _configuration(context: _Context) -> None:
    def references(value: Any) -> None:
        if isinstance(value, Mapping):
            if {"sha256", "size_bytes", "uri"} <= set(value):
                _retained_reference(context, value, "native profile configuration or model")
            else:
                for child in value.values():
                    references(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                references(child)

    references(context.scenario["profile"])
    references(context.scenario.get("native_model"))
    clock_configuration = context.run["time_authority"].get("configuration_sha256")
    if clock_configuration is not None:
        rules._require_raw(context.grouped, clock_configuration, "original clock configuration")
    if context.grouped.get("execution_permit") or context.grouped.get("execution_verification"):
        rules._fail("non-physical qualification must not include physical authorization subjects")


def _evidence(context: _Context) -> None:
    indexes = {}
    for domain, artifact in context.evidence_indexes.items():
        document = rules._document(artifact)
        indexes[domain] = replace(
            artifact,
            document={
                **document,
                "artifacts": [
                    item
                    for item in document["artifacts"]
                    if item["kind"] != "acceptance_observation"
                ],
            },
        )
    rules._validate_evidence(context.grouped, indexes, context.recording_summaries)


def _transport(context: _Context) -> None:
    if context.aggregate["cross_domain_e2e"]["status"] != "unevaluated" or any(
        context.grouped.get(kind)
        for kind in (
            "transport_qualification",
            "causal_chain_contract",
            "channel_contract",
            "channel_observation",
            "clock_relation",
        )
    ):
        rules._fail(
            "transport-qualification-result.v1 does not support native v2 execution profiles"
        )


def inspect_native_links(
    artifacts: Sequence[QualificationArtifact],
    context: _Context,
    diagnostics: list[QualificationDiagnostic],
) -> QualificationReport:
    from robotics_runtime_contracts._qualification_checks import (
        _aggregate_results,
        _Check,
        _identity_checks,
        _run_check,
    )

    try:
        observations = _observations(context)
    except ContractError as error:
        diagnostics.append(
            QualificationDiagnostic(
                error.error_id, str(error), "native.observations", json_path=error.json_path
            )
        )
        return QualificationReport(tuple(artifacts), tuple(diagnostics), blocked_checks=("links",))

    for check in _identity_checks(context):
        _run_check(check, diagnostics)
    domains_valid = _run_check(
        _Check("native.domains", partial(_domains, context, observations)), diagnostics
    )
    if domains_valid:
        for domain, artifact in observations.items():
            _run_check(
                _Check(
                    "native.domain",
                    partial(_domain, context, domain, artifact),
                    artifact.subject_name,
                ),
                diagnostics,
            )
        for check in (
            _Check("native.assessments", partial(_assessment_registry, context)),
            _Check("native.configuration", partial(_configuration, context)),
            _Check("native.evidence", partial(_evidence, context)),
            _Check(
                "native.receipts",
                partial(
                    rules._validate_receipts,
                    context.grouped,
                    context.scenario,
                    context.run["run_id"],
                    context.evidence_indexes,
                    context.run["created_at"],
                    context.aggregate["generated_at"],
                ),
            ),
            _Check("native.transport", partial(_transport, context)),
        ):
            _run_check(check, diagnostics)
    _run_check(_Check("aggregate.results", partial(_aggregate_results, context)), diagnostics)
    return QualificationReport(
        tuple(artifacts),
        tuple(diagnostics),
        context.run["run_id"],
        context.aggregate["generated_at"],
        () if domains_valid else ("native.domain.links",),
    )
