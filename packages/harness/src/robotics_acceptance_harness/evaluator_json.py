"""Finite evaluator packets; execution and captured-input custody belong to the caller."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from functools import cache
from importlib.resources import files
from typing import Any, Literal, cast

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from robotics_runtime_contracts import (
    ContractError,
    dumps_canonical,
    loads_mapping,
    schema_registry,
)

from robotics_acceptance_harness.evaluation import EvaluationError, _validate_product_evaluation
from robotics_acceptance_harness.metrics import AssertionEvaluation

MAX_PACKET_BYTES = 1024 * 1024
MAX_PACKET_ITEMS = 256
_COMMON = "urn:robotics-runtime-contracts:v1:internal:common#/$defs/"
_ASSERTION = "urn:robotics-runtime-contracts:v1:acceptance-result#/$defs/assertionResult"


@cache
def _validator(name: str) -> Draft202012Validator:
    resource = files("robotics_acceptance_harness").joinpath(
        "schemas", f"evaluator-{name}.v1.schema.json"
    )
    schema = loads_mapping(resource.read_bytes(), source_name="evaluator-schema.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=schema_registry(), format_checker=FormatChecker())


@cache
def _fragment_validator(reference: str) -> Draft202012Validator:
    return Draft202012Validator(
        {"$ref": reference}, registry=schema_registry(), format_checker=FormatChecker()
    )


def _check_fragment(value: Any, reference: str, label: str) -> None:
    try:
        _fragment_validator(reference).validate(value)
    except ValidationError as error:
        raise EvaluationError(f"{label}: {error.message}") from error


def _parse(raw: bytes, name: str) -> dict[str, Any]:
    if not isinstance(raw, bytes):
        raise EvaluationError(f"evaluator {name} must be captured bytes")
    if len(raw) > MAX_PACKET_BYTES:
        raise EvaluationError(f"evaluator {name} exceeds {MAX_PACKET_BYTES} bytes")
    try:
        document = loads_mapping(raw, source_name=f"evaluator-{name}.json")
        _validator(name).validate(document)
    except (ContractError, ValidationError) as error:
        raise EvaluationError(f"invalid evaluator {name}: {error}") from error
    return dict(document)


def _expected_ids(namespace: str, identifiers: Sequence[str]) -> frozenset[str]:
    _check_fragment(namespace, _ASSERTION + "/properties/namespace", "evaluator namespace")
    if len(namespace) > 128:
        raise EvaluationError("evaluator namespace exceeds 128 characters")
    if (
        isinstance(identifiers, (str, bytes))
        or not isinstance(identifiers, Sequence)
        or not 1 <= len(identifiers) <= MAX_PACKET_ITEMS
    ):
        raise EvaluationError("expected_assertion_ids must contain 1 to 256 identifiers")
    for identifier in identifiers:
        _check_fragment(identifier, _COMMON + "identifier", "expected assertion ID")
        if not identifier.startswith(f"{namespace}."):
            raise EvaluationError(f"expected assertion {identifier!r} is outside namespace")
    expected = frozenset(identifiers)
    if len(expected) != len(identifiers):
        raise EvaluationError("expected_assertion_ids contains duplicate identifiers")
    return expected


def _check_request(document: Mapping[str, Any]) -> None:
    _expected_ids(document["namespace"], document["expected_assertion_ids"])
    locations: dict[str, str] = {}
    paths: set[str] = set()
    for location in document["locations"]:
        digest, path = location["sha256"], location["path"]
        if (
            "\\" in path
            or "\x00" in path
            or any(component in {"", ".", ".."} for component in path.split("/"))
        ):
            raise EvaluationError("location path must be a confined relative POSIX path")
        if digest in locations or path in paths:
            raise EvaluationError("location digests and paths must be unique")
        locations[digest] = path
        paths.add(path)
    references = [
        *document["documents"].values(),
        document["method"]["configuration"],
        document["controls"],
    ]
    if any(reference["sha256"] not in locations for reference in references):
        raise EvaluationError("every document, method configuration and controls needs a location")
    window = document.get("window")
    if window is not None and window["start_ns"] >= window["end_ns"]:
        raise EvaluationError("measurement window start_ns must precede end_ns")


def encode_evaluator_request(request: Mapping[str, Any]) -> bytes:
    """Validate prepared data and encode it; this does not verify referenced file bytes."""
    if not isinstance(request, Mapping):
        raise EvaluationError("evaluator request must be a mapping")
    try:
        raw = dumps_canonical(dict(request))
    except ContractError as error:
        raise EvaluationError(f"invalid evaluator request: {error}") from error
    _check_request(_parse(raw, "request"))
    return raw


def decode_evaluator_response(
    raw: bytes,
    *,
    request_sha256: str,
    namespace: str,
    expected_assertion_ids: Sequence[str],
    allowed_evidence_sha256: Collection[str],
) -> tuple[AssertionEvaluation, ...]:
    """Decode captured bytes against trusted bindings, without admitting or executing code."""
    _check_fragment(request_sha256, _COMMON + "sha256", "request_sha256")
    expected = _expected_ids(namespace, expected_assertion_ids)
    if isinstance(allowed_evidence_sha256, (str, bytes)) or not isinstance(
        allowed_evidence_sha256, Collection
    ):
        raise EvaluationError("allowed_evidence_sha256 must be a collection of digests")
    for digest in allowed_evidence_sha256:
        _check_fragment(digest, _COMMON + "sha256", "allowed evidence digest")
    allowed = frozenset(allowed_evidence_sha256)
    response = _parse(raw, "response")
    if response["request_sha256"] != request_sha256:
        raise EvaluationError("evaluator response does not match the captured request SHA-256")
    evaluations: list[AssertionEvaluation] = []
    identifiers: set[str] = set()
    for row in response["assertion_results"]:
        evaluation = AssertionEvaluation(
            assertion_id=row["assertion_id"],
            status=cast(Literal["passed", "failed", "error", "skipped"], row["status"]),
            observed_value=row["observed_value"],
            unit=row["unit"],
            message=row.get("message", ""),
            source="product",
            namespace=row["namespace"],
            evidence_sha256=tuple(row["evidence_sha256"]),
        )
        _validate_product_evaluation(namespace, evaluation, allowed)
        if evaluation.assertion_id in identifiers:
            raise EvaluationError(f"duplicate assertion ID {evaluation.assertion_id!r}")
        identifiers.add(evaluation.assertion_id)
        evaluations.append(evaluation)
    if identifiers != expected:
        raise EvaluationError(
            "evaluator response assertion IDs differ from expected set: "
            f"missing={sorted(expected - identifiers)}, extra={sorted(identifiers - expected)}"
        )
    return tuple(evaluations)


__all__ = ["decode_evaluator_response", "encode_evaluator_request"]
