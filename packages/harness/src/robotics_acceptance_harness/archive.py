"""Read-only captured inputs for a distinct assessment of an original archive."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit
from urllib.request import url2pathname

from robotics_runtime_contracts import loads_mapping
from robotics_runtime_contracts.assessments import validate_assessment_controls
from robotics_runtime_contracts.serialization import MAX_DOCUMENT_BYTES

from robotics_acceptance_harness.documents import (
    BundleValidationError,
    LoadedDocument,
    _freeze,
    load_document_bytes,
)
from robotics_acceptance_harness.evaluator_trust import EvaluatorTrustError, read_once
from robotics_acceptance_harness.evidence import _read_local

if TYPE_CHECKING:
    from robotics_acceptance_harness.application import VerificationOutputs
    from robotics_acceptance_harness.evaluation import EvaluationContext
    from robotics_acceptance_harness.evaluator_trust import AuthenticatedInstallation
    from robotics_acceptance_harness.receipts import VerifiedReceiptSet


@dataclass(frozen=True, slots=True)
class AssessmentControls:
    """Exact control bytes and declared calibration inputs captured for one method."""

    path: Path
    raw: bytes
    inputs: Mapping[str, bytes]
    data: Mapping[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        inputs = dict(self.inputs)
        if type(self.raw) is not bytes or any(
            type(value) is not bytes for value in inputs.values()
        ):
            raise BundleValidationError("$", "assessment captures require immutable bytes")
        if len(self.raw) + sum(len(value) for value in inputs.values()) > MAX_DOCUMENT_BYTES:
            raise BundleValidationError("$", "assessment captures exceed the total byte limit")
        data = loads_mapping(self.raw, source_name=str(self.path))
        validate_assessment_controls(data)
        calibration = data.get("calibration")
        if calibration is None:
            raise BundleValidationError(
                "$.calibration", "new assessment controls require a declaration"
            )
        _capture_budget(self.raw, calibration)
        artifacts = calibration.get("artifacts", ())
        expected = {item["sha256"]: item for item in artifacts}
        if len(expected) != len(artifacts):
            raise BundleValidationError("$.calibration", "duplicate input identity")
        if set(expected) != set(inputs):
            raise BundleValidationError("$.calibration", "captured inputs differ from declarations")
        for digest, raw in inputs.items():
            if len(raw) != expected[digest]["size_bytes"] or sha256(raw).hexdigest() != digest:
                raise BundleValidationError(
                    "$.calibration", "captured bytes differ from declaration"
                )
        object.__setattr__(self, "data", _freeze(data))
        object.__setattr__(self, "inputs", MappingProxyType(inputs))

    @property
    def sha256(self) -> str:
        return sha256(self.raw).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return loads_mapping(self.raw, source_name=str(self.path))

    def read_input(self, reference: Mapping[str, Any]) -> bytes:
        """Return a captured declared calibration input without reading its path again."""
        digest = str(reference["sha256"])
        raw = self.inputs.get(digest)
        if raw is None or len(raw) != reference["size_bytes"]:
            raise BundleValidationError("$.calibration", "input is not a captured method input")
        return raw


def _capture_budget(raw: bytes, calibration: Mapping[str, Any]) -> None:
    sizes = [item["size_bytes"] for item in calibration.get("artifacts", ())]
    if any(size > MAX_DOCUMENT_BYTES for size in sizes):
        raise BundleValidationError("$.calibration", "input exceeds the per-file byte limit")
    if len(raw) + sum(sizes) > MAX_DOCUMENT_BYTES:
        raise BundleValidationError("$.calibration", "inputs exceed the total capture byte limit")


def load_assessment_controls(path: str | Path) -> AssessmentControls:
    """Capture explicit method controls and their local calibration bytes once."""
    source = Path(path).expanduser().absolute()
    try:
        raw = read_once(source, MAX_DOCUMENT_BYTES)
    except (EvaluatorTrustError, OSError) as failure:
        raise BundleValidationError("$.evaluation.method.configuration", str(failure)) from failure
    data = loads_mapping(raw, source_name=str(source))
    validate_assessment_controls(data)
    calibration = data.get("calibration")
    if calibration is None:
        raise BundleValidationError(
            "$.calibration", "new assessment controls require a declaration"
        )
    _capture_budget(raw, calibration)
    inputs: dict[str, bytes] = {}
    if calibration["state"] == "selected":
        if data["assertions"] or not data["evaluator_requirements"]:
            raise BundleValidationError(
                "$.calibration",
                "selected calibration requires a product method; core metrics cannot apply it",
            )
        for index, reference in enumerate(calibration["artifacts"]):
            uri = urlsplit(reference["uri"])
            if uri.scheme != "file" or uri.netloc not in {"", "localhost"}:
                raise BundleValidationError(
                    f"$.calibration.artifacts[{index}].uri", "requires a local captured input"
                )
            digest = str(reference["sha256"])
            if digest in inputs:
                raise BundleValidationError("$.calibration.artifacts", "duplicate input identity")
            payload = _read_local(
                Path(url2pathname(uri.path)),
                reference,
                source.parent,
                f"$.calibration.artifacts[{index}]",
                capture=True,
            )
            inputs[digest] = payload
    return AssessmentControls(source, raw, MappingProxyType(inputs))


def load_original_result(path: str | Path) -> LoadedDocument:
    """Validate and retain the identity of the exact bounded original result bytes."""
    source = Path(path).expanduser().absolute()
    try:
        raw = read_once(source, MAX_DOCUMENT_BYTES)
    except (EvaluatorTrustError, OSError) as failure:
        raise BundleValidationError(
            "$.original_execution.original_result_sha256", str(failure)
        ) from failure
    return load_document_bytes(raw, source=source, expected_role="acceptance_result")


def assess_archive(
    context: EvaluationContext,
    run_context: LoadedDocument,
    output_dir: str | Path,
    *,
    evaluator_receipts: VerifiedReceiptSet | None = None,
    evaluator_authentications: Mapping[str, AuthenticatedInstallation] | None = None,
) -> VerificationOutputs:
    """Assess captured native source inputs using explicit controls and public writers."""
    from robotics_acceptance_harness.application import VerificationOutputs
    from robotics_acceptance_harness.native import evaluate_native
    from robotics_acceptance_harness.result import write_contract_json, write_junit_xml

    if context.bundle.scenario.schema_version != "acceptance-scenario.v2":
        raise BundleValidationError("$", "archive assessment requires native v2 source inputs")
    if context.scenario["execution"]["target_environment"] in {"hil", "real_robot"}:
        raise BundleValidationError("$", "physical archive qualification is not supported")
    if context.assessment_controls is None:
        raise BundleValidationError("$.evaluation.method", "archive assessment requires controls")
    result = evaluate_native(
        context, run_context, output_dir, evaluator_receipts, evaluator_authentications
    )
    destination = Path(output_dir).expanduser().resolve()
    result_path = write_contract_json(result, destination / "acceptance-result.json")
    junit_path = write_junit_xml(result, destination / "junit.xml")
    return VerificationOutputs(result, result_path, junit_path)
