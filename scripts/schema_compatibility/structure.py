"""Bounded D10 comparison, not a general JSON Schema implication solver."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from scripts.bundle_schemas import (
    Schema,
    check_references,
    registry_for,
    schema_locations,
    subschemas,
)

METADATA = {"description", "title", "examples"}
ADDRESSING = {"$ref", "$defs", "$id", "$schema"}
MAPS = {"properties", "patternProperties", "dependentSchemas"}
SEQUENCES = {"allOf", "anyOf", "oneOf", "prefixItems"}
SINGLES = {
    "additionalProperties",
    "items",
    "contains",
    "propertyNames",
    "not",
    "if",
    "then",
    "else",
    "unevaluatedProperties",
    "unevaluatedItems",
}
LITERALS = {
    "type",
    "const",
    "enum",
    "required",
    "pattern",
    "format",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minProperties",
    "maxProperties",
    "minContains",
    "maxContains",
    "dependentRequired",
    "default",
    "$comment",
}
SUPPORTED = METADATA | ADDRESSING | MAPS | SEQUENCES | SINGLES | LITERALS
POSITIVE = {"properties", "items", "allOf", "anyOf", "then", "else", "$ref", "prefixItems"}
INPUT_ROLES = {
    "acceptance_scenario",
    "qualification_profile",
    "runtime_manifest",
    "dataset_manifest",
    "model_artifact_manifest",
}
# These internal roots are also checked independently of the public wrappers.
INPUT_CORES = {"acceptance-scenario-core.v1", "runtime-manifest-core.v1"}


class ReviewRequired(ValueError):
    """The supported D10 rules cannot establish compatibility."""


class Resolver(Protocol):
    def lookup(self, ref: str) -> Any: ...


@dataclass
class Node:
    keywords: dict[str, Any]
    reference: Node | bool | None = None


def token(value: Any) -> str:
    """Compare JSON types exactly, including bool/int and literal instance data."""
    encoder = json.JSONEncoder(sort_keys=True, allow_nan=False, default=_node_json)
    chunks = []
    length = 0
    for chunk in encoder.iterencode(value):
        length += len(chunk)
        if length > 4_000_000:
            raise ReviewRequired("Expanded comparison token exceeds 4 million characters")
        chunks.append(chunk)
    return "".join(chunks)


def _node_json(value: Node) -> dict[str, Any]:
    own = value.keywords
    # This is a comparison token, never an emitted JSON Schema. Ref siblings
    # remain adjacent; moving them into allOf changes evaluated annotations.
    return {"$ref": value.reference, **own} if value.reference is not None else own


class Expansion:
    def __init__(self, schemas: dict[str, Schema]) -> None:
        check_references(schemas)
        self.registry = registry_for(schemas)
        self.locations = schema_locations(self.registry)
        self.cache: dict[int, Node | bool] = {}
        for name, schema in schemas.items():
            resolver = self.registry.resolver(schema["$id"])
            for node in subschemas(schema):
                unknown = set(node) - SUPPORTED
                if unknown:
                    raise ReviewRequired(f"{name}: unsupported keywords {sorted(unknown)}")
                # Include unused definitions in domain and cycle checks.
                self.visit(node, resolver, frozenset())

    def visit(self, value: Any, resolver: Resolver, active: frozenset[int]) -> Any:
        if isinstance(value, list):
            return [self.visit(item, resolver, active) for item in value]
        if not isinstance(value, dict):
            return value
        if id(value) not in self.locations:
            return {key: self.visit(item, resolver, active) for key, item in value.items()}
        if id(value) in active or len(active) >= 128:
            raise ReviewRequired("Reference cycle or schema depth over 128")
        if id(value) not in self.cache:
            self.cache[id(value)] = self.expand(value, resolver, active | {id(value)})
        return self.cache[id(value)]

    def expand(self, value: Schema, resolver: Resolver, active: frozenset[int]) -> Node | bool:
        own = {
            key: self.visit(item, resolver, active)
            for key, item in value.items()
            if key not in METADATA | ADDRESSING
        }
        if "$ref" not in value:
            return Node(own)
        resolved = resolver.lookup(value["$ref"])
        target: Node | bool = self.visit(resolved.contents, resolved.resolver, active)
        return Node(own, target) if own else target

    def root(self, schema: Schema) -> Node | bool:
        return self.cache[id(schema)]


@dataclass(frozen=True)
class Context:
    path: str
    input_document: bool = False
    positive: bool = True

    def child(self, key: str, positive: bool = True) -> Context:
        return Context(f"{self.path}/{key}", self.input_document, self.positive and positive)

    def reject(self, reason: str) -> None:
        raise ReviewRequired(f"{self.path}: {reason}")


def compare(before: Node | bool, after: Node | bool, context: Context) -> None:
    if token(before) == token(after):
        return
    if not context.positive or not isinstance(before, Node) or not isinstance(after, Node):
        context.reject("changed assertion in a frozen context")
        return
    if (before.reference is None) != (after.reference is None):
        context.reject("changed reference/sibling evaluation scope")
    if before.reference is not None and after.reference is not None:
        compare(before.reference, after.reference, context.child("$ref"))
    sensitive = {"unevaluatedProperties", "unevaluatedItems"}
    if sensitive & (before.keywords.keys() | after.keywords.keys()):
        context.reject("changed annotation-dependent schema needs explicit review")
    if before.keywords.keys() - {"properties"} != after.keywords.keys() - {"properties"}:
        context.reject("added or removed assertion keywords")
    for key in before.keywords.keys() | after.keywords.keys():
        _keyword(key, before.keywords.get(key, {}), after.keywords.get(key, {}), (before, context))


def _keyword(key: str, old: Any, new: Any, parent: tuple[Node, Context]) -> None:
    node, context = parent
    if token(old) == token(new):
        return
    child = context.child(key, key in POSITIVE)
    if key == "oneOf" and _disjoint_objects(old) and _disjoint_objects(new):
        child = context.child(key)
    if key == "enum" and context.input_document and context.positive:
        if {token(item) for item in old} <= {token(item) for item in new}:
            return
    elif key == "properties":
        _properties(old, new, node, child)
        return
    elif key in SINGLES:
        compare(old, new, child)
        return
    elif key in SEQUENCES and len(old) == len(new):
        for index, (left, right) in enumerate(zip(old, new, strict=True)):
            compare(left, right, child.child(str(index)))
        return
    context.child(key).reject("change is not an automatically allowed D10 addition")


def _string_discriminators(branch: Node | bool) -> dict[str, str]:
    if not isinstance(branch, Node) or branch.keywords.get("type") != "object":
        return {}
    result = {}
    properties = branch.keywords.get("properties", {})
    for name in branch.keywords.get("required", []):
        constraint = properties.get(name)
        if isinstance(constraint, Node):
            value = constraint.keywords.get("const")
            if isinstance(value, str):
                result[name] = value
    return result


def _disjoint_objects(branches: list[Node | bool]) -> bool:
    """Prove branches cannot overlap using a required, unique string constant.

    Schema relaxation within an arbitrary oneOf can reject old instances by
    making two branches match. An unchanged exclusive discriminator rules out
    that counterexample; normal D10 comparison still checks every assertion.
    """
    if not branches:
        return False
    discriminators = [_string_discriminators(branch) for branch in branches]
    common = set.intersection(*(set(item) for item in discriminators))
    return any(len({item[name] for item in discriminators}) == len(branches) for name in common)


def _properties(old: Schema, new: Schema, parent: Node, context: Context) -> None:
    if old.keys() - new.keys():
        context.reject("removed or renamed property")
    added = new.keys() - old.keys()
    if added:
        closed = parent.keywords.get("additionalProperties") is False
        ambiguous = {"patternProperties", "unevaluatedProperties"} & parent.keywords.keys()
        required = set(parent.keywords.get("required", []))
        if not context.positive or not closed or ambiguous or added & required:
            context.reject("optional property is not proved additive in this object context")
    for name, old_value in old.items():
        compare(old_value, new[name], context.child(name))


def check_catalog(catalog: Schema, schemas: dict[str, Schema]) -> None:
    if set(catalog) != {"contract_set", "roles", "internal_resources"}:
        raise ReviewRequired("Unsupported catalog structure")
    roles, internal = catalog["roles"], catalog["internal_resources"]
    if not isinstance(roles, dict) or not isinstance(internal, list):
        raise ReviewRequired("Invalid catalog role/internal inventory")
    names = list(roles.values()) + internal
    if any(not isinstance(name, str) for name in names):
        raise ReviewRequired("Catalog schema names must be strings")
    if len(set(names)) != len(names) or {f"{name}.schema.json" for name in names} != schemas.keys():
        raise ReviewRequired("Catalog must enumerate each resource exactly once")


def check_structure(
    before: dict[str, Schema], after: dict[str, Schema], old_catalog: Schema, new_catalog: Schema
) -> int:
    """Require retained identities and only proved D10 additions in reachable trees."""
    check_catalog(old_catalog, before)
    check_catalog(new_catalog, after)
    if old_catalog["contract_set"] != new_catalog["contract_set"]:
        raise ReviewRequired("Changed contract_set")
    for role, name in old_catalog["roles"].items():
        if new_catalog["roles"].get(role) != name:
            raise ReviewRequired(f"Removed or renamed published role: {role}")
    if set(old_catalog["internal_resources"]) - set(new_catalog["internal_resources"]):
        raise ReviewRequired("Removed published internal resources")
    left, right = Expansion(before), Expansion(after)
    inputs = INPUT_CORES | {
        name for role, name in old_catalog["roles"].items() if role in INPUT_ROLES
    }
    for name, schema in before.items():
        if name not in after or schema["$id"] != after[name]["$id"]:
            raise ReviewRequired(f"Removed resource or changed $id: {name}")
        context = Context(name, name.removesuffix(".schema.json") in inputs)
        compare(left.root(schema), right.root(after[name]), context)
    return len(before)
