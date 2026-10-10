from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from types import MappingProxyType
from typing import Any, cast

from robotics_runtime_contracts.errors import ContractError


class UnknownContractRoleError(ContractError):
    """Raised when a caller requests an unpublished document role."""

    error_id = "schema.role_unknown"


@cache
def _catalog() -> dict[str, Any]:
    resource = files("robotics_runtime_contracts").joinpath("schemas", "catalog.v1.json")
    return cast(dict[str, Any], json.loads(resource.read_text(encoding="utf-8")))


def contract_set() -> str:
    """Return the single published contract-set identifier."""

    return str(_catalog()["contract_set"])


def role_schemas() -> MappingProxyType[str, str]:
    """Return the immutable role-to-schema catalog."""

    return MappingProxyType(dict(_catalog()["roles"]))


def contract_roles() -> tuple[str, ...]:
    """Return published document roles in stable order."""

    return tuple(role_schemas())


def schema_versions_for_role(role: str) -> tuple[str, ...]:
    """Return the supported schemas without changing the role's canonical default."""
    try:
        canonical = role_schemas()[role]
    except KeyError as error:
        raise UnknownContractRoleError(f"Unknown contract role: {role}") from error
    additional = _catalog().get("supported_versions", {}).get(role, ())
    return (canonical, *(str(name) for name in additional))


def schema_for_role(role: str, *, version: int | None = None) -> str:
    """Resolve a public document role to its canonical schema."""

    names = schema_versions_for_role(role)
    if version is None:
        return names[0]
    for name in names:
        if name.endswith(f".v{version}"):
            return name
    raise UnknownContractRoleError(f"Unsupported version {version} for contract role: {role}")


def internal_schema_names() -> tuple[str, ...]:
    """Return schema resources used only for modular references."""

    return tuple(str(item) for item in _catalog()["internal_resources"])
