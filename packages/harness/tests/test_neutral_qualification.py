from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from robotics_runtime_contracts import ContractError
from robotics_runtime_contracts.qualification import (
    QualificationError,
    validate_qualification_artifacts,
)
from robotics_runtime_contracts.statements import create_qualification_statement
from robotics_runtime_contracts.status import worst_status

from robotics_acceptance_harness.aggregate import (
    aggregate_results,
    evaluate_transport_qualification,
)
from robotics_acceptance_harness.documents import BundleValidationError

POLICY_IDS = tuple(
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

RUN_ID = "run-01234567-89ab-4def-8123-456789abcdef"
T0 = "2026-10-10T12:00:00+00:00"
T1 = "2026-10-10T12:00:01+00:00"
T2 = "2026-10-10T12:00:02+00:00"
T3 = "2026-10-10T12:00:03+00:00"
T4 = "2026-10-10T12:00:04+00:00"
T5 = "2026-10-10T12:00:05+00:00"
T6 = "2026-10-10T12:00:06+00:00"


def _write(path: Path, value: Any) -> Path:
    path.write_text(json.dumps(value, sort_keys=True) + "\n")
    return path


def _document(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text()))


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _reference(path: Path) -> dict[str, Any]:
    return {
        "uri": path.as_uri(),
        "sha256": _digest(path),
        "size_bytes": path.stat().st_size,
        "media_type": "application/json",
    }


def _indexed(path: Path, artifact_id: str, kind: str) -> dict[str, Any]:
    return {
        **_reference(path),
        "artifact_id": artifact_id,
        "kind": kind,
        "retention_class": "pull-request-7d",
        "storage_state": "local",
        "local_path": str(path),
    }


def _archive(
    tmp_path: Path, domains: tuple[str, ...] = ("primary",), *, native_model: bool = False
) -> list[str]:
    state = _write(tmp_path / "native-state.json", {"native_final_state": "completed", "error": 0})
    method = tmp_path / "method.json"
    environment = _write(tmp_path / "environment.json", {"python": "3.12", "platform": "test"})
    profile: dict[str, Any] = {
        "profile_id": "org.example.native",
        "channels": [],
        "clock": {"kind": "external", "source_id": "system-utc"},
        "observations": {
            "error": {"kind": "postcondition", "requirement": "required"},
            "clock-delivery": {
                "kind": "clock",
                "requirement": "not_applicable",
                "reason": "local-file profile has no delivery latency",
            },
        },
    }
    scenario = _write(
        tmp_path / "scenario.json",
        {
            "schema_version": "acceptance-scenario.v2",
            "scenario_id": "native-qualification",
            "execution": {"target_environment": "software", "data_source": "local-file"},
            "profile": profile,
            "metric_definitions": [],
            "assertions": [],
            "evaluator_requirements": [],
            "evidence_policy": {
                "max_artifact_size_bytes": 65536,
                "max_archive_size_bytes": 131072,
                "max_upload_lag_sec": 0,
                "upload_mode": "local_only",
                "retention_class": "pull-request-7d",
                "remote_sink_allowed": False,
            },
        },
    )
    _write(
        method,
        {
            key: _document(scenario)[key]
            for key in (
                "metric_definitions",
                "assertions",
                "evaluator_requirements",
                "evidence_policy",
            )
        },
    )
    model = _write(tmp_path / "model.json", {"model": "native-counter"})
    if native_model:
        candidate = _document(scenario)
        candidate["native_model"] = _reference(model)
        _write(scenario, candidate)
    run = _write(
        tmp_path / "run.json",
        {
            "schema_version": "acceptance-run.v1",
            "run_id": RUN_ID,
            "created_at": T0,
            "scenario_id": "native-qualification",
            "scenario_sha256": _digest(scenario),
            "time_authority": profile["clock"],
            "domains": [{"domain_id": domain, "role": "worker"} for domain in domains],
        },
    )
    specs = [
        f"scenario:scenario.json={scenario}",
        f"acceptance_run:acceptance-run.json={run}",
        f"other_evidence:evidence/native-state.json={state}",
        f"other_evidence:evaluation/method.json={method}",
        f"other_evidence:evaluation/environment.json={environment}",
    ]
    if native_model:
        specs.append(f"other_evidence:evidence/model.json={model}")
    results = []
    for domain in domains:
        runtime = _write(
            tmp_path / f"runtime-{domain}.json",
            {
                "schema_version": "runtime-manifest.v2",
                "runtime_id": f"runtime-{domain}",
                "generated_at": T1,
                "scenario_sha256": _digest(scenario),
                "execution": _document(scenario)["execution"],
                "profile": profile,
                "evaluator_bindings": [],
            },
        )
        if native_model:
            candidate = _document(runtime)
            candidate["native_model"] = _reference(model)
            _write(runtime, candidate)
        source_observations = {
            "error": {"state": "measured", "value": 0, "evidence": _reference(state)},
            "clock-delivery": {
                "state": "not_applicable",
                "reason": profile["observations"]["clock-delivery"]["reason"],
            },
        }
        observation = _write(
            tmp_path / f"observation-{domain}.json",
            {
                "schema_version": "acceptance-observation.v2",
                "observation_id": f"observed-{domain}",
                "run_id": RUN_ID,
                "scenario_id": "native-qualification",
                "domain_id": domain,
                "scenario_sha256": _digest(scenario),
                "runtime_manifest_sha256": _digest(runtime),
                "started_at": T2,
                "finished_at": T3,
                "observations": source_observations,
                "evidence": [_reference(state)],
            },
        )
        if native_model:
            candidate = _document(observation)
            candidate["native_model"] = _reference(model)
            _write(observation, candidate)
        index = _write(
            tmp_path / f"index-{domain}.json",
            {
                "schema_version": "evidence-index.v1",
                "run_id": RUN_ID,
                "generated_at": T4,
                "finalized": True,
                "policy_observation": {
                    "recording_mode": "native-file",
                    "compression": "none",
                    "retention_class": "pull-request-7d",
                    "upload_mode": "local_only",
                    "remote_sink_used": False,
                    "spool_peak_size_bytes": 0,
                    "upload_lag_max_sec": 0,
                },
                "artifacts": [
                    _indexed(state, "native-state", "native_state"),
                    _indexed(observation, "source-observation", "acceptance_observation"),
                ],
            },
        )
        if native_model:
            candidate = _document(index)
            candidate["artifacts"].append(_indexed(model, "native-model", "native_model"))
            _write(index, candidate)
        evidence = [
            {
                key: value
                for key, value in item.items()
                if key not in {"storage_state", "local_path"}
            }
            for item in _document(index)["artifacts"]
        ]
        result = _write(
            tmp_path / f"result-{domain}.json",
            {
                "schema_version": "acceptance-result.v2",
                "result_id": f"result-{uuid4()}",
                "run_id": RUN_ID,
                "scenario_id": "native-qualification",
                "domain_id": domain,
                "scenario_sha256": _digest(scenario),
                "runtime_manifest_sha256": _digest(runtime),
                "verdict_scope": "domain",
                "evaluation_mode": "offline",
                "execution": _document(scenario)["execution"],
                "profile": profile,
                "original_execution": {
                    "acceptance_run_sha256": _digest(run),
                    "observation_sha256": _digest(observation),
                    "evidence_index_sha256": _digest(index),
                    "started_at": T2,
                    "finished_at": T3,
                },
                "evaluation": {
                    "method": {
                        "implementation": "org.example.native-evaluation",
                        "version": "1",
                        "configuration": _reference(method),
                    },
                    "environment": _reference(environment),
                    "started_at": T4,
                    "finished_at": T5,
                },
                "observations": source_observations,
                "unevaluated": ["$.assertions"],
                "assertion_results": [
                    {
                        "assertion_id": name,
                        "source": "core",
                        "status": "passed",
                        "observed_value": 1,
                        "unit": "1",
                    }
                    for name in POLICY_IDS
                ],
                "status": "incomplete",
                "evaluators": [],
                "evidence": evidence,
            },
        )
        if native_model:
            candidate = _document(result)
            candidate["native_model"] = _reference(model)
            _write(result, candidate)
        results.append(result)
        specs.extend(
            [
                f"runtime_manifest:runtime-manifests/{domain}.json={runtime}",
                f"acceptance_observation:observations/{domain}.json={observation}",
                f"evidence_index:evidence-indexes/{domain}.json={index}",
                f"domain_result:results/{domain}.json={result}",
            ]
        )
    aggregate = aggregate_results(
        scenario_path=scenario,
        run_context_path=run,
        result_paths=results,
        output_path=tmp_path / "aggregate.json",
        generated_at=datetime.fromisoformat(T6),
    )
    specs.append(f"acceptance_aggregate:acceptance-aggregate.json={aggregate}")
    return specs


def test_native_chain_reuses_v1_run_aggregate_and_bundle(tmp_path: Path) -> None:
    specs = _archive(tmp_path)
    metadata = validate_qualification_artifacts(specs)
    assert (metadata["run_id"], metadata["generated_at"]) == (RUN_ID, "2026-10-10T12:00:06Z")
    bundle = create_qualification_statement(specs)
    assert bundle["predicate"]["schema_version"] == "qualification-bundle.v1"
    assert "observations/primary.json" in {item["name"] for item in bundle["subject"]}
    assert _document(tmp_path / "run.json")["schema_version"] == "acceptance-run.v1"
    assert _document(tmp_path / "aggregate.json")["schema_version"] == "acceptance-aggregate.v1"


@pytest.mark.parametrize(
    "change",
    [
        "run",
        "scenario",
        "runtime",
        "source",
        "index",
        "observation-domain",
        "original-time",
        "environment",
        "method",
        "profile",
    ],
)
def test_native_qualification_rejects_source_and_assessment_substitution(
    tmp_path: Path, change: str
) -> None:
    specs = _archive(tmp_path)
    result_path = tmp_path / "result-primary.json"
    result = _document(result_path)
    if change in {"run", "source", "index"}:
        field = {
            "run": "acceptance_run_sha256",
            "source": "observation_sha256",
            "index": "evidence_index_sha256",
        }[change]
        result["original_execution"][field] = "a" * 64
    elif change == "scenario":
        result["scenario_sha256"] = "a" * 64
    elif change == "runtime":
        result["runtime_manifest_sha256"] = "a" * 64
    elif change == "observation-domain":
        observation_path = tmp_path / "observation-primary.json"
        observation = _document(observation_path)
        observation["domain_id"] = "foreign"
        _write(observation_path, observation)
    elif change == "original-time":
        result["original_execution"]["started_at"] = T1
    elif change in {"environment", "method"}:
        reference = (
            result["evaluation"]["environment"]
            if change == "environment"
            else result["evaluation"]["method"]["configuration"]
        )
        reference["sha256"] = "a" * 64
    elif change == "profile":
        result["profile"]["profile_id"] = "org.example.foreign"
    _write(result_path, result)
    with pytest.raises(ContractError):
        validate_qualification_artifacts(specs)


def test_native_qualification_requires_actual_raw_evidence(tmp_path: Path) -> None:
    specs = _archive(tmp_path)
    (tmp_path / "native-state.json").write_bytes(b"substituted")
    with pytest.raises(QualificationError, match="retained raw artifact"):
        validate_qualification_artifacts(specs)


def test_native_qualification_requires_captured_source_observation(tmp_path: Path) -> None:
    specs = [item for item in _archive(tmp_path) if not item.startswith("acceptance_observation:")]
    with pytest.raises(QualificationError, match="observation set"):
        validate_qualification_artifacts(specs)


@pytest.mark.parametrize(
    "change", ["method", "configuration", "environment", "model", "run", "clock", "time"]
)
def test_native_aggregate_refuses_incompatible_assessments(tmp_path: Path, change: str) -> None:
    _archive(tmp_path, ("first", "second"))
    path = tmp_path / "result-second.json"
    result = _document(path)
    if change == "method":
        result["evaluation"]["method"]["version"] = "2"
    elif change == "configuration":
        result["evaluation"]["method"]["configuration"]["size_bytes"] += 1
    elif change == "environment":
        result["evaluation"]["environment"]["sha256"] = "a" * 64
    elif change == "model":
        result["native_model"] = _reference(tmp_path / "native-state.json")
    elif change == "run":
        result["original_execution"]["acceptance_run_sha256"] = "a" * 64
    elif change == "clock":
        result["profile"]["clock"]["source_id"] = "foreign-clock"
    elif change == "time":
        result["evaluation"]["started_at"] = T1
    _write(path, result)
    with pytest.raises((ContractError, BundleValidationError)):
        aggregate_results(
            scenario_path=tmp_path / "scenario.json",
            run_context_path=tmp_path / "run.json",
            result_paths=[tmp_path / "result-first.json", path],
            output_path=tmp_path / "refused.json",
            generated_at=datetime.fromisoformat(T6),
        )
    assert not (tmp_path / "refused.json").exists()


def test_native_aggregate_refuses_duplicate_domain(tmp_path: Path) -> None:
    _archive(tmp_path)
    with pytest.raises(BundleValidationError, match="domain results must be unique"):
        aggregate_results(
            scenario_path=tmp_path / "scenario.json",
            run_context_path=tmp_path / "run.json",
            result_paths=[tmp_path / "result-primary.json"] * 2,
            output_path=tmp_path / "refused.json",
        )


def test_native_aggregate_refuses_v1_transport_qualification(tmp_path: Path) -> None:
    _archive(tmp_path)
    with pytest.raises(BundleValidationError, match="does not support native v2"):
        aggregate_results(
            scenario_path=tmp_path / "scenario.json",
            run_context_path=tmp_path / "run.json",
            result_paths=[tmp_path / "result-primary.json"],
            transport_qualification_path=tmp_path / "unused.json",
            output_path=tmp_path / "refused.json",
        )


def test_native_qualification_compares_assessment_environment_and_method(tmp_path: Path) -> None:
    specs = _archive(tmp_path, ("first", "second"))
    result_path = tmp_path / "result-second.json"
    result = _document(result_path)
    result["evaluation"]["method"]["version"] = "2"
    _write(result_path, result)
    with pytest.raises(QualificationError, match="assessment method version"):
        validate_qualification_artifacts(specs)


def _refresh_domain(tmp_path: Path, domain: str = "primary") -> None:
    observation_path = tmp_path / f"observation-{domain}.json"
    index_path = tmp_path / f"index-{domain}.json"
    result_path = tmp_path / f"result-{domain}.json"
    index = _document(index_path)
    for item in index["artifacts"]:
        if item["kind"] == "acceptance_observation":
            item.update(_reference(observation_path))
    _write(index_path, index)
    result = _document(result_path)
    result["original_execution"]["observation_sha256"] = _digest(observation_path)
    result["original_execution"]["evidence_index_sha256"] = _digest(index_path)
    result["evidence"] = [
        {key: value for key, value in item.items() if key not in {"storage_state", "local_path"}}
        for item in index["artifacts"]
    ]
    _write(result_path, result)
    aggregate_path = tmp_path / "aggregate.json"
    aggregate = _document(aggregate_path)
    for item in aggregate["per_domain_results"]:
        if item["domain_id"] == domain:
            item["result_sha256"] = _digest(result_path)
            item["status"] = result["status"]
    aggregate["per_domain_aggregate"] = worst_status(
        item["status"] for item in aggregate["per_domain_results"]
    )
    _write(aggregate_path, aggregate)


def test_native_qualification_preserves_missing_required_observation(tmp_path: Path) -> None:
    specs = _archive(tmp_path)
    path = tmp_path / "observation-primary.json"
    source = _document(path)
    del source["observations"]["error"]
    _write(path, source)
    result_path = tmp_path / "result-primary.json"
    result = _document(result_path)
    result["observations"]["error"] = {
        "state": "unobserved",
        "reason": "producer supplied no observation",
    }
    result["unevaluated"].extend(["$.observations.error", "$.observations"])
    _write(result_path, result)
    _refresh_domain(tmp_path)
    assert validate_qualification_artifacts(specs)["run_id"] == RUN_ID


def test_native_qualification_requires_actual_model_binding(tmp_path: Path) -> None:
    specs = _archive(tmp_path, native_model=True)
    assert validate_qualification_artifacts(specs)["run_id"] == RUN_ID
    path = tmp_path / "observation-primary.json"
    source = _document(path)
    source["native_model"] = _reference(tmp_path / "native-state.json")
    _write(path, source)
    _refresh_domain(tmp_path)
    with pytest.raises(QualificationError, match="observation primary native model"):
        validate_qualification_artifacts(specs)


def test_native_qualification_keeps_assessment_artifacts_out_of_original_index(
    tmp_path: Path,
) -> None:
    specs = _archive(tmp_path)
    path = tmp_path / "index-primary.json"
    index = _document(path)
    index["artifacts"].append(_indexed(tmp_path / "method.json", "later-method", "assessment"))
    _write(path, index)
    _refresh_domain(tmp_path)
    with pytest.raises(QualificationError, match="must be separate from original evidence"):
        validate_qualification_artifacts(specs)


def test_native_qualification_rejects_ambiguous_raw_evidence_aliases(tmp_path: Path) -> None:
    specs = _archive(tmp_path)
    specs.append(f"other_evidence:evidence/alias.json={tmp_path / 'native-state.json'}")
    with pytest.raises(QualificationError, match="exactly one retained raw artifact"):
        validate_qualification_artifacts(specs)


def test_native_qualification_rejects_noncanonical_observation_alias(tmp_path: Path) -> None:
    specs = [
        item.replace("observations/primary.json=", "noncanonical.json=")
        for item in _archive(tmp_path)
    ]
    with pytest.raises(QualificationError, match="non-canonical acceptance_observation"):
        validate_qualification_artifacts(specs)


def test_native_qualification_rejects_environment_mix_after_all_links_match(tmp_path: Path) -> None:
    specs = _archive(tmp_path, ("first", "second"))
    environment = _write(tmp_path / "second-environment.json", {"python": "3.13"})
    specs.append(f"other_evidence:evaluation/second-environment.json={environment}")
    path = tmp_path / "result-second.json"
    result = _document(path)
    result["evaluation"]["environment"] = _reference(environment)
    _write(path, result)
    _refresh_domain(tmp_path, "second")
    with pytest.raises(QualificationError, match="assessment environment"):
        validate_qualification_artifacts(specs)


@pytest.mark.parametrize("environment", ["hil", "real_robot"])
def test_native_physical_qualification_is_explicitly_unsupported(
    tmp_path: Path, environment: str
) -> None:
    specs = _archive(tmp_path)
    scenario_path = tmp_path / "scenario.json"
    scenario = _document(scenario_path)
    scenario["execution"] = {
        "target_environment": environment,
        "data_source": "native-device",
        "security_profile": "test-signed",
        "hardware_scope": ["controller"],
        "physical_effect": "test-operation",
    }
    scenario["authorization"] = {
        "mode": "signed_execution_permit",
        "permit_schema": "execution-permit.v1",
        "verification_schema": "execution-verification.v1",
        "trust_policy_sha256": "a" * 64,
        "two_party_approval": True,
    }
    _write(scenario_path, scenario)
    run_path = tmp_path / "run.json"
    run = _document(run_path)
    run["scenario_sha256"] = _digest(scenario_path)
    _write(run_path, run)
    runtime_path = tmp_path / "runtime-primary.json"
    runtime = _document(runtime_path)
    runtime["execution"] = scenario["execution"]
    runtime["scenario_sha256"] = _digest(scenario_path)
    runtime["authorization"] = {
        "mode": "verified_execution_permit",
        "permit_sha256": "b" * 64,
        "execution_verification_sha256": "c" * 64,
        "trust_policy_sha256": "a" * 64,
    }
    runtime["execution_subject"] = {
        "kind": "native_process",
        "locator": "urn:example:test-process",
        "digest": "sha256:" + "d" * 64,
    }
    runtime["physical_targets"] = [
        {
            "target_id": "test-controller",
            "scope": "controller",
            "identity_kind": "udev_serial",
            "identity_sha256": "e" * 64,
            "preflight_evidence_sha256": "f" * 64,
        }
    ]
    _write(runtime_path, runtime)
    observation_path = tmp_path / "observation-primary.json"
    observation = _document(observation_path)
    observation["scenario_sha256"] = _digest(scenario_path)
    observation["runtime_manifest_sha256"] = _digest(runtime_path)
    _write(observation_path, observation)
    result_path = tmp_path / "result-primary.json"
    result = _document(result_path)
    result["execution"] = scenario["execution"]
    result["scenario_sha256"] = _digest(scenario_path)
    result["runtime_manifest_sha256"] = _digest(runtime_path)
    result["original_execution"]["acceptance_run_sha256"] = _digest(run_path)
    _write(result_path, result)
    aggregate_path = tmp_path / "aggregate.json"
    aggregate = _document(aggregate_path)
    aggregate["acceptance_run_sha256"] = _digest(run_path)
    _write(aggregate_path, aggregate)
    _refresh_domain(tmp_path)
    with pytest.raises(
        QualificationError, match="hil and real_robot qualification are not supported"
    ):
        validate_qualification_artifacts(specs)


@pytest.mark.parametrize("change", ["fabricated-core", "fabricated-product", "missing-policy"])
def test_native_qualification_refuses_unbound_assertion_claims(tmp_path: Path, change: str) -> None:
    specs = _archive(tmp_path)
    path = tmp_path / "result-primary.json"
    result = _document(path)
    if change == "missing-policy":
        result["assertion_results"].pop()
    else:
        assertion = {
            "assertion_id": "org.fake.passed",
            "source": "core",
            "status": "passed",
            "observed_value": 1,
            "unit": "1",
        }
        if change == "fabricated-product":
            assertion.update(
                {
                    "source": "product",
                    "namespace": "org.fake",
                    "evidence_sha256": [_digest(tmp_path / "native-state.json")],
                }
            )
        result["assertion_results"].append(assertion)
        result["unevaluated"] = []
        result["status"] = "passed"
    _write(path, result)
    _refresh_domain(tmp_path)
    with pytest.raises(QualificationError, match="core assertions|evaluator namespace"):
        validate_qualification_artifacts(specs)


@pytest.mark.parametrize("outside", [False, True])
def test_native_qualification_binds_assessment_window_to_source_interval(
    tmp_path: Path, outside: bool
) -> None:
    specs = _archive(tmp_path)
    _set_measurement_window(tmp_path, start_ns=2000, end_ns=3000)
    path = tmp_path / "result-primary.json"
    result = _document(path)
    result["evaluation"]["window"]["start_ns"] -= 1 if outside else 0
    _write(path, result)
    _refresh_domain(tmp_path)
    if outside:
        with pytest.raises(QualificationError, match="assessment window exceeds its actual source"):
            validate_qualification_artifacts(specs)
    else:
        assert validate_qualification_artifacts(specs)["run_id"] == RUN_ID


def test_native_transport_evaluation_refuses_legacy_format(tmp_path: Path) -> None:
    _archive(tmp_path)
    with pytest.raises(BundleValidationError, match="does not support native v2"):
        evaluate_transport_qualification(
            run_id=RUN_ID,
            scenario_path=tmp_path / "scenario.json",
            causal_chain_paths=[],
            channel_contract_paths=[],
            trace_paths={},
            evidence_index_paths={},
            observation_output_dir=tmp_path / "observed-transport",
            output_path=tmp_path / "refused.json",
        )
    assert not (tmp_path / "refused.json").exists()


def test_native_qualification_accepts_runtime_prepared_before_run_context(tmp_path: Path) -> None:
    specs = _archive(tmp_path)
    runtime_path = tmp_path / "runtime-primary.json"
    runtime = _document(runtime_path)
    runtime["generated_at"] = "2026-10-10T11:59:59Z"
    _write(runtime_path, runtime)
    observation_path = tmp_path / "observation-primary.json"
    observation = _document(observation_path)
    observation["runtime_manifest_sha256"] = _digest(runtime_path)
    _write(observation_path, observation)
    result_path = tmp_path / "result-primary.json"
    result = _document(result_path)
    result["runtime_manifest_sha256"] = _digest(runtime_path)
    _write(result_path, result)
    _refresh_domain(tmp_path)
    assert validate_qualification_artifacts(specs)["run_id"] == RUN_ID


def test_native_qualification_requires_exact_declared_nonapplicability_reason(
    tmp_path: Path,
) -> None:
    specs = _archive(tmp_path)
    path = tmp_path / "observation-primary.json"
    source = _document(path)
    source["observations"]["clock-delivery"]["reason"] = "different inapplicability"
    _write(path, source)
    _refresh_domain(tmp_path)
    with pytest.raises(QualificationError, match="preserve declared non-applicability and reason"):
        validate_qualification_artifacts(specs)


@pytest.mark.parametrize("all_not_applicable", [False, True])
def test_native_link_coverage_independently_refuses_forged_pass(
    tmp_path: Path, all_not_applicable: bool
) -> None:
    from robotics_runtime_contracts._qualification_checks import _context
    from robotics_runtime_contracts._qualification_native import (
        _domain_coverage,
        _method_controls,
        _observations,
    )
    from robotics_runtime_contracts.qualification import inspect_qualification_artifacts

    report = inspect_qualification_artifacts(_archive(tmp_path))
    assert report.valid
    context = _context(report.artifacts, [])
    assert context is not None
    result = context.results["primary"].document
    assert isinstance(result, dict)
    result["status"] = "passed"
    if all_not_applicable:
        source_artifact = _observations(context)["primary"]
        source = source_artifact.document
        assert isinstance(source, dict)
        declaration = {
            "kind": "postcondition",
            "requirement": "not_applicable",
            "reason": "unavailable",
        }
        context.scenario["profile"]["observations"]["error"] = declaration
        value = {"state": "not_applicable", "reason": "unavailable"}
        source["observations"]["error"] = value
        result["observations"]["error"] = value
        result["unevaluated"].append("$.observations")
    with pytest.raises(
        QualificationError, match="passing despite missing source or criterion coverage"
    ):
        _domain_coverage(
            context,
            "primary",
            _observations(context)["primary"],
            _method_controls(context, "primary"),
        )


def _set_measurement_window(
    tmp_path: Path, *, start_ns: int, end_ns: int, clock: dict[str, str] | None = None
) -> None:
    run_path = tmp_path / "run.json"
    run = _document(run_path)
    if clock is not None:
        scenario_path = tmp_path / "scenario.json"
        scenario = _document(scenario_path)
        scenario["profile"]["clock"] = clock
        _write(scenario_path, scenario)
        run["time_authority"] = clock
        run["scenario_sha256"] = _digest(scenario_path)
        _write(run_path, run)
        runtime_path = tmp_path / "runtime-primary.json"
        runtime = _document(runtime_path)
        runtime["scenario_sha256"] = _digest(scenario_path)
        runtime["profile"] = scenario["profile"]
        _write(runtime_path, runtime)
    source_path = tmp_path / "observation-primary.json"
    source = _document(source_path)
    source["scenario_sha256"] = _digest(tmp_path / "scenario.json")
    source["runtime_manifest_sha256"] = _digest(tmp_path / "runtime-primary.json")
    window = {
        "start_ns": start_ns,
        "end_ns": end_ns,
        "clock": run["time_authority"],
        "timestamp_encoding": "native_ns",
    }
    source["measurement_window"] = window
    _write(source_path, source)
    result_path = tmp_path / "result-primary.json"
    result = _document(result_path)
    result["scenario_sha256"] = source["scenario_sha256"]
    result["runtime_manifest_sha256"] = source["runtime_manifest_sha256"]
    result["profile"] = _document(tmp_path / "scenario.json")["profile"]
    result["original_execution"]["acceptance_run_sha256"] = _digest(run_path)
    result["evaluation"]["window"] = window
    _write(result_path, result)
    aggregate_path = tmp_path / "aggregate.json"
    aggregate = _document(aggregate_path)
    aggregate["acceptance_run_sha256"] = _digest(run_path)
    _write(aggregate_path, aggregate)
    _refresh_domain(tmp_path)


@pytest.mark.parametrize(
    "value",
    [
        "2026-10-10T12:00:02.123456789Z",
        "2026-10-10T14:00:02.123456789+02:00",
        "2026-10-10T11:00:02.123456789-01:00",
        "2026-10-10t12:00:02.123456789z",
    ],
)
def test_exact_utc_provenance_parser_preserves_nine_digits(value: str) -> None:
    from robotics_runtime_contracts._timestamps import parse_timestamp_ns

    assert parse_timestamp_ns(value) == 1791633602_123456789


def test_exact_utc_provenance_parser_refuses_excess_precision() -> None:
    from robotics_runtime_contracts._timestamps import parse_timestamp_ns

    with pytest.raises(ContractError, match="invalid timestamp") as caught:
        parse_timestamp_ns("2026-10-10T12:00:02.1234567890Z", json_path="$.started_at")
    assert caught.value.error_id == "input.invalid_timestamp"
    assert caught.value.json_path == "$.started_at"


def test_native_qualification_keeps_zero_based_measurement_clock_separate_from_utc(
    tmp_path: Path,
) -> None:
    specs = _archive(tmp_path)
    _set_measurement_window(
        tmp_path,
        start_ns=0,
        end_ns=1_000_000_000,
        clock={"kind": "external", "source_id": "native-zero"},
    )
    assert _document(tmp_path / "observation-primary.json")["started_at"] == T2
    assert validate_qualification_artifacts(specs)["run_id"] == RUN_ID


@pytest.mark.parametrize(
    "change", ["source-absent", "foreign-clock", "foreign-configuration", "foreign-encoding"]
)
def test_native_qualification_requires_captured_window_and_matching_clock(
    tmp_path: Path, change: str
) -> None:
    specs = _archive(tmp_path)
    _set_measurement_window(tmp_path, start_ns=0, end_ns=1_000_000_000)
    if change == "source-absent":
        path = tmp_path / "observation-primary.json"
        source = _document(path)
        del source["measurement_window"]
        _write(path, source)
    else:
        path = tmp_path / "result-primary.json"
        result = _document(path)
        clock = result["evaluation"]["window"]["clock"]
        if change == "foreign-clock":
            clock["source_id"] = "foreign-clock"
        elif change == "foreign-configuration":
            clock["configuration_sha256"] = "a" * 64
        else:
            result["evaluation"]["window"]["timestamp_encoding"] = "unix_ns"
        _write(path, result)
    _refresh_domain(tmp_path)
    with pytest.raises(
        QualificationError, match="measurement window|assessment clock|timestamp encoding"
    ):
        validate_qualification_artifacts(specs)


def test_native_qualification_detects_one_nanosecond_provenance_boundary_violation(
    tmp_path: Path,
) -> None:
    specs = _archive(tmp_path)
    runtime_path = tmp_path / "runtime-primary.json"
    runtime = _document(runtime_path)
    runtime["generated_at"] = "2026-10-10T12:00:02.000000901Z"
    _write(runtime_path, runtime)
    source_path = tmp_path / "observation-primary.json"
    source = _document(source_path)
    source["runtime_manifest_sha256"] = _digest(runtime_path)
    source["started_at"] = "2026-10-10T12:00:02.000000900Z"
    _write(source_path, source)
    result_path = tmp_path / "result-primary.json"
    result = _document(result_path)
    result["runtime_manifest_sha256"] = _digest(runtime_path)
    result["original_execution"]["started_at"] = source["started_at"]
    _write(result_path, result)
    _refresh_domain(tmp_path)
    with pytest.raises(QualificationError, match="runtime manifest primary before execution"):
        validate_qualification_artifacts(specs)
