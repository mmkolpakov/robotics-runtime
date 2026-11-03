from __future__ import annotations

import platform
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime
from hashlib import sha256
from importlib.metadata import distributions
from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from packaging.utils import canonicalize_name
from robotics_runtime_contracts import dumps_canonical, validate_document, worst_status
from robotics_runtime_contracts._timestamps import parse_timestamp_ns
from robotics_runtime_contracts.writers import protect_inputs, write_bytes_atomically

from robotics_acceptance_harness import __version__
from robotics_acceptance_harness._oci_executor import run_oci_evaluator
from robotics_acceptance_harness._oci_operator import _OCIProfile
from robotics_acceptance_harness._oci_request import build_oci_request
from robotics_acceptance_harness.documents import (
    BundleValidationError,
    LoadedDocument,
    load_document_bytes,
)
from robotics_acceptance_harness.evaluation import (
    EvaluationContext,
    EvaluationError,
    ProductEvaluator,
    evaluate_acceptance,
)
from robotics_acceptance_harness.evaluator_json import decode_evaluator_response
from robotics_acceptance_harness.evaluator_trust import (
    DEFAULT_TRUST_LIMITS,
    AuthenticatedInstallation,
    read_once,
)
from robotics_acceptance_harness.metrics import AssertionEvaluation
from robotics_acceptance_harness.receipts import VerifiedReceiptSet
from robotics_acceptance_harness.result import format_utc_datetime


def _reference_key(reference: Mapping[str, Any]) -> tuple[str, str, int]:
    return str(reference["uri"]), str(reference["sha256"]), int(reference["size_bytes"])


def _references(value: object) -> Iterator[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        if {"uri", "sha256", "size_bytes"} <= value.keys():
            yield value
        else:
            for child in value.values():
                yield from _references(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _references(child)


def _validate_source(context: EvaluationContext, source: LoadedDocument) -> None:
    expected = {
        "run_id": context.run_id,
        "domain_id": context.domain_id,
        "scenario_id": context.scenario["scenario_id"],
        "scenario_sha256": context.bundle.scenario.sha256,
        "runtime_manifest_sha256": context.bundle.runtime.sha256,
    }
    for key, value in expected.items():
        if source.data[key] != value:
            raise BundleValidationError(
                f"$.observation.{key}", "identifies another execution input"
            )
    if source.data.get("native_model") != context.runtime.get("native_model"):
        raise BundleValidationError(
            "$.observation.native_model", "does not identify the model bytes actually loaded"
        )
    declared = context.scenario["profile"]["observations"]
    if set(source.data["observations"]) - set(declared):
        raise BundleValidationError(
            "$.observations", "includes observations outside the selected profile"
        )
    indexed = {_reference_key(reference) for reference in context.evidence.links}
    retained = (
        context.scenario["profile"],
        context.runtime.get("native_model"),
        source.data["evidence"],
    )
    for reference in _references(retained):
        if _reference_key(reference) not in indexed:
            raise BundleValidationError(
                "$.evidence", "a native source binding is absent from verified evidence"
            )


def _observations(context: EvaluationContext, source: LoadedDocument) -> dict[str, Any]:
    supplied = source.as_dict()["observations"]
    observations: dict[str, Any] = {}
    for name, requirement in context.scenario["profile"]["observations"].items():
        if requirement["requirement"] == "not_applicable":
            declared = {"state": "not_applicable", "reason": requirement["reason"]}
            observed = supplied.get(name, declared)
            if observed != declared:
                raise BundleValidationError(
                    f"$.observations.{name}", "contradicts declared inapplicability"
                )
        else:
            observed = supplied.get(
                name, {"state": "unobserved", "reason": "producer supplied no observation"}
            )
            if observed["state"] == "not_applicable":
                raise BundleValidationError(
                    f"$.observations.{name}", "inapplicability is not declared by the profile"
                )
        observations[name] = observed
    return observations


def _measurement_window(
    context: EvaluationContext, source: LoadedDocument, run_context: LoadedDocument
) -> dict[str, Any] | None:
    window = source.as_dict().get("measurement_window")
    if window is None:
        if context.method_controls["metric_definitions"]:
            raise BundleValidationError(
                "$.measurement_window", "metric assessment requires a captured source window"
            )
        return None
    if window["clock"] != dict(run_context.data["time_authority"]):
        raise BundleValidationError(
            "$.measurement_window.clock", "differs from the run's declared measurement clock"
        )
    if context.method_controls["metric_definitions"] and window["timestamp_encoding"] != "unix_ns":
        raise BundleValidationError(
            "$.measurement_window", "OTLP metric assessment requires unix_ns source timestamps"
        )
    if (
        not window["start_ns"]
        <= context.window_start_ns
        < context.window_end_ns
        <= window["end_ns"]
    ):
        raise BundleValidationError(
            "$.evaluation.window", "must lie within the captured source window"
        )
    return {
        **window,
        "start_ns": context.window_start_ns,
        "end_ns": context.window_end_ns,
    }


def _artifact(
    content: Mapping[str, Any],
    path: Path,
    *,
    raw: bytes | None = None,
    media_type: str = "application/json",
) -> dict[str, Any]:
    raw = dumps_canonical(dict(content)) if raw is None else raw
    destination = write_bytes_atomically(raw, path)
    return {
        "uri": destination.as_uri(),
        "sha256": sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "media_type": media_type,
    }


def _installed_distribution_inventory() -> dict[str, str]:
    inventory: dict[str, str] = {}
    for distribution in distributions():
        declared_name = distribution.metadata.get("Name")
        if not declared_name:
            raise BundleValidationError(
                "$.evaluation.environment", "installed distribution has no name"
            )
        name = canonicalize_name(declared_name)
        installed_version = distribution.version
        previous = inventory.get(name)
        if previous is not None and previous != installed_version:
            raise BundleValidationError(
                "$.evaluation.environment",
                f"installed distribution {name} has ambiguous versions",
            )
        inventory[name] = installed_version
    return dict(sorted(inventory.items()))


def _evaluation_environment(
    path: Path, profile: _OCIProfile | None = None, config_digests: Mapping[str, str] | None = None
) -> dict[str, Any]:
    environment: dict[str, Any] = {
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "packages": _installed_distribution_inventory(),
    }
    if profile is not None:
        environment["oci"] = {
            "evaluators": [
                {
                    "namespace": namespace,
                    "manifest_sha256": binding["manifest_sha256"],
                    "config_sha256": (config_digests or {})[namespace],
                    "platform": dict(binding["platform"]),
                }
                for namespace, binding in sorted(profile.evaluators.items())
            ],
            "verifier_sha256": profile.verifier.executable_sha256,
            "public_key_sha256": profile.verifier.public_key_sha256,
            "trusted_root_sha256": profile.verifier.trusted_root_sha256,
            "verifier_version": profile.verifier.version,
            "engine_sha256": profile.engine["executable_sha256"],
            "engine_version": profile.engine["version"],
            "containers_conf_sha256": profile.engine["containers_conf"]["sha256"],
            "storage_conf_sha256": profile.engine["storage_conf"]["sha256"],
            "limits": dict(profile.limits),
        }
    return _artifact(environment, path)


def _load_observation(context: EvaluationContext) -> LoadedDocument:
    matches: list[LoadedDocument] = []
    for source_path, reference in context.evidence.local_files.items():
        if reference["kind"] != "acceptance_observation":
            continue
        raw = context.evidence.read_local(
            source_path, max_raw_evidence_bytes=context.max_raw_evidence_bytes
        )
        source = load_document_bytes(
            raw, source=source_path, expected_role="acceptance_observation"
        )
        if source.schema_version != "acceptance-observation.v2":
            raise BundleValidationError(
                "$.observation.schema_version", "native assessment requires v2 observations"
            )
        if (
            source.data["run_id"] == context.run_id
            and source.data["domain_id"] == context.domain_id
        ):
            matches.append(source)
    if len(matches) != 1:
        raise BundleValidationError(
            "$.observations",
            "native assessment requires exactly one indexed observation for this run and domain",
        )
    return matches[0]


def _protect_source_inputs(
    context: EvaluationContext, run_context: LoadedDocument, destination: Path
) -> None:
    inputs = [
        context.bundle.scenario.path,
        context.bundle.runtime.path,
        run_context.path,
        context.evidence.index.path,
        *context.evidence.local_files,
    ]
    if context.assessment_controls is not None:
        inputs.append(context.assessment_controls.path)
        from urllib.parse import urlsplit
        from urllib.request import url2pathname

        for reference in context.method_controls["calibration"].get("artifacts", ()):
            inputs.append(Path(url2pathname(urlsplit(reference["uri"]).path)))
    for document in (context.bundle.permit, context.bundle.verification, context.original_result):
        if document is not None:
            inputs.append(document.path)
    for name in (
        "evaluation-method.json",
        "evaluation-environment.json",
        "acceptance-result.json",
        "junit.xml",
    ):
        protect_inputs(destination / name, inputs)


def _criterion_evidence(context: EvaluationContext, item: AssertionEvaluation) -> tuple[str, ...]:
    if item.status not in {"passed", "failed"}:
        return ()
    if item.source == "product":
        return tuple(sorted(set(item.evidence_sha256) & context.original_evidence_sha256))
    if item.observed_value is None or context.metric_evidence_sha256 is None:
        return ()
    return (context.metric_evidence_sha256,)


def _criterion_coverage(
    context: EvaluationContext, assertions: tuple[AssertionEvaluation, ...]
) -> dict[str, Any]:
    declared = {item["assertion_id"] for item in context.method_controls["assertions"]}
    if context.method_controls.get("schema_version") == "assessment-controls.v1":
        declared.update(
            identifier
            for evaluator in context.method_controls["evaluator_requirements"]
            for identifier in evaluator["expected_assertion_ids"]
        )
    criteria = {
        item.assertion_id: item
        for item in assertions
        if item.source == "product" or item.assertion_id in declared
    }
    covered, uncovered = [], []
    for identifier in sorted(set(criteria) | declared):
        item = criteria.get(identifier)
        evidence = _criterion_evidence(context, item) if item is not None else ()
        if evidence:
            covered.append({"assertion_id": identifier, "evidence_sha256": list(evidence)})
        else:
            uncovered.append(
                {
                    "assertion_id": identifier,
                    "reason": (
                        item.message or "method has no observed source-bound outcome"
                        if item is not None
                        else "method returned no outcome"
                    ),
                }
            )
    return {"covered_assertions": covered, "uncovered_assertions": uncovered}


def _original_execution(
    context: EvaluationContext,
    run_context: LoadedDocument,
    source: LoadedDocument,
    started_at: datetime,
) -> dict[str, Any]:
    original = {
        "acceptance_run_sha256": run_context.sha256,
        "observation_sha256": source.sha256,
        "evidence_index_sha256": context.evidence.index.sha256,
        "started_at": source.data["started_at"],
        "finished_at": source.data["finished_at"],
    }
    baseline = context.original_result
    if baseline is None:
        return original
    if context.assessment_controls is None or baseline.schema_version != "acceptance-result.v2":
        raise BundleValidationError(
            "$.original_result", "requires selected native v2 controls and result"
        )
    expected = {
        "run_id": context.run_id,
        "domain_id": context.domain_id,
        "scenario_id": context.scenario["scenario_id"],
        "scenario_sha256": context.bundle.scenario.sha256,
        "runtime_manifest_sha256": context.bundle.runtime.sha256,
        "execution": context.runtime["execution"],
        "profile": context.scenario["profile"],
        "native_model": source.data.get("native_model"),
    }
    for key, value in expected.items():
        if baseline.data.get(key) != value:
            raise BundleValidationError(
                f"$.original_result.{key}", "differs from original execution"
            )
    for key, value in original.items():
        if baseline.data["original_execution"].get(key) != value:
            raise BundleValidationError(
                f"$.original_result.original_execution.{key}", "differs from original execution"
            )
    if parse_timestamp_ns(baseline.data["evaluation"]["finished_at"]) > parse_timestamp_ns(
        format_utc_datetime(started_at)
    ):
        raise BundleValidationError(
            "$.original_result.evaluation",
            "original assessment finishes after new assessment starts",
        )
    return {**original, "original_result_sha256": baseline.sha256}


class _NativeAdmission(TypedDict):
    receipts: VerifiedReceiptSet | None
    authentications: Mapping[str, AuthenticatedInstallation] | None
    oci_profile: _OCIProfile | None


class _OCIInputs(TypedDict):
    documents: Mapping[str, LoadedDocument]
    method: Mapping[str, Any]
    window: Mapping[str, Any] | None
    destination: Path
    config_digests: dict[str, str]


def evaluate_native(
    context: EvaluationContext,
    run_context: LoadedDocument,
    output_dir: str | Path,
    evaluator_receipts: VerifiedReceiptSet | None,
    evaluator_authentications: Mapping[str, AuthenticatedInstallation] | None = None,
) -> dict[str, Any]:
    """Assess captured native observations without executing or rewriting their source."""
    return _evaluate_native(
        context,
        run_context,
        output_dir,
        {
            "receipts": evaluator_receipts,
            "authentications": evaluator_authentications,
            "oci_profile": None,
        },
    )


def _validate_native_admission(
    context: EvaluationContext, admission: _NativeAdmission, marked: bool
) -> None:
    requirements = context.method_controls["evaluator_requirements"]
    if marked and context.original_result is None:
        raise EvaluationError("versioned assessment controls require an original v2 result")
    if marked and requirements and admission["oci_profile"] is None:
        raise EvaluationError("OCI evaluator execution requires an operator profile")
    if not marked and admission["oci_profile"] is not None:
        raise EvaluationError("OCI operator profile requires versioned assessment controls")
    if marked:
        _verify_oci_provenance(requirements, admission["oci_profile"], admission["receipts"])


class _NativeEvaluationInputs(TypedDict):
    method: Mapping[str, Any]
    window: Mapping[str, Any] | None
    destination: Path
    config_digests: dict[str, str]


def _selected_native_evaluators(
    context: EvaluationContext,
    profile: _OCIProfile | None,
    run_context: LoadedDocument,
    source: LoadedDocument,
    inputs: _NativeEvaluationInputs,
) -> tuple[tuple[str, ProductEvaluator], ...] | None:
    if context.method_controls.get("schema_version") != "assessment-controls.v1":
        return None
    if not context.method_controls["evaluator_requirements"]:
        return ()
    assert profile is not None
    documents = {
        "acceptance_scenario": context.bundle.scenario,
        "runtime_manifest": context.bundle.runtime,
        "acceptance_run": run_context,
        "acceptance_observation": source,
        "evidence_index": context.evidence.index,
    }
    if context.original_result is not None:
        documents["acceptance_result"] = context.original_result
    return _oci_product_evaluators(context, profile, {"documents": documents, **inputs})


def _evaluate_native(
    context: EvaluationContext,
    run_context: LoadedDocument,
    output_dir: str | Path,
    admission: _NativeAdmission,
) -> dict[str, Any]:
    marked = context.method_controls.get("schema_version") == "assessment-controls.v1"
    _validate_native_admission(context, admission, marked)
    source = _load_observation(context)
    _validate_source(context, source)
    observations = _observations(context, source)
    measurement_window = _measurement_window(context, source, run_context)
    if "clock" in context.scenario["profile"]:
        clock = context.scenario["profile"]["clock"]
        if any(
            clock[key] != run_context.data["time_authority"][key] for key in ("kind", "source_id")
        ):
            raise BundleValidationError(
                "$.profile.clock", "differs from the original run's declared clock"
            )
    destination = Path(output_dir).expanduser().resolve()
    _protect_source_inputs(context, run_context, destination)
    started_at = datetime.now(UTC)
    original = _original_execution(context, run_context, source, started_at)
    method = context.method_controls
    selected = context.assessment_controls
    configuration = _artifact(
        selected.as_dict()
        if selected is not None
        else {
            key: context.bundle.scenario.as_dict()[key]
            for key in (
                "metric_definitions",
                "assertions",
                "evaluator_requirements",
                "evidence_policy",
            )
        },
        destination / "evaluation-method.json",
        raw=selected.raw if selected is not None else None,
        media_type="application/octet-stream" if selected is not None else "application/json",
    )
    config_digests: dict[str, str] = {}
    environment = (
        _evaluation_environment(destination / "evaluation-environment.json")
        if admission["oci_profile"] is None
        else None
    )
    method_metadata = {
        "implementation": "robotics_acceptance_harness.evaluate_acceptance",
        "version": __version__,
        "configuration": configuration,
    }
    evaluators = _selected_native_evaluators(
        context,
        admission["oci_profile"],
        run_context,
        source,
        {
            "method": method_metadata,
            "window": measurement_window,
            "destination": destination,
            "config_digests": config_digests,
        },
    )
    assertions = evaluate_acceptance(
        context,
        evaluators=evaluators,
        evaluator_receipts=admission["receipts"],
        evaluator_authentications=admission["authentications"],
    )
    if environment is None:
        environment = _evaluation_environment(
            destination / "evaluation-environment.json", admission["oci_profile"], config_digests
        )
    finished_at = datetime.now(UTC)
    unevaluated = {
        f"$.observations.{name}"
        for name, requirement in context.scenario["profile"]["observations"].items()
        if requirement["requirement"] == "required"
        and observations[name]["state"] in {"unobserved", "invalid"}
    }
    if not any(item["state"] == "measured" for item in observations.values()):
        unevaluated.add("$.observations")
    if not method["assertions"] and not any(item.source == "product" for item in assertions):
        unevaluated.add("$.assertions")
    coverage = _criterion_coverage(context, assertions)
    unevaluated.update(
        f"$.assertions.{item['assertion_id']}" for item in coverage["uncovered_assertions"]
    )
    unevaluated.update(
        f"$.assertions.{item.assertion_id}" for item in assertions if item.status == "skipped"
    )
    statuses = ["incomplete" if item.status == "skipped" else item.status for item in assertions]
    if unevaluated:
        statuses.append("incomplete")
    result: dict[str, Any] = {
        "schema_version": "acceptance-result.v3" if marked else "acceptance-result.v2",
        "result_id": f"result-{uuid4()}",
        "run_id": context.run_id,
        "scenario_id": context.scenario["scenario_id"],
        "domain_id": context.domain_id,
        "verdict_scope": "domain",
        "evaluation_mode": "offline",
        "scenario_sha256": context.bundle.scenario.sha256,
        "runtime_manifest_sha256": context.bundle.runtime.sha256,
        "execution": context.bundle.runtime.as_dict()["execution"],
        "profile": context.bundle.scenario.as_dict()["profile"],
        "original_execution": original,
        "evaluation": {
            "method": method_metadata,
            "environment": environment,
            "calibration": (
                selected.as_dict()["calibration"]
                if selected is not None
                else {
                    "state": "unobserved",
                    "reason": "original method has no explicit calibration selection",
                }
            ),
            "coverage": coverage,
            **({"window": measurement_window} if measurement_window is not None else {}),
            "started_at": format_utc_datetime(started_at),
            "finished_at": format_utc_datetime(finished_at),
        },
        "observations": observations,
        "unevaluated": sorted(unevaluated),
        "status": worst_status(statuses),
        "assertion_results": [
            {
                "assertion_id": item.assertion_id,
                "source": item.source,
                "status": item.status,
                "observed_value": item.observed_value,
                "unit": item.unit,
                **({"message": item.message} if item.message else {}),
                **({"namespace": item.namespace} if item.namespace else {}),
                **({"evidence_sha256": list(item.evidence_sha256)} if item.evidence_sha256 else {}),
            }
            for item in assertions
        ],
        "evaluators": (
            selected.as_dict()["evaluator_requirements"]
            if marked and selected is not None
            else [dict(item) for item in method["evaluator_requirements"]]
        ),
        "evidence": [dict(item) for item in context.evidence.links],
    }
    if "native_model" in context.runtime:
        result["native_model"] = context.bundle.runtime.as_dict()["native_model"]
    validate_document(result)
    return result


def _oci_product_evaluators(
    context: EvaluationContext, profile: _OCIProfile, inputs: _OCIInputs
) -> tuple[tuple[str, ProductEvaluator], ...]:
    def bind(requirement: Mapping[str, Any]) -> tuple[str, ProductEvaluator]:
        namespace = str(requirement["namespace"])
        expected_ids = tuple(str(item) for item in requirement["expected_assertion_ids"])

        def evaluate(current: EvaluationContext) -> tuple[AssertionEvaluation, ...]:
            attempt = inputs["destination"] / f"oci-attempt-{uuid4()}"
            attempt.mkdir(mode=0o700)
            packet = build_oci_request(
                current,
                documents=inputs["documents"],
                method=inputs["method"],
                requirement=requirement,
                options={
                    "window": inputs["window"],
                    "attempt_dir": attempt,
                    "max_input_bytes": profile.limits["input_bytes"],
                },
            )
            response = run_oci_evaluator(profile, namespace, packet, attempt / "inputs", attempt)
            config = read_once(attempt / "config.json", DEFAULT_TRUST_LIMITS.max_bundle_bytes)
            inputs["config_digests"][namespace] = sha256(config).hexdigest()
            return decode_evaluator_response(
                response,
                request_sha256=sha256(packet).hexdigest(),
                namespace=namespace,
                expected_assertion_ids=expected_ids,
                allowed_evidence_sha256=current.evidence_sha256,
            )

        return namespace, evaluate

    return tuple(bind(item) for item in context.method_controls["evaluator_requirements"])


def _verify_oci_provenance(
    requirements: Sequence[Mapping[str, Any]],
    profile: _OCIProfile | None,
    receipts: VerifiedReceiptSet | None,
) -> None:
    verified = receipts or VerifiedReceiptSet({})
    namespaces = {str(requirement["namespace"]) for requirement in requirements}
    if requirements and (profile is None or set(profile.evaluators) != namespaces):
        raise EvaluationError("OCI operator profile differs from declared evaluator namespaces")
    for requirement in requirements:
        assert profile is not None
        binding = profile.evaluators[str(requirement["namespace"])]
        if "sha256:" + binding["manifest_sha256"] != requirement["execution_subject"]["digest"]:
            raise EvaluationError("OCI operator manifest differs from the declared digest")
    expected = {
        str(requirement["execution_subject"]["provenance_receipt_sha256"])
        for requirement in requirements
        if "provenance_receipt_sha256" in requirement["execution_subject"]
    }
    if set(verified.by_digest) != expected:
        raise EvaluationError("OCI provenance receipts must match declared evaluator requirements")
    for requirement in requirements:
        subject = requirement["execution_subject"]
        receipt_digest = subject.get("provenance_receipt_sha256")
        if receipt_digest is None:
            continue
        namespace = str(requirement["namespace"])
        if profile is None:
            raise EvaluationError("OCI evaluator execution requires an operator profile")
        binding = profile.evaluators[namespace]
        raw = read_once(binding["manifest"], DEFAULT_TRUST_LIMITS.max_bundle_bytes)
        digest = sha256(raw).hexdigest()
        if "sha256:" + digest != subject["digest"]:
            raise EvaluationError("OCI provenance manifest differs from the declared digest")
        verified.verify_artifact(str(receipt_digest), {"sha256": digest, "size_bytes": len(raw)})
