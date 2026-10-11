from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
from collections.abc import Iterator
from dataclasses import replace
from importlib.metadata import Distribution, EntryPoint
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from robotics_acceptance_harness import evaluator_trust as trust
from robotics_acceptance_harness import operator_trust
from robotics_acceptance_harness.diagnostics import doctor_report
from robotics_acceptance_harness.documents import load_bundle
from robotics_acceptance_harness.evaluation import EvaluationError, evaluate_acceptance
from robotics_acceptance_harness.evaluator_trust import (
    AuthenticatedInstallation,
    EvaluatorTrustError,
    GitHubVerifierProfile,
    verify_installed_wheel,
)
from robotics_acceptance_harness.receipts import load_verified_receipts
from tests.support import write_verified_receipt
from tests.test_evaluation import FIXTURES, context
from tests.test_evaluator_trust import DIST_INFO, admit_unit_wheel, fixture_wheel

SOURCE = b"""from robotics_acceptance_harness import AssertionEvaluation

def evaluate(context):
    return (AssertionEvaluation(
        "org.example.detected", "passed", 1, "1",
        source="product", namespace="org.example",
        evidence_sha256=(next(iter(context.evidence_sha256)),),
    ),)
"""


@pytest.fixture
def installation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Any, ...]]:
    wheel, installed = fixture_wheel(tmp_path, {"example_evaluator/__init__.py": SOURCE})
    executable, roots = tmp_path / "gh", tmp_path / "roots"
    executable.write_bytes(b"unit probe only")
    roots.write_bytes(b"unit roots only")
    profile = GitHubVerifierProfile(
        executable,
        hashlib.sha256(executable.read_bytes()).hexdigest(),
        "2.102.0",
        roots,
        hashlib.sha256(roots.read_bytes()).hexdigest(),
    )
    authenticated = admit_unit_wheel(monkeypatch, wheel, profile)
    bound = verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))
    chain = write_verified_receipt(
        tmp_path,
        {
            "uri": f"file://{wheel}",
            "sha256": authenticated.sha256,
            "size_bytes": wheel.stat().st_size,
            "media_type": "application/vnd.python.wheel",
            "immutable_revision": f"sha256:{authenticated.sha256}",
        },
        stem="evaluator",
    )
    requirement = {
        "namespace": "org.example",
        "entry_point": "example_evaluator:evaluate",
        "distribution": "example-evaluator",
        "version": "1.0",
        "artifact_sha256": authenticated.sha256,
        "receipt_sha256": chain["receipt_sha256"],
    }
    scenario = yaml.safe_load((FIXTURES / "scenario.yaml").read_text())
    runtime = yaml.safe_load((FIXTURES / "runtime.yaml").read_text())
    scenario["evaluator_requirements"] = [requirement]
    runtime["evaluator_bindings"] = [requirement]
    scenario_path, runtime_path = tmp_path / "scenario.yaml", tmp_path / "runtime.yaml"
    scenario_path.write_text(yaml.safe_dump(scenario))
    runtime_path.write_text(yaml.safe_dump(runtime))
    receipts = load_verified_receipts(
        receipt_paths=[chain["receipt"]],
        verification_paths=[chain["verification"]],
        dependency_paths=chain["dependencies"],
    )
    monkeypatch.syspath_prepend(str(installed))
    yield (
        context(load_bundle(scenario_path, runtime_path=runtime_path)),
        receipts,
        bound,
        installed,
        requirement,
        profile,
        wheel,
    )
    sys.modules.pop("example_evaluator", None)


def test_loader_executes_captured_original_source_and_ignores_derived_cache(
    installation: tuple[Any, ...],
) -> None:
    evaluation_context, receipts, bound, installed, *_ = installation
    source = installed / "example_evaluator/__init__.py"
    source.write_bytes(b"raise RuntimeError('late source replacement')\n")
    cache = source.parent / "__pycache__"
    cache.mkdir()
    (cache / "__init__.cpython-312.pyc").write_bytes(b"invalid derived bytecode")
    (installed / DIST_INFO / "RECORD").write_text("late untrusted record")
    results = evaluate_acceptance(
        evaluation_context,
        evaluator_receipts=receipts,
        evaluator_authentications={"org.example": bound},
    )
    assert results[-1].assertion_id == "org.example.detected"
    assert results[-1].observed_value == 1


def test_mutated_entry_point_is_not_recovered_from_installed_metadata(
    installation: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    evaluation_context, receipts, bound, installed, *_ = installation
    fake = EntryPoint("org.example", "example_evaluator:other", "robotics_acceptance.evaluators")
    cast(Any, fake)._for(Distribution.at(installed / DIST_INFO))
    monkeypatch.setattr(
        "robotics_acceptance_harness.evaluation.entry_points", lambda **kwargs: (fake,)
    )
    scenario = dict(evaluation_context.bundle.scenario.data)
    scenario["evaluator_requirements"] = [
        dict(scenario["evaluator_requirements"][0], entry_point=fake.value)
    ]
    bundle = replace(
        evaluation_context.bundle,
        scenario=replace(evaluation_context.bundle.scenario, data=scenario),
    )
    with pytest.raises(EvaluationError, match="authenticated wheel bindings"):
        evaluate_acceptance(
            replace(evaluation_context, bundle=bundle),
            evaluator_receipts=receipts,
            evaluator_authentications={"org.example": bound},
        )
    assert "example_evaluator" not in sys.modules


def test_constructor_and_dataclass_copy_cannot_issue_installation_admission(
    installation: tuple[Any, ...],
) -> None:
    evaluation_context, receipts, bound, *_ = installation
    copies = (
        AuthenticatedInstallation(
            bound.wheel_sha256,
            bound.distribution,
            bound.version,
            bound.paths,
            bound.files,
            bound.sources,
            bound.entry_points,
        ),
        replace(bound),
    )
    for copied in copies:
        with pytest.raises(EvaluatorTrustError, match="issued"):
            evaluate_acceptance(
                evaluation_context,
                evaluator_receipts=receipts,
                evaluator_authentications={"org.example": copied},
            )
    assert "example_evaluator" not in sys.modules


def test_doctor_reports_authenticated_inventory_without_importing_target(
    installation: tuple[Any, ...],
) -> None:
    evaluation_context, receipts, bound, *_ = installation
    report = doctor_report(
        evaluator_requirements=evaluation_context.scenario["evaluator_requirements"],
        evaluator_receipts=receipts,
        evaluator_authentications={"org.example": bound},
    )
    assert report["status"] == "passed"
    assert report["evaluators"][0]["status"] == "authenticated"
    assert "example_evaluator" not in sys.modules


def profile_json(
    profile: GitHubVerifierProfile, wheel: Path, requirement: dict[str, Any]
) -> dict[str, Any]:
    return {
        "profile_version": 1,
        "verifier": {
            "kind": "github",
            "executable": str(profile.executable),
            "executable_sha256": profile.executable_sha256,
            "version": profile.version,
            "trusted_root": str(profile.trusted_root),
            "trusted_root_sha256": profile.trusted_root_sha256,
        },
        "evaluators": [
            {
                "namespace": "org.example",
                "wheel": str(wheel),
                "bundle": str(wheel.parent / "bundle.jsonl"),
                "publisher": {
                    "repository": "example/evaluators",
                    "certificate_identity": "https://github.com/example/evaluators/.github/workflows/release.yml@refs/tags/v1",
                    "wheel_sha256": requirement["artifact_sha256"],
                },
            }
        ],
    }


def test_operator_profile_binds_declared_original_wheel(
    installation: tuple[Any, ...], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, _, installed, requirement, profile, wheel = installation
    path = tmp_path / "operator.json"
    path.write_text(json.dumps(profile_json(profile, wheel, requirement)))
    path.chmod(0o600)
    monkeypatch.setattr(
        operator_trust, "distribution", lambda name: Distribution.at(installed / DIST_INFO)
    )
    admitted = operator_trust.load_evaluator_authentications(path, [requirement])
    trust.require_authenticated_installation(admitted["org.example"])
    assert admitted["org.example"].sources[installed / "example_evaluator/__init__.py"] == SOURCE


@pytest.mark.parametrize(
    "fault", ["unknown-field", "evidence-root", "subject", "unreferenced", "writable"]
)
def test_operator_profile_rejects_policy_or_location_faults(
    installation: tuple[Any, ...], tmp_path: Path, fault: str
) -> None:
    *_, requirement, profile, wheel = installation
    data = profile_json(profile, wheel, requirement)
    path = tmp_path / "operator.json"
    if fault == "unknown-field":
        data["trusted"] = True
    elif fault == "subject":
        data["evaluators"][0]["publisher"]["wheel_sha256"] = "f" * 64
    elif fault == "unreferenced":
        data["evaluators"][0]["namespace"] = "org.unreferenced"
    path.write_text(json.dumps(data))
    path.chmod(0o600)
    if fault == "writable":
        path.chmod(0o666)
    with pytest.raises(EvaluatorTrustError):
        operator_trust.load_evaluator_authentications(
            path,
            [requirement],
            evidence_root=tmp_path if fault == "evidence-root" else None,
        )


@pytest.mark.parametrize(
    "fault", ["source", "entry-point", "missing-hash", "installer-root", "shared-namespace"]
)
def test_authentication_binding_rejects_original_record_and_namespace_faults(
    installation: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    _, _, _, installed, _, profile, wheel = installation
    if fault == "source":
        (installed / "example_evaluator/__init__.py").write_bytes(b"tampered source")
    elif fault == "entry-point":
        (installed / DIST_INFO / "entry_points.txt").write_bytes(b"tampered entry point")
    elif fault == "missing-hash":
        record = installed / DIST_INFO / "RECORD"
        rows = list(csv.reader(io.StringIO(record.read_text())))
        for row in rows:
            if row[0] == "example_evaluator/__init__.py":
                row[1:] = ["", ""]
        stream = io.StringIO(newline="")
        csv.writer(stream).writerows(rows)
        record.write_text(stream.getvalue())
    elif fault == "installer-root":
        (installed / "INSTALLER").write_bytes(b"unowned executable-looking metadata")
        record = installed / DIST_INFO / "RECORD"
        record.write_text(record.read_text() + "INSTALLER,,\n")
    else:
        (installed / "example_evaluator/peer.py").write_bytes(b"other distribution source")
    authenticated = admit_unit_wheel(monkeypatch, wheel, profile)
    with pytest.raises(EvaluatorTrustError):
        verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))


def test_operator_profile_dot_segments_cannot_enter_evidence_root(
    installation: tuple[Any, ...], tmp_path: Path
) -> None:
    *_, requirement, profile, wheel = installation
    evidence = tmp_path / "evidence"
    outside = tmp_path / "outside"
    evidence.mkdir()
    outside.mkdir()
    path = evidence / "operator.json"
    path.write_text(json.dumps(profile_json(profile, wheel, requirement)))
    path.chmod(0o600)
    aliased = outside / ".." / "evidence" / "operator.json"
    with pytest.raises(EvaluatorTrustError, match="outside the evidence root"):
        operator_trust.load_evaluator_authentications(
            aliased, [requirement], evidence_root=evidence
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("wheel_sha256", 123),
        ("repository", None),
        ("certificate_identity", []),
        ("source_ref", 123),
        ("source_digest", {}),
        ("deny_self_hosted_runners", "true"),
    ],
)
def test_malformed_publisher_policy_has_a_modeled_error(field: str, value: object) -> None:
    publisher = {
        "repository": "example/evaluators",
        "certificate_identity": "https://github.com/example/evaluators/.github/workflows/ci.yml@refs/heads/main",
        "wheel_sha256": "a" * 64,
        field: value,
    }
    with pytest.raises(EvaluatorTrustError):
        operator_trust._publisher(publisher)


@pytest.mark.parametrize("kind", [None, "legacy", "cosign", "github-fallback"])
def test_operator_verifier_kind_never_defaults_or_downgrades(
    installation: tuple[Any, ...],
    kind: str | None,
) -> None:
    *_, requirement, profile, wheel = installation
    value = profile_json(profile, wheel, requirement)["verifier"]
    if kind is None:
        value.pop("kind")
    else:
        value["kind"] = kind
    with pytest.raises(EvaluatorTrustError, match="explicitly select"):
        operator_trust._verifier(value, wheel.parent)
