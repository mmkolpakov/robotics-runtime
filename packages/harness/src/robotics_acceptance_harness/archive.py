"""Read-only captured inputs for a distinct assessment of an original archive."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import urlsplit
from urllib.request import url2pathname

from robotics_runtime_contracts import loads_mapping
from robotics_runtime_contracts.assessments import validate_assessment_controls
from robotics_runtime_contracts.serialization import read_document_bytes

from robotics_acceptance_harness.documents import BundleValidationError, _freeze
from robotics_acceptance_harness.evidence import _read_local


@dataclass(frozen=True, slots=True)
class AssessmentControls:
    """Exact control bytes and declared calibration inputs captured for one method."""

    path: Path
    raw: bytes
    data: Mapping[str, Any]
    inputs: Mapping[str, bytes]

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


def load_assessment_controls(path: str | Path) -> AssessmentControls:
    """Capture explicit method controls and their local calibration bytes once."""
    source = Path(path).expanduser().resolve()
    raw = read_document_bytes(source)
    data = loads_mapping(raw, source_name=str(source))
    validate_assessment_controls(data)
    calibration = data.get("calibration")
    if calibration is None:
        raise BundleValidationError(
            "$.calibration", "new assessment controls require a declaration"
        )
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
    return AssessmentControls(source, raw, _freeze(data), MappingProxyType(inputs))
