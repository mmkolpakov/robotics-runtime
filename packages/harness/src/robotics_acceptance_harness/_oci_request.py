"""Build a finite evaluator request from already validated assessment inputs."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any, TypedDict

from robotics_runtime_contracts.serialization import MAX_DOCUMENT_BYTES

from robotics_acceptance_harness.archive import AssessmentControls
from robotics_acceptance_harness.documents import LoadedDocument
from robotics_acceptance_harness.evaluation import EvaluationContext, EvaluationError
from robotics_acceptance_harness.evaluator_json import encode_evaluator_request
from robotics_acceptance_harness.evaluator_trust import _sha256, read_once
from robotics_acceptance_harness.evidence import _verified_payload
from robotics_acceptance_harness.otel import _validate_raw_evidence_budget

_DOCUMENT_ROLES = frozenset(
    {
        "acceptance_scenario",
        "runtime_manifest",
        "acceptance_run",
        "acceptance_observation",
        "evidence_index",
    }
)


class _RequestOptions(TypedDict):
    window: Mapping[str, Any] | None
    attempt_dir: Path
    max_input_bytes: int


def _validate_source_documents(
    context: EvaluationContext, documents: Mapping[str, LoadedDocument]
) -> None:
    roles = set(documents)
    if not roles >= _DOCUMENT_ROLES or roles - _DOCUMENT_ROLES - {"acceptance_result"}:
        raise EvaluationError("OCI request requires the five source document roles")
    expected = {
        "acceptance_scenario": context.bundle.scenario.sha256,
        "runtime_manifest": context.bundle.runtime.sha256,
        "evidence_index": context.evidence.index.sha256,
    }
    if context.original_result is not None:
        expected["acceptance_result"] = context.original_result.sha256
        if "acceptance_result" not in roles:
            raise EvaluationError("captured original result is required")
    elif "acceptance_result" in roles:
        raise EvaluationError("unexpected original result")
    for role, digest in expected.items():
        if documents[role].sha256 != digest:
            raise EvaluationError(f"source document {role} differs from the evaluation context")
    schemas = {
        "acceptance_scenario": "acceptance-scenario.v2",
        "runtime_manifest": "runtime-manifest.v2",
        "acceptance_run": "acceptance-run.v1",
        "acceptance_observation": "acceptance-observation.v2",
        "evidence_index": "evidence-index.v1",
        "acceptance_result": "acceptance-result.v2",
    }
    if any(documents[role].schema_version != schemas[role] for role in roles):
        raise EvaluationError("source document role has an unexpected schema")
    _validate_source_links(context, documents)


def _validate_source_links(
    context: EvaluationContext, documents: Mapping[str, LoadedDocument]
) -> None:
    run = documents["acceptance_run"].data
    observation = documents["acceptance_observation"].data
    if (
        run.get("run_id") != context.run_id
        or run.get("scenario_sha256") != context.bundle.scenario.sha256
        or observation.get("run_id") != context.run_id
        or observation.get("domain_id") != context.domain_id
        or observation.get("scenario_sha256") != context.bundle.scenario.sha256
        or observation.get("runtime_manifest_sha256") != context.bundle.runtime.sha256
        or context.evidence.index.data.get("run_id") != context.run_id
        or not any(
            link.get("kind") == "acceptance_observation"
            and link.get("sha256") == documents["acceptance_observation"].sha256
            for link in context.evidence.links
        )
    ):
        raise EvaluationError("run or observation differs from the evaluation context")


def build_oci_request(
    context: EvaluationContext,
    *,
    documents: Mapping[str, LoadedDocument],
    method: Mapping[str, Any],
    requirement: Mapping[str, Any],
    options: _RequestOptions,
) -> bytes:
    """Stage verified snapshots under the owned attempt and encode one evaluator request."""
    max_input_bytes = _input_budget(options["max_input_bytes"])
    _validate_raw_evidence_budget(context.max_raw_evidence_bytes)
    selected = _selected_controls(context, requirement)
    _validate_source_documents(context, documents)
    roles = set(documents)
    attempt_dir = options["attempt_dir"]
    inputs = attempt_dir / "inputs"
    objects = inputs / "objects"
    inputs.mkdir(mode=0o700)
    objects.mkdir(mode=0o700)
    sizes: dict[str, int] = {}
    used = 0

    def add(raw: bytes, digest: str) -> None:
        nonlocal used
        if sha256(raw).hexdigest() != digest:
            raise EvaluationError("captured input differs from its validated digest")
        if digest in sizes:
            return
        if len(raw) > max_input_bytes - used:
            raise EvaluationError("captured inputs exceed their total byte budget")
        path = objects / digest
        with path.open("xb") as stream:
            stream.write(raw)
        path.chmod(0o400)
        sizes[digest] = len(raw)
        used += len(raw)

    refs: dict[str, Any] = {}
    for role in sorted(roles):
        document = documents[role]
        if document.sha256 not in sizes:
            raw = read_once(document.path, min(MAX_DOCUMENT_BYTES, max_input_bytes - used))
            add(raw, document.sha256)
        refs[role] = {
            "uri": document.path.as_uri(),
            "sha256": document.sha256,
            "size_bytes": sizes[document.sha256],
        }
    add(selected.raw, selected.sha256)
    controls_ref = {
        "uri": selected.path.as_uri(),
        "sha256": selected.sha256,
        "size_bytes": len(selected.raw),
    }
    method_ref = _method_reference(method, selected)
    for digest, raw in selected.inputs.items():
        add(raw, digest)

    _stage_evidence(context, objects, sizes, max_input_bytes)
    used = sum(sizes.values())
    evidence = [dict(item) for item in context.evidence.links]
    locations = [{"sha256": digest, "path": f"objects/{digest}"} for digest in sorted(sizes)]
    request: dict[str, Any] = {
        "schema_version": "evaluator-request.v1",
        "run_id": context.run_id,
        "domain_id": context.domain_id,
        "namespace": requirement["namespace"],
        "expected_assertion_ids": list(requirement["expected_assertion_ids"]),
        "method": {**dict(method), "configuration": method_ref},
        "documents": refs,
        "controls": controls_ref,
        "evidence": evidence,
        "locations": locations,
    }
    if options["window"] is not None:
        request["window"] = dict(options["window"])
    packet = encode_evaluator_request(request)
    if used + len(packet) > max_input_bytes:
        raise EvaluationError("request and captured inputs exceed their total byte budget")
    request_path = inputs / "request.json"
    with request_path.open("xb") as stream:
        stream.write(packet)
    request_path.chmod(0o400)
    return packet


def _stage_evidence(
    context: EvaluationContext, objects: Path, sizes: dict[str, int], max_input_bytes: int
) -> None:
    for link in context.evidence.links:
        digest = str(link["sha256"])
        _sha256(digest)
        expected_size = int(link["size_bytes"])
        if (
            context.max_raw_evidence_bytes is not None
            and expected_size > context.max_raw_evidence_bytes
        ):
            raise EvaluationError("evidence exceeds its raw byte budget")
        matching = [
            (path, item)
            for path, item in context.evidence.local_files.items()
            if item["sha256"] == digest
        ]
        if not matching:
            raise EvaluationError("evidence has no captured local input")
        if digest not in sizes:
            if expected_size > max_input_bytes - sum(sizes.values()):
                raise EvaluationError("captured inputs exceed their total byte budget")
            source, reference = matching[0]
            path = objects / digest
            try:
                with path.open("xb") as sink:
                    _verified_payload(
                        source, reference, context.evidence.index.path.parent, sink=sink
                    )
            except BaseException:
                path.unlink(missing_ok=True)
                raise
            path.chmod(0o400)
            sizes[digest] = expected_size
        if sizes[digest] != expected_size:
            raise EvaluationError("evidence size differs from captured bytes")


def _input_budget(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise EvaluationError("input byte budget must be a positive integer")
    return value


def _selected_controls(
    context: EvaluationContext, requirement: Mapping[str, Any]
) -> AssessmentControls:
    selected = context.assessment_controls
    if selected is None or selected.data.get("schema_version") != "assessment-controls.v1":
        raise EvaluationError("OCI request requires versioned assessment controls")
    if (
        requirement.get("kind") != "oci"
        or requirement not in selected.data["evaluator_requirements"]
    ):
        raise EvaluationError("OCI evaluator must be declared by the captured controls")
    return selected


def _method_reference(method: Mapping[str, Any], selected: AssessmentControls) -> dict[str, Any]:
    reference = method.get("configuration")
    if not isinstance(reference, Mapping) or (
        reference.get("sha256"),
        reference.get("size_bytes"),
    ) != (selected.sha256, len(selected.raw)):
        raise EvaluationError("method configuration differs from captured controls")
    return dict(reference)
