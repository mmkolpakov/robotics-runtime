from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from robotics_runtime_contracts.serialization import MAX_DOCUMENT_BYTES

from robotics_acceptance_harness._oci_request import build_oci_request
from robotics_acceptance_harness.archive import load_assessment_controls
from robotics_acceptance_harness.documents import load_bundle, load_document
from robotics_acceptance_harness.evaluation import EvaluationContext, EvaluationError
from robotics_acceptance_harness.evaluator_trust import EvaluatorTrustError
from robotics_acceptance_harness.evidence import load_evidence_index
from tests.test_archive_controls import controls
from tests.test_neutral_qualification import (
    RUN_ID,
    _archive,
    _document,
    _indexed,
    _reference,
    _write,
)
from tests.test_oci_assessment_v3 import OCI


def setup_request(
    tmp_path: Path, *, large: bool = False
) -> tuple[EvaluationContext, dict[str, Any], dict[str, Any]]:
    _archive(tmp_path)
    if large:
        extra = tmp_path / "large-evidence.bin"
        extra.write_bytes(b"x" * (MAX_DOCUMENT_BYTES + 1))
        index_path = tmp_path / "index-primary.json"
        index = _document(index_path)
        index["artifacts"].append(_indexed(extra, "large-evidence", "other_evidence"))
        _write(index_path, index)
    bundle = load_bundle(tmp_path / "scenario.json", runtime_path=tmp_path / "runtime-primary.json")
    evidence = load_evidence_index(tmp_path / "index-primary.json", expected_run_id=RUN_ID)
    calibration = tmp_path / "calibration.json"
    calibration.write_bytes((tmp_path / "native-state.json").read_bytes())
    raw_controls = controls()
    raw_controls.update(
        schema_version="assessment-controls.v1",
        evaluator_requirements=[OCI],
        calibration={"state": "selected", "artifacts": [_reference(calibration)]},
    )
    controls_path = _write(tmp_path / "selected-controls.json", raw_controls)
    selected = load_assessment_controls(controls_path)
    original = (
        None
        if large
        else load_document(tmp_path / "result-primary.json", expected_role="acceptance_result")
    )
    context = EvaluationContext(
        RUN_ID,
        "primary",
        bundle,
        evidence,
        (),
        100,
        200,
        max_raw_evidence_bytes=2 * MAX_DOCUMENT_BYTES if large else 65536,
        assessment_controls=selected,
        original_result=original,
    )
    documents = {
        "acceptance_scenario": bundle.scenario,
        "runtime_manifest": bundle.runtime,
        "acceptance_run": load_document(tmp_path / "run.json", expected_role="acceptance_run"),
        "acceptance_observation": load_document(
            tmp_path / "observation-primary.json", expected_role="acceptance_observation"
        ),
        "evidence_index": evidence.index,
    }
    if original is not None:
        documents["acceptance_result"] = original
    method = {
        "implementation": "owner.whole-method",
        "version": "42",
        "configuration": _reference(controls_path),
    }
    return context, documents, method


def build(
    context: EvaluationContext,
    documents: dict[str, Any],
    method: dict[str, Any],
    *,
    budget: int = 1024 * 1024,
) -> tuple[bytes, Any]:
    assert context.assessment_controls is not None
    attempt = documents["acceptance_run"].path.parent / f"attempt-{uuid4()}"
    attempt.mkdir(mode=0o700)
    packet = build_oci_request(
        context,
        documents=documents,
        method=method,
        requirement=context.assessment_controls.data["evaluator_requirements"][0],
        options={"window": None, "attempt_dir": attempt, "max_input_bytes": budget},
    )
    inputs = attempt / "inputs"
    assert (inputs / "request.json").read_bytes() == packet
    assert (inputs / "request.json").stat().st_mode & 0o777 == 0o400
    assert all(path.stat().st_mode & 0o777 == 0o400 for path in (inputs / "objects").iterdir())
    return packet, {
        f"objects/{path.name}": path.read_bytes() for path in (inputs / "objects").iterdir()
    }


def test_request_preserves_validated_bytes_and_deduplicates_locations(tmp_path: Path) -> None:
    context, documents, method = setup_request(tmp_path)
    assert context.assessment_controls is not None
    original_controls = context.assessment_controls.raw
    (tmp_path / "selected-controls.json").write_bytes(b"changed after capture")
    (tmp_path / "calibration.json").write_bytes(b"changed after capture")
    packet, captured = build(context, documents, method)
    request = json.loads(packet)
    assert request["method"]["implementation"] == "owner.whole-method"
    assert request["method"]["version"] == "42"
    assert (
        request["documents"]["acceptance_run"]["uri"] == documents["acceptance_run"].path.as_uri()
    )
    assert request["controls"]["uri"] == context.assessment_controls.path.as_uri()
    assert captured["objects/" + context.assessment_controls.sha256] == original_controls
    for location in request["locations"]:
        assert sha256(captured[location["path"]]).hexdigest() == location["sha256"]
    assert len(request["locations"]) == len(captured)
    calibration_digest = sha256((tmp_path / "native-state.json").read_bytes()).hexdigest()
    assert sum(item["sha256"] == calibration_digest for item in request["locations"]) == 1
    assert all(path.startswith("objects/") for path in captured)


def test_verified_document_recapture_rejects_substitution(tmp_path: Path) -> None:
    context, documents, method = setup_request(tmp_path)
    documents["acceptance_run"].path.write_bytes(b"{}")
    with pytest.raises(EvaluationError, match="validated digest"):
        build(context, documents, method)


def test_foreign_requirement_and_document_refuse(tmp_path: Path) -> None:
    context, documents, method = setup_request(tmp_path)
    foreign = {**OCI, "namespace": "org.example.foreign"}
    with pytest.raises(EvaluationError, match="declared"):
        build_oci_request(
            context,
            documents=documents,
            method=method,
            requirement=foreign,
            options={"window": None, "attempt_dir": tmp_path, "max_input_bytes": 1024 * 1024},
        )
    documents["acceptance_run"] = documents["runtime_manifest"]
    with pytest.raises(EvaluationError, match="unexpected schema"):
        build(context, documents, method)


def test_remote_only_evidence_is_refused(tmp_path: Path) -> None:
    context, documents, method = setup_request(tmp_path)
    context = replace(context, evidence=replace(context.evidence, local_files={}))
    with pytest.raises(EvaluationError, match="no captured local input"):
        build(context, documents, method)


def test_total_budget_includes_packet_and_unique_inputs(tmp_path: Path) -> None:
    context, documents, method = setup_request(tmp_path)
    packet, captured = build(context, documents, method)
    exact = len(packet) + sum(map(len, captured.values()))
    assert build(context, documents, method, budget=exact)[0] == packet
    with pytest.raises((EvaluationError, EvaluatorTrustError)):
        build(context, documents, method, budget=exact - 1)


def test_method_reference_cannot_claim_other_controls(tmp_path: Path) -> None:
    context, documents, method = setup_request(tmp_path)
    method["configuration"] = {**method["configuration"], "sha256": "0" * 64}
    with pytest.raises(EvaluationError, match="method configuration"):
        build(context, documents, method)


def test_large_indexed_evidence_streams_into_owned_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from robotics_acceptance_harness import _oci_request as builder

    context, documents, method = setup_request(tmp_path, large=True)
    observed: list[int] = []
    from robotics_acceptance_harness.evidence import _verified_payload as original

    def track(*args: Any, **kwargs: Any) -> bytes:
        assert kwargs.get("sink") is not None
        assert not kwargs.get("capture", False)
        result = original(*args, **kwargs)
        assert result == b""
        observed.append(int(args[1]["size_bytes"]))
        return result

    monkeypatch.setattr(builder, "_verified_payload", track)
    _, captured = build(context, documents, method, budget=2 * MAX_DOCUMENT_BYTES)
    raw = (tmp_path / "large-evidence.bin").read_bytes()
    assert len(raw) in observed
    assert captured["objects/" + sha256(raw).hexdigest()] == raw


def test_evidence_replacement_removes_partial_snapshot(tmp_path: Path) -> None:
    from robotics_acceptance_harness._evidence_files import EvidenceReadError

    context, documents, method = setup_request(tmp_path, large=True)
    source = tmp_path / "large-evidence.bin"
    digest = sha256(source.read_bytes()).hexdigest()
    source.write_bytes(b"y" * source.stat().st_size)
    attempt = tmp_path / "failed-attempt"
    attempt.mkdir(mode=0o700)
    assert context.assessment_controls is not None
    with pytest.raises(EvidenceReadError, match="expected"):
        build_oci_request(
            context,
            documents=documents,
            method=method,
            requirement=context.assessment_controls.data["evaluator_requirements"][0],
            options={
                "window": None,
                "attempt_dir": attempt,
                "max_input_bytes": 2 * MAX_DOCUMENT_BYTES,
            },
        )
    assert not (attempt / "inputs" / "objects" / digest).exists()
    assert not (attempt / "inputs" / "request.json").exists()


def test_growing_evidence_refuses_and_removes_partial_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import contextmanager

    from robotics_acceptance_harness import evidence as evidence_module
    from robotics_acceptance_harness._evidence_files import EvidenceReadError

    context, documents, method = setup_request(tmp_path, large=True)
    source = tmp_path / "large-evidence.bin"
    digest = sha256(source.read_bytes()).hexdigest()
    from robotics_acceptance_harness._evidence_files import open_evidence as actual_open

    @contextmanager
    def growing(path: Path, root: Path) -> Any:
        with actual_open(path, root) as stream:
            if path != source:
                yield stream
                return

            class Reader:
                changed = False

                def read(self, size: int) -> bytes:
                    chunk = stream.read(size)
                    if not self.changed:
                        self.changed = True
                        with source.open("ab") as writer:
                            writer.write(b"g")
                    return chunk

                def fileno(self) -> int:
                    return stream.fileno()

            yield Reader()

    monkeypatch.setattr(evidence_module, "open_evidence", growing)
    attempt = tmp_path / "growing-attempt"
    attempt.mkdir(mode=0o700)
    assert context.assessment_controls is not None
    with pytest.raises(EvidenceReadError, match="grew|changed"):
        build_oci_request(
            context,
            documents=documents,
            method=method,
            requirement=context.assessment_controls.data["evaluator_requirements"][0],
            options={
                "window": None,
                "attempt_dir": attempt,
                "max_input_bytes": 2 * MAX_DOCUMENT_BYTES,
            },
        )
    assert not (attempt / "inputs" / "objects" / digest).exists()
    assert not (attempt / "inputs" / "request.json").exists()


def test_existing_captured_byte_api_still_returns_bytes(tmp_path: Path) -> None:
    context, _, _ = setup_request(tmp_path)
    source = tmp_path / "native-state.json"
    assert context.evidence.read_local(source, max_raw_evidence_bytes=65536) == source.read_bytes()


def test_raw_evidence_budget_applies_to_already_staged_document(tmp_path: Path) -> None:
    context, documents, method = setup_request(tmp_path)
    context = replace(context, max_raw_evidence_bytes=1)
    with pytest.raises(EvaluationError, match="raw byte budget"):
        build(context, documents, method)


def test_evidence_symlink_is_refused_without_partial_output(tmp_path: Path) -> None:
    from robotics_acceptance_harness._evidence_files import EvidenceReadError

    context, documents, method = setup_request(tmp_path, large=True)
    source = tmp_path / "large-evidence.bin"
    digest = sha256(source.read_bytes()).hexdigest()
    original = tmp_path / "moved-evidence.bin"
    source.rename(original)
    source.symlink_to(original)
    attempt = tmp_path / "symlink-attempt"
    attempt.mkdir(mode=0o700)
    assert context.assessment_controls is not None
    with pytest.raises((EvidenceReadError, OSError)):
        build_oci_request(
            context,
            documents=documents,
            method=method,
            requirement=context.assessment_controls.data["evaluator_requirements"][0],
            options={
                "window": None,
                "attempt_dir": attempt,
                "max_input_bytes": 2 * MAX_DOCUMENT_BYTES,
            },
        )
    assert not (attempt / "inputs" / "objects" / digest).exists()
    assert not (attempt / "inputs" / "request.json").exists()


def test_evidence_sink_refuses_short_writes(tmp_path: Path) -> None:
    from io import BytesIO

    from robotics_acceptance_harness._evidence_files import EvidenceReadError
    from robotics_acceptance_harness.evidence import _verified_payload

    context, _, _ = setup_request(tmp_path)
    source = tmp_path / "native-state.json"
    reference = context.evidence.local_files[source]

    class ShortSink(BytesIO):
        def write(self, data: Any) -> int:
            super().write(data[:-1])
            return len(data) - 1

    with pytest.raises(EvidenceReadError, match="complete chunk"):
        _verified_payload(source, reference, context.evidence.index.path.parent, sink=ShortSink())


def test_unindexed_observation_and_empty_evidence_fail_closed(tmp_path: Path) -> None:
    context, documents, method = setup_request(tmp_path)
    evidence = replace(context.evidence, links=(), local_files={})
    with pytest.raises(EvaluationError, match="observation differs"):
        build(replace(context, evidence=evidence), documents, method)


@pytest.mark.parametrize("budget", [0, -1, True])
def test_invalid_disk_budget_refused_before_staging(tmp_path: Path, budget: int) -> None:
    context, documents, method = setup_request(tmp_path)
    with pytest.raises(EvaluationError, match="positive integer"):
        build(context, documents, method, budget=budget)
