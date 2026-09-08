from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from secrets import token_hex
from typing import Any
from uuid import uuid4

from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012

from robotics_runtime_contracts import (
    load_schema,
    resolve_schema_name,
    schema_digest,
    schema_registry,
    validate_document,
)
from robotics_runtime_contracts._merge_patch import JSONValue, create_patch, json_equal, merge_patch
from robotics_runtime_contracts.errors import ContractError
from robotics_runtime_contracts.serialization import ensure_finite_numbers


def _resolve_property(
    value: Mapping[str, Any],
    *,
    current_schema: Mapping[str, Any],
) -> Mapping[str, Any]:
    resolved = value
    resolver = schema_registry().resolver_with_root(
        DRAFT202012.create_resource(dict(current_schema))
    )
    resolver = resolver.in_subresource(DRAFT202012.create_resource(dict(value)))
    visited: set[int] = set()
    while "$ref" in resolved:
        reference = str(resolved["$ref"])
        if id(resolved) in visited:
            raise ContractError(
                f"cyclic schema reference: {reference}", error_id="schema.reference_invalid"
            )
        visited.add(id(resolved))
        try:
            lookup = resolver.lookup(reference)
        except Unresolvable as error:
            raise ContractError(
                f"unresolvable schema reference: {reference}", error_id="schema.reference_invalid"
            ) from error
        target = lookup.contents
        if isinstance(target, bool):
            return {}
        if not isinstance(target, Mapping):
            raise ContractError(
                f"schema reference does not resolve to a schema: {reference}",
                error_id="schema.reference_invalid",
            )
        resolved = target
        resolver = lookup.resolver
    return resolved


def describe_schema(schema_name: str) -> dict[str, Any]:
    """Return a stable, machine-readable summary derived from a published schema."""

    canonical_name = resolve_schema_name(schema_name)
    schema = load_schema(canonical_name)
    properties = schema.get("properties", {})
    return {
        "schema": canonical_name,
        "id": schema["$id"],
        "sha256": schema_digest(canonical_name),
        "title": schema.get("title", ""),
        "description": schema.get("description", ""),
        "required": list(schema.get("required", [])),
        "properties": {
            name: {
                key: resolved[key]
                for key in ("type", "description", "const", "enum", "$ref")
                if key in resolved
            }
            for name, value in properties.items()
            for resolved in (_resolve_property(value, current_schema=schema),)
        },
    }


def resolve_merge_patches(
    base: Mapping[str, Any],
    overlays: Sequence[Mapping[str, Any]],
    *,
    extension_schemas: Mapping[str, bytes | str] | None = None,
) -> dict[str, Any]:
    """Materialize RFC 7396 overlays and validate the resulting document."""

    ensure_finite_numbers(base)
    resolved: dict[str, JSONValue] = deepcopy(dict(base))
    for overlay in overlays:
        ensure_finite_numbers(overlay)
        merged = merge_patch(resolved, dict(overlay))
        assert isinstance(merged, dict)  # An object patch always produces an object.
        resolved = merged
    validate_document(resolved, extension_schemas=extension_schemas)
    return resolved


def semantic_diff(
    source: Mapping[str, Any],
    target: Mapping[str, Any],
) -> dict[str, Any]:
    """Return an RFC 7396 patch preserving parsed JSON scalar types."""

    ensure_finite_numbers(source)
    ensure_finite_numbers(target)
    patch = create_patch(dict(source), dict(target))
    if not json_equal(merge_patch(dict(source), patch), dict(target)):
        raise ContractError(
            "target cannot be represented by RFC 7396 because null denotes member removal",
            error_id="diff.unrepresentable",
        )
    return patch


def create_execution_permit(
    *,
    scenario_sha256: str,
    subject_digest: str,
    trust_policy_sha256: str,
    environment: str,
    target_id: str,
    identity_kind: str,
    identity_sha256: str,
    hardware_scope: Sequence[str],
    operator_id: str,
    approver_id: str,
    interlock_reference: str,
    interlock_sha256: str,
    validity_sec: int = 900,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create a validated, unsigned physical-execution permit predicate."""

    if not 1 <= validity_sec <= 1800:
        raise ContractError("validity_sec must be between 1 and 1800")
    issued_at = (now or datetime.now(UTC)).astimezone(UTC)
    expires_at = issued_at + timedelta(seconds=validity_sec)
    document = {
        "schema_version": "execution-permit.v1",
        "predicate_type": (
            "https://robotics-runtime-contracts.dev/attestations/execution-permit/v1"
        ),
        "permit_id": f"permit-{uuid4()}",
        "scenario_sha256": scenario_sha256,
        "subject_digest": subject_digest,
        "trust_policy_sha256": trust_policy_sha256,
        "target": {
            "environment": environment,
            "target_id": target_id,
            "identity_kind": identity_kind,
            "identity_sha256": identity_sha256,
        },
        "allowed_physical_effect": "none" if environment == "hil" else "observation",
        "hardware_scope": list(hardware_scope),
        "issued_at": issued_at.isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "nonce": token_hex(32),
        "operator_id": operator_id,
        "approver_id": approver_id,
        "interlock_check": {
            "reference": interlock_reference,
            "sha256": interlock_sha256,
            "status": "passed",
            "checked_at": issued_at.isoformat().replace("+00:00", "Z"),
        },
    }
    validate_document(document)
    return document


__all__ = [
    "create_execution_permit",
    "describe_schema",
    "resolve_merge_patches",
    "semantic_diff",
]
