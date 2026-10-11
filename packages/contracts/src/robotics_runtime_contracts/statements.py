"""Unsigned in-toto qualification statements over validated artifact bytes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from robotics_runtime_contracts import (
    ContractError,
    dumps_canonical,
    load_mapping,
    validate_document,
)
from robotics_runtime_contracts.qualification import validate_qualification_artifacts
from robotics_runtime_contracts.writers import protect_inputs, write_document


def create_qualification_statement(
    specifications: Sequence[str],
    *,
    extension_schemas: Mapping[str, bytes] | None = None,
    schema_version: str = "qualification-bundle.v1",
    comparison_rule: str | None = None,
) -> dict[str, Any]:
    """Validate KIND:SUBJECT=PATH inputs and bind the exact bytes validation read.

    The artifact validator owns parsing, cross-document validation and hashing.
    Its metadata is used directly: no input is reserialized or rehashed here.
    The timestamp comes from the validated aggregate; run identity comes from
    the validated run. Neither value is a writer default.
    """
    _require_options(schema_version, comparison_rule)
    if schema_version == "qualification-bundle.v1":
        metadata = validate_qualification_artifacts(specifications, extension_schemas)
    else:
        metadata = validate_qualification_artifacts(
            specifications,
            extension_schemas,
            schema_version=schema_version,
            comparison_rule=comparison_rule,
        )
    return _statement_from_metadata(metadata, schema_version)


def _require_options(schema_version: str, comparison_rule: str | None) -> None:
    if schema_version not in ("qualification-bundle.v1", "qualification-bundle.v2"):
        raise ContractError(
            f"unsupported qualification statement version: {schema_version}",
            error_id="qualification.schema_unsupported",
            json_path="$.predicate.schema_version",
        )
    valid_rule = (
        comparison_rule is None
        if schema_version == "qualification-bundle.v1"
        else comparison_rule == "exact_assertion_outcome"
    )
    if not valid_rule:
        raise ContractError(
            "v1 accepts no comparison rule; v2 requires exact_assertion_outcome",
            error_id="qualification.comparison_rule_invalid",
            json_path="$.predicate.comparison.rule",
        )


def _statement_from_metadata(
    metadata: Mapping[str, Any], schema_version: str = "qualification-bundle.v1"
) -> dict[str, Any]:
    artifacts = metadata["artifacts"]
    predicate = {
        "schema_version": schema_version,
        "run_id": metadata["run_id"],
        "generated_at": metadata["generated_at"],
        "artifacts": [
            {"kind": item["kind"], "subject_name": item["subject_name"]} for item in artifacts
        ],
    }
    if schema_version == "qualification-bundle.v2":
        for field in ("original_execution", "acceptance_aggregate", "assessments", "comparison"):
            predicate[field] = metadata[field]
    version = schema_version.rsplit(".", 1)[1]
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {"name": item["subject_name"], "digest": {"sha256": item["sha256"]}}
            for item in artifacts
        ],
        "predicateType": (
            "https://robotics-runtime-contracts.dev/attestations/qualification-bundle/" + version
        ),
        "predicate": predicate,
    }
    validate_document(statement, schema=schema_version)
    return statement


def validate_qualification_statement(
    statement: str | Path,
    specifications: Sequence[str],
    *,
    extension_schemas: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    """Match a decoded statement to a fully validated local artifact set.

    Return the artifact metadata from the same reads used for comparison.
    Object formatting is immaterial; subject/classification arrays must use the
    writer's sorted order. Neither the statement nor its subjects are rewritten.
    Signature verification is the caller's responsibility and must authenticate
    the exact statement bytes passed here.

    Predicate extensions must pass their supplied, digest-pinned schemas. They
    carry domain claims, never replacements for the core artifact bindings.
    """
    candidate = load_mapping(statement)
    predicate = candidate.get("predicate")
    schema_version = predicate.get("schema_version") if isinstance(predicate, Mapping) else None
    if not isinstance(predicate, Mapping) or not isinstance(schema_version, str):
        raise ContractError(
            "statement predicate must declare a supported schema_version",
            error_id="qualification.schema_unsupported",
            json_path="$.predicate.schema_version",
        )
    if schema_version not in ("qualification-bundle.v1", "qualification-bundle.v2"):
        _require_options(schema_version, None)
    validate_document(candidate, schema=schema_version, extension_schemas=extension_schemas)
    comparison_rule = (
        predicate["comparison"]["rule"] if schema_version == "qualification-bundle.v2" else None
    )
    _require_options(schema_version, comparison_rule)
    if schema_version == "qualification-bundle.v1":
        metadata = validate_qualification_artifacts(specifications, extension_schemas)
    else:
        metadata = validate_qualification_artifacts(
            specifications,
            extension_schemas,
            schema_version=schema_version,
            comparison_rule=comparison_rule,
        )
    expected = _statement_from_metadata(metadata, schema_version)
    for field in ("extension_schemas", "extensions"):
        if field in candidate["predicate"]:
            expected["predicate"][field] = candidate["predicate"][field]
    if dumps_canonical(candidate) != dumps_canonical(expected):
        raise ContractError(
            "statement does not exactly match local subjects, digests, and classifications",
            error_id="qualification.statement_mismatch",
            json_path="$",
        )
    return metadata


def write_qualification_statement(
    specifications: Sequence[str],
    output: str | Path,
    *,
    extension_schemas: Mapping[str, bytes] | None = None,
    schema_version: str = "qualification-bundle.v1",
    comparison_rule: str | None = None,
) -> Path:
    """Atomically write a deterministic statement after complete link validation."""
    statement = create_qualification_statement(
        specifications,
        extension_schemas=extension_schemas,
        schema_version=schema_version,
        comparison_rule=comparison_rule,
    )
    # Specifications have already been checked by the qualification validator.
    protect_inputs(output, [item.partition("=")[2] for item in specifications])
    return write_document(statement, output, schema=schema_version)


__all__ = [
    "create_qualification_statement",
    "validate_qualification_statement",
    "write_qualification_statement",
]
