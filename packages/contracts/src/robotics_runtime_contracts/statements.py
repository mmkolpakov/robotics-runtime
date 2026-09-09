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
) -> dict[str, Any]:
    """Validate KIND:SUBJECT=PATH inputs and bind the exact bytes validation read.

    The artifact validator owns parsing, cross-document validation and hashing.
    Its metadata is used directly: no input is reserialized or rehashed here.
    The timestamp comes from the validated aggregate; run identity comes from
    the validated run. Neither value is a writer default.
    """
    return _statement_from_metadata(
        validate_qualification_artifacts(specifications, extension_schemas)
    )


def _statement_from_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    artifacts = metadata["artifacts"]
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {"name": item["subject_name"], "digest": {"sha256": item["sha256"]}}
            for item in artifacts
        ],
        "predicateType": "https://robotics-runtime-contracts.dev/attestations/qualification-bundle/v1",
        "predicate": {
            "schema_version": "qualification-bundle.v1",
            "run_id": metadata["run_id"],
            "generated_at": metadata["generated_at"],
            "artifacts": [
                {"kind": item["kind"], "subject_name": item["subject_name"]} for item in artifacts
            ],
        },
    }
    validate_document(statement, schema="qualification-bundle.v1")
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
    validate_document(
        candidate, schema="qualification-bundle.v1", extension_schemas=extension_schemas
    )
    metadata = validate_qualification_artifacts(specifications, extension_schemas)
    expected = _statement_from_metadata(metadata)
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
) -> Path:
    """Atomically write a deterministic statement after complete link validation."""
    statement = create_qualification_statement(specifications, extension_schemas=extension_schemas)
    # Specifications have already been checked by the qualification validator.
    protect_inputs(output, [item.partition("=")[2] for item in specifications])
    return write_document(statement, output, schema="qualification-bundle.v1")


__all__ = [
    "create_qualification_statement",
    "validate_qualification_statement",
    "write_qualification_statement",
]
