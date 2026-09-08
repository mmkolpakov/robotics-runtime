"""Unsigned in-toto qualification statements over validated artifact bytes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from robotics_runtime_contracts import validate_document
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
    Timestamp/run identity come from the validated run, not writer defaults.
    """
    metadata = validate_qualification_artifacts(specifications, extension_schemas)
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


__all__ = ["create_qualification_statement", "write_qualification_statement"]
