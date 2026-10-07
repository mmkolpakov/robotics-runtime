"""Optional import of pinned SignalFlag JSONL emissions into scalar metric samples.

The caller explicitly binds topics and numeric fields to native metric names and
units, and declares that selected timestamps are Unix nanoseconds. This module
does not retain files, qualify execution, or depend on the SignalFlag SDK.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal

from robotics_runtime_contracts.serialization import (
    MAX_DOCUMENT_BYTES,
    MAX_DOCUMENT_NODES,
    loads_mapping,
)

from robotics_acceptance_harness.errors import HarnessInputError
from robotics_acceptance_harness.metrics import MetricAttribute, MetricSample


@dataclass(frozen=True, slots=True)
class MetricBinding:
    """An explicit native gauge name and unit for one emitted numeric field."""

    name: str
    unit: str

    def __post_init__(self) -> None:
        if any(type(value) is not str or not value.strip() for value in (self.name, self.unit)):
            raise HarnessInputError("emissions metric name and unit must be nonempty strings")


def _bindings_by_topic(
    bindings: Mapping[tuple[str, str], MetricBinding],
) -> dict[str, dict[str, MetricBinding]]:
    if len(bindings) > MAX_DOCUMENT_NODES:
        raise HarnessInputError("emissions bindings exceed the document node limit")
    grouped: dict[str, dict[str, MetricBinding]] = {}
    for key, binding in bindings.items():
        if (
            type(key) is not tuple
            or len(key) != 2
            or any(type(part) is not str or not part.strip() for part in key)
            or not isinstance(binding, MetricBinding)
        ):
            raise HarnessInputError("emissions bindings require (topic, field) and MetricBinding")
        topic, field = key
        grouped.setdefault(topic, {})[field] = binding
    return grouped


def _emission(line: bytes, line_number: int) -> tuple[str, dict[str, Any], dict[str, Any]]:
    document = loads_mapping(line, source_name="emissions.json")
    if set(document) != {"$metadata", "$data"}:
        raise HarnessInputError(f"emissions line {line_number} requires $metadata and $data only")
    metadata, data = document["$metadata"], document["$data"]
    if not isinstance(metadata, dict) or not isinstance(data, dict):
        raise HarnessInputError(f"emissions line {line_number} metadata and data must be objects")
    if set(metadata) - {"topic", "timestamp", "event"}:
        raise HarnessInputError(f"emissions line {line_number} has unsupported metadata")
    topic = metadata.get("topic")
    if type(topic) is not str or not topic.strip():
        raise HarnessInputError(f"emissions line {line_number} requires a nonempty topic")
    if "event" in metadata and type(metadata["event"]) is not bool:
        raise HarnessInputError(f"emissions line {line_number} event flag must be boolean")
    return topic, metadata, data


def _numeric_value(value: object, line_number: int, field: str) -> float:
    if type(value) is not int and type(value) is not float:
        raise HarnessInputError(f"emissions line {line_number} field {field!r} must be numeric")
    try:
        numeric = float(value)
    except OverflowError as error:
        raise HarnessInputError(
            f"emissions line {line_number} field {field!r} is too large"
        ) from error
    if not math.isfinite(numeric):
        raise HarnessInputError(f"emissions line {line_number} field {field!r} must be finite")
    if type(value) is int and int(numeric) != value:
        raise HarnessInputError(
            f"emissions line {line_number} field {field!r} cannot be represented exactly as a gauge"
        )
    return numeric


def _samples(
    metadata: dict[str, Any],
    data: dict[str, Any],
    fields: Mapping[str, MetricBinding],
    digest: str,
    line_number: int,
) -> list[MetricSample]:
    if not fields:
        return []
    timestamp = metadata.get("timestamp")
    if type(timestamp) is not int or timestamp < 0:
        raise HarnessInputError(
            f"selected emissions line {line_number} requires an integer Unix-ns timestamp"
        )
    output = []
    for field, binding in fields.items():
        if field not in data:
            raise HarnessInputError(f"emissions line {line_number} lacks selected field {field!r}")
        attributes: dict[str, MetricAttribute] = {
            "signalflag.source_sha256": digest,
            "signalflag.topic": metadata["topic"],
            "signalflag.field": field,
            "signalflag.line_number": line_number,
        }
        if "event" in metadata:
            attributes["signalflag.event"] = metadata["event"]
        output.append(
            MetricSample(
                name=binding.name,
                value=_numeric_value(data[field], line_number, field),
                unit=binding.unit,
                observed_at_ns=timestamp,
                attributes=attributes,
                instrument_kind="gauge",
            )
        )
    return output


def read_emissions(
    source: bytes,
    *,
    bindings: Mapping[tuple[str, str], MetricBinding],
    timestamp_basis: Literal["unix_ns"],
) -> tuple[MetricSample, ...]:
    """Convert explicitly selected fields from bounded, strict JSONL emissions.

    Timestamps must be exact nonnegative integers with the declared Unix-ns
    basis; absent timestamps are acceptable for unselected rows. Input bytes,
    line count, binding count, and result count use the existing document limits.
    Units are copied from bindings without conversion. Integer values must be
    exactly representable as native float gauges; representable powers larger
    than 2**53 remain valid. The source digest records
    byte identity only; opaque retention and independent qualification remain
    responsibilities of the caller.
    """

    if type(source) is not bytes:
        raise HarnessInputError("emissions source must be bytes")
    if type(timestamp_basis) is not str or timestamp_basis != "unix_ns":
        raise HarnessInputError("emissions timestamp_basis must be explicitly unix_ns")
    if len(source) > MAX_DOCUMENT_BYTES:
        raise HarnessInputError("emissions source exceeds the document byte limit")
    lines = source.splitlines()
    if len(lines) > MAX_DOCUMENT_NODES:
        raise HarnessInputError("emissions lines exceed the document node limit")
    grouped = _bindings_by_topic(bindings)
    digest = sha256(source).hexdigest()
    output: list[MetricSample] = []
    for line_number, line in enumerate(lines, start=1):
        topic, metadata, data = _emission(line, line_number)
        selected = grouped.get(topic, {})
        if len(output) + len(selected) > MAX_DOCUMENT_NODES:
            raise HarnessInputError("emissions samples exceed the document node limit")
        output.extend(_samples(metadata, data, selected, digest, line_number))
    return tuple(output)
