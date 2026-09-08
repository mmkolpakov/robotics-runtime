from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

import pytest
from junitparser import JUnitXml

from robotics_acceptance_harness.documents import DocumentBundle, load_bundle
from robotics_acceptance_harness.evidence import VerifiedEvidence, load_evidence_index
from robotics_acceptance_harness.forbidden_graph import (
    ForbiddenGraphObservation,
    ForbiddenGraphViolation,
)
from robotics_acceptance_harness.hardware_timing import HardwareTimingObservation
from robotics_acceptance_harness.metrics import AssertionEvaluation
from robotics_acceptance_harness.readiness import (
    EndpointObservation,
    GraphSnapshot,
    ReadinessResult,
    TopicObservation,
)
from robotics_acceptance_harness.result import (
    build_acceptance_result,
    write_contract_json,
    write_junit_xml,
)
from robotics_acceptance_harness.time_authority import TimeAuthorityObservation
from robotics_acceptance_harness.timing import TimingObservation
from tests.support import local_evidence_artifact, write_evidence_index

FIXTURES = Path(__file__).parent / "fixtures" / "simulation"
RUN_ID = "run-00000000-0000-4000-8000-000000000001"
OTHER_RUN_ID = "run-00000000-0000-4000-8000-000000000002"


class ResultInputs(TypedDict):
    result_id: str
    run_id: str
    domain_id: str
    bundle: DocumentBundle
    readiness: ReadinessResult
    timing: TimingObservation
    time_authority: TimeAuthorityObservation
    time_authority_evidence_sha256: str | None
    assertions: Sequence[AssertionEvaluation]
    unevaluated: Sequence[str]
    started_at: datetime
    finished_at: datetime
    monotonic_duration_sec: float
    shutdown: Mapping[str, bool]
    evidence_index: VerifiedEvidence
    forbidden_graph: ForbiddenGraphObservation
    hardware_timing: NotRequired[HardwareTimingObservation]
    hardware_timing_evidence_sha256: NotRequired[str]


def result_inputs(tmp_path: Path, *, evidence_run_id: str = RUN_ID) -> ResultInputs:
    evidence_file = tmp_path / f"{evidence_run_id}.json"
    evidence_file.write_text("{}\n", encoding="utf-8")
    evidence = load_evidence_index(
        write_evidence_index(
            tmp_path / f"{evidence_run_id}-evidence.yaml",
            run_id=evidence_run_id,
            artifacts=[local_evidence_artifact(evidence_file)],
        )
    )
    snapshot = GraphSnapshot(
        observed_at_ns=2_000_000_000,
        topics={
            "/clock": TopicObservation(
                types=("rosgraph_msgs/msg/Clock",),
                publishers=1,
                subscribers=1,
                first_message_at_ns=1_000_000_000,
            )
        },
    )
    started_at = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
    return {
        "result_id": "result-00000000-0000-4000-8000-000000000001",
        "run_id": RUN_ID,
        "domain_id": "camera-domain",
        "bundle": load_bundle(
            FIXTURES / "scenario.yaml",
            runtime_path=FIXTURES / "runtime.yaml",
        ),
        "readiness": ReadinessResult(snapshot, 1_000_000_000, 1.0),
        "timing": TimingObservation(True, 0, 0, 0.99, 0, 0, 10),
        "time_authority": TimeAuthorityObservation(
            source_id="simulation-clock",
            sample_count=30,
            window_start_ns=1_000_000_000,
            window_end_ns=2_000_000_000,
            p50_ms=0.1,
            p95_ms=0.2,
            max_ms=0.3,
            within_policy=True,
        ),
        "time_authority_evidence_sha256": evidence.links[0]["sha256"],
        "assertions": (AssertionEvaluation("domain-smoke", "passed", 1, "1"),),
        "unevaluated": (),
        "started_at": started_at,
        "finished_at": started_at + timedelta(seconds=30),
        "monotonic_duration_sec": 30,
        "shutdown": {
            "observer_detached": True,
            "recorders_closed": True,
            "evidence_index_finalized": True,
        },
        "evidence_index": evidence,
        "forbidden_graph": ForbiddenGraphObservation((), (), (), ()),
    }


def test_build_result_validates_no_inference_execution(tmp_path: Path) -> None:
    result = build_acceptance_result(**result_inputs(tmp_path))

    assert result["status"] == "passed"
    assert result["workload"] == {"kind": "none"}


def test_result_omits_endpoints_that_lost_their_type(tmp_path: Path) -> None:
    snapshot = GraphSnapshot(
        observed_at_ns=2_000_000_000,
        topics={
            "/clock": TopicObservation(
                types=(),
                publishers=1,
                subscribers=1,
                first_message_at_ns=1_000_000_000,
            )
        },
        services={"/reset": EndpointObservation(types=(), server_nodes=1)},
        actions={"/move": EndpointObservation(types=(), server_nodes=1, client_nodes=1)},
    )
    inputs = result_inputs(tmp_path)
    inputs["readiness"] = ReadinessResult(snapshot, 1_000_000_000, 1.0)

    result = build_acceptance_result(**inputs)

    assert result["observed_ros_graph"]["topics"] == []
    assert result["observed_ros_graph"]["services"] == []
    assert result["observed_ros_graph"]["actions"] == []


def test_json_and_junit_outputs_share_status(tmp_path: Path) -> None:
    inputs = result_inputs(tmp_path)
    inputs["assertions"] = (
        AssertionEvaluation("latency", "failed", 120.0, "ms", "threshold lte 100"),
    )
    result = build_acceptance_result(**inputs)

    json_path = write_contract_json(result, tmp_path / "acceptance-result.json")
    junit_path = write_junit_xml(result, tmp_path / "junit.xml")

    assert json.loads(json_path.read_text(encoding="utf-8"))["status"] == "failed"
    xml = JUnitXml.fromfile(str(junit_path))
    assert (xml.failures, xml.errors) == (1, 0)


def test_result_rejects_evidence_from_another_run(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="evidence index run_id"):
        build_acceptance_result(**result_inputs(tmp_path, evidence_run_id=OTHER_RUN_ID))


def test_result_marks_declared_gap_incomplete(tmp_path: Path) -> None:
    inputs = result_inputs(tmp_path)
    inputs["time_authority"] = TimeAuthorityObservation(
        source_id="external-clock",
        sample_count=0,
        window_start_ns=0,
        window_end_ns=0,
        p50_ms=0,
        p95_ms=0,
        max_ms=0,
        within_policy=False,
    )
    inputs["time_authority_evidence_sha256"] = None
    inputs["unevaluated"] = ("$.time_authority_observation",)

    result = build_acceptance_result(**inputs)

    assert result["status"] == "incomplete"
    assert "evidence_sha256" not in result["time_authority_observation"]
    junit = JUnitXml.fromfile(str(write_junit_xml(result, tmp_path / "junit.xml")))
    assert (junit.failures, junit.errors, junit.skipped) == (0, 0, 2)


def test_result_and_junit_mark_skipped_assertion_incomplete(tmp_path: Path) -> None:
    inputs = result_inputs(tmp_path)
    inputs["assertions"] = (AssertionEvaluation("optional-check", "skipped", "not-observed", "1"),)

    result = build_acceptance_result(**inputs)

    assert result["status"] == "incomplete"
    assert result["unevaluated"] == ["$.assertions.optional-check"]
    assert result["assertion_results"][0]["observed_value"] == "not-observed"
    junit = JUnitXml.fromfile(str(write_junit_xml(result, tmp_path / "junit.xml")))
    assert (junit.failures, junit.errors, junit.skipped) == (0, 0, 2)


def hardware_result_inputs(tmp_path: Path) -> ResultInputs:
    inputs = result_inputs(tmp_path)
    physical = FIXTURES.parent / "physical"
    started = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)
    inputs["bundle"] = load_bundle(
        physical / "hil-scenario.yaml",
        runtime_path=physical / "hil-runtime.json",
        permit_path=physical / "hil-permit.json",
        verification_path=physical / "hil-verification.json",
        now=started,
    )
    inputs["started_at"] = started
    inputs["finished_at"] = started + timedelta(seconds=30)
    inputs["timing"] = TimingObservation(True, 0, 0, 0, 0, 0, 0)
    inputs["hardware_timing"] = HardwareTimingObservation(
        "mavlink_timesync", "mavlink_timesync_status", started, 30, 0, 0, 0, 0, True, True
    )
    inputs["hardware_timing_evidence_sha256"] = inputs["evidence_index"].links[0]["sha256"]
    return inputs


def forbidden_violation() -> ForbiddenGraphObservation:
    return ForbiddenGraphObservation(
        ("/cmd_vel",), (), (), (ForbiddenGraphViolation("topic", "/cmd_vel"),)
    )


@pytest.mark.parametrize("assertion_status", ["passed", "failed", "error", "skipped", None])
@pytest.mark.parametrize("violation", ["forbidden", "hardware", "time_authority"])
def test_policy_violation_dominates_incomplete_but_not_error(
    tmp_path: Path,
    assertion_status: Literal["passed", "failed", "error", "skipped"] | None,
    violation: str,
) -> None:
    inputs = (
        hardware_result_inputs(tmp_path) if violation == "hardware" else result_inputs(tmp_path)
    )
    inputs["assertions"] = (
        (AssertionEvaluation("domain-smoke", assertion_status, None, "1"),)
        if assertion_status is not None
        else ()
    )
    inputs["unevaluated"] = ("$.observed_ros_graph",)
    if violation == "forbidden":
        inputs["forbidden_graph"] = forbidden_violation()
    elif violation == "hardware":
        inputs["hardware_timing"] = replace(inputs["hardware_timing"], within_policy=False)
    else:
        inputs["time_authority"] = replace(inputs["time_authority"], within_policy=False)

    result = build_acceptance_result(**inputs)
    junit = JUnitXml.fromfile(str(write_junit_xml(result, tmp_path / "junit.xml")))

    assert result["status"] == ("error" if assertion_status == "error" else "failed")
    assert junit.failures == 1 + (assertion_status == "failed")
    assert junit.errors == (assertion_status == "error")
    assert junit.skipped == 1 + (assertion_status == "skipped")


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    ("core_status", "product_status", "expected"),
    [
        ("skipped", "passed", "failed"),
        ("passed", "skipped", "failed"),
        ("skipped", "failed", "failed"),
        ("skipped", "error", "error"),
        ("error", "passed", "error"),
    ],
)
def test_multiple_violations_preserve_product_and_core_error_precedence(
    tmp_path: Path,
    core_status: Literal["passed", "error", "skipped"],
    product_status: Literal["passed", "failed", "error", "skipped"],
    expected: str,
    reverse: bool,
) -> None:
    inputs = hardware_result_inputs(tmp_path)
    inputs["forbidden_graph"] = forbidden_violation()
    inputs["hardware_timing"] = replace(inputs["hardware_timing"], within_policy=False)
    inputs["time_authority"] = replace(inputs["time_authority"], within_policy=False)
    assertions = (
        AssertionEvaluation("time-policy", core_status, None, "1"),
        AssertionEvaluation(
            "org.example.sorting.time-policy",
            product_status,
            None,
            "1",
            source="product",
            namespace="org.example.sorting",
            evidence_sha256=(inputs["evidence_index"].links[0]["sha256"],),
        ),
    )
    inputs["assertions"] = assertions[::-1] if reverse else assertions

    result = build_acceptance_result(**inputs)
    junit = JUnitXml.fromfile(str(write_junit_xml(result, tmp_path / "junit.xml")))

    assert result["status"] == expected
    assert junit.failures == 3 + (product_status == "failed")
    assert junit.errors == (expected == "error")
    assert junit.skipped == 1 + (core_status == "skipped") + (product_status == "skipped")
    assert {item["status"] for item in result["assertion_results"]} <= {
        "passed",
        "failed",
        "error",
        "skipped",
    }


def test_empty_assertions_report_skipped_coverage_without_a_failure(tmp_path: Path) -> None:
    inputs = result_inputs(tmp_path)
    inputs["assertions"] = ()

    result = build_acceptance_result(**inputs)
    junit = JUnitXml.fromfile(str(write_junit_xml(result, tmp_path / "junit.xml")))

    assert result["status"] == "incomplete"
    assert result["unevaluated"] == ["$.assertions"]
    assert (junit.failures, junit.errors, junit.skipped) == (0, 0, 1)


def test_hardware_zero_placeholders_are_explicitly_unevaluated(tmp_path: Path) -> None:
    result = build_acceptance_result(**hardware_result_inputs(tmp_path))
    junit = JUnitXml.fromfile(str(write_junit_xml(result, tmp_path / "junit.xml")))

    assert result["status"] == "incomplete"
    assert result["unevaluated"] == [
        "$.clock_observation.deadline_miss_ratio",
        "$.clock_observation.real_time_factor",
    ]
    assert (junit.failures, junit.errors, junit.skipped) == (0, 0, 1)
