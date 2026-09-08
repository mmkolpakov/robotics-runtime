"""Compare resolved assertions and fixture outcomes with the frozen pre-refactor schemas.

This is a refactor-specific equality gate, not the future additive-release checker.
URI, pointer and anchor resolution belongs entirely to referencing.
"""

import gzip
import json
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any, Protocol

import pytest
from jsonschema import Draft202012Validator
from jsonschema.validators import validator_for
from referencing import Registry
from robotics_runtime_contracts import load_mapping

from scripts.bundle_schemas import RESOURCES, ROOT, Schema, read_schemas, registry_for, subschemas

SNAPSHOT = json.loads(
    gzip.decompress((Path(__file__).parent / "fixtures/baseline.json.gz").read_bytes())
)
BEFORE = {
    name: json.loads(raw)
    for name, raw in SNAPSHOT["resources"].items()
    if name.endswith(".schema.json")
}
AFTER = read_schemas(RESOURCES)


class Resolver(Protocol):
    def lookup(self, ref: str) -> Any: ...


def assertions(schema: Schema, schemas: dict[str, Schema]) -> Any:
    """Expand static refs with their resolver context; retain every assertion keyword.

    $defs and IDs address schemas; descriptive metadata is ignored.
    A resolved ref keeps its siblings in the same token, not in an allOf branch:
    annotation-dependent keywords observe their adjacent applicators. Cycles fail
    closed because this finite-tree comparison is limited to these schemas.
    """
    registry = registry_for(schemas)
    locations = {id(node) for document in schemas.values() for node in subschemas(document)}

    def visit(value: Any, resolver: Resolver, active: frozenset[int]) -> Any:
        if isinstance(value, list):
            return [visit(item, resolver, active) for item in value]
        if not isinstance(value, dict):
            return value
        if id(value) not in locations:
            return {key: visit(item, resolver, active) for key, item in value.items()}
        if id(value) in active:
            raise ValueError("Recursive schema needs a different equivalence proof")
        active = active | {id(value)}
        own = {
            key: visit(item, resolver, active)
            for key, item in value.items()
            if key
            not in {
                "$ref",
                "$defs",
                "$id",
                "$schema",
                "title",
                "description",
                "$comment",
                "examples",
            }
        }
        if "$ref" not in value:
            return own
        resolved = resolver.lookup(value["$ref"])
        target = visit(resolved.contents, resolved.resolver, active)
        # This token is not a JSON Schema: its $ref holds a schema, not a URI.
        # Keeping the reserved key avoids collisions with authored allOf trees.
        return {"$ref": target, **own} if own else target

    return visit(schema, registry.resolver(schema["$id"]), frozenset())


def comparison_key(schema: Schema, schemas: dict[str, Schema]) -> str:
    # Python container equality conflates True/1 and False/0. Compare JSON tokens
    # so constraint changes cannot hide behind that coercion. This is a test
    # representation, not artifact or canonical-statement serialization.
    return json.dumps(assertions(schema, schemas), sort_keys=True, allow_nan=False)


def test_resource_and_catalog_identities_are_unchanged() -> None:
    assert set(BEFORE) == set(AFTER)
    assert (RESOURCES / "catalog.v1.json").read_bytes() == SNAPSHOT["resources"][
        "catalog.v1.json"
    ].encode()
    assert {name: value["$id"] for name, value in BEFORE.items()} == {
        name: value["$id"] for name, value in AFTER.items()
    }


@pytest.mark.parametrize("name", sorted(BEFORE))
def test_every_resolved_schema_assertion_is_identical(name: str) -> None:
    assert comparison_key(BEFORE[name], BEFORE) == comparison_key(AFTER[name], AFTER)


def test_cores_use_named_conditionals_and_common_owns_named_primitives() -> None:
    for name, schema in AFTER.items():
        for node in subschemas(schema):
            assert "/allOf/" not in node.get("$ref", "")
        if name.endswith("-core.v1.schema.json"):
            assert all(item["$ref"].startswith("#/$defs/") for item in schema.get("allOf", []))
        if name != "common.v1.schema.json":
            for definition in schema.get("$defs", {}).values():
                assert definition.get("type") in (None, "object", "array")
                if definition.get("$ref", "").startswith("urn:robotics-runtime-contracts:build:"):
                    pytest.fail("Build-only reference escaped into a packaged resource")


def document_cases() -> Iterator[tuple[str, dict[str, Any]]]:
    directories = [
        ROOT / "packages/contracts/tests/fixtures",
        ROOT / "packages/contracts/consumer-examples",
        ROOT / "packages/harness/tests/fixtures",
    ]
    for directory in directories:
        for path in sorted(directory.rglob("*")):
            if path.suffix not in {".json", ".yaml", ".yml"}:
                continue
            try:
                value = load_mapping(path)
            except ValueError:
                continue  # Malformed serialization has no schema instance to compare.
            name = f"{value.get('schema_version')}.schema.json"
            if name in BEFORE:
                yield path.relative_to(ROOT).as_posix(), value


CASES = list(document_cases())


def validation_errors(value: Any, schema: Schema, registry: Registry[Any]) -> list[str]:
    validator = Draft202012Validator(
        schema, registry=registry, format_checker=Draft202012Validator.FORMAT_CHECKER
    )
    return sorted(
        json.dumps([list(error.absolute_path), error.validator, error.message], sort_keys=True)
        for error in validator.iter_errors(value)
    )


def test_fixture_comparison_is_not_empty_or_single_package() -> None:
    paths = [path for path, _ in CASES]
    assert len(paths) >= 50
    assert any(path.startswith("packages/contracts/consumer-examples/") for path in paths)
    assert any(path.startswith("packages/harness/tests/fixtures/") for path in paths)
    assert any("/invalid/" in path for path in paths)


@pytest.mark.parametrize("path,value", CASES, ids=[path for path, _ in CASES])
def test_fixture_validation_and_instance_diagnostics_are_unchanged(
    path: str, value: Schema
) -> None:
    name = f"{value['schema_version']}.schema.json"
    assert validation_errors(value, BEFORE[name], registry_for(BEFORE)) == validation_errors(
        value, AFTER[name], registry_for(AFTER)
    ), path


@pytest.mark.parametrize(
    "constraint,replacement",
    [
        ("type", "integer"),
        ("enum", ["short"]),
        ("pattern", "^a$"),
        ("minLength", 2),
        ("maxLength", 3),
        ("additionalProperties", False),
        ("required", ["extra"]),
        ("if", {"required": ["extra"]}),
    ],
)
def test_assertion_comparison_detects_changed_constraints(
    constraint: str, replacement: Any
) -> None:
    original = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:example",
        "type": "string",
    }
    changed = deepcopy(original)
    changed[constraint] = replacement
    assert comparison_key(original, {"schema": original}) != comparison_key(
        changed, {"schema": changed}
    )


@pytest.mark.parametrize("before,after", [(True, 1), (False, 0), (1, 1.0)])
def test_assertion_comparison_preserves_json_scalar_types(before: Any, after: Any) -> None:
    original: Schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:example",
        "const": {"nested": [before]},
    }
    changed = deepcopy(original)
    changed["const"]["nested"] = [after]
    assert original == changed  # Demonstrate the Python equality trap.
    assert comparison_key(original, {"schema": original}) != comparison_key(
        changed, {"schema": changed}
    )


def test_ref_siblings_are_not_dropped_and_literal_refs_are_not_resolved() -> None:
    schema: Schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:example",
        "$ref": "#/$defs/limited",
        "maxLength": 3,
        "$defs": {"limited": {"type": "string", "maxLength": 10}},
        "const": {"$ref": "this-is-instance-data"},
    }
    result = assertions(schema, {"schema": schema})
    assert result == {
        "$ref": {"type": "string", "maxLength": 10},
        "maxLength": 3,
        "const": {"$ref": "this-is-instance-data"},
    }


def test_recursive_ref_comparison_fails_closed() -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:example",
        "$ref": "#",
    }
    with pytest.raises(ValueError, match="Recursive schema"):
        assertions(schema, {"schema": schema})


def test_comparison_preserves_ref_sibling_annotation_scope() -> None:
    original: Schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:example",
        "$defs": {"properties": {"properties": {"x": {"type": "integer"}}}},
        "$ref": "#/$defs/properties",
        "unevaluatedProperties": False,
    }
    changed: Schema = {
        "$schema": original["$schema"],
        "$id": original["$id"],
        "allOf": [
            {"properties": {"x": {"type": "integer"}}},
            {"unevaluatedProperties": False},
        ],
    }
    assert Draft202012Validator(original).is_valid({"x": 1})
    assert not Draft202012Validator(changed).is_valid({"x": 1})
    assert comparison_key(original, {"schema": original}) != comparison_key(
        changed, {"schema": changed}
    )


def test_comparison_rejects_a_dialect_change_with_different_validation() -> None:
    original: Schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:example",
        "type": "object",
        "unevaluatedProperties": False,
    }
    changed = {**original, "$schema": "http://json-schema.org/draft-07/schema#"}
    assert not validator_for(original)(original).is_valid({"x": 1})
    assert validator_for(changed)(changed).is_valid({"x": 1})
    comparison_key(original, {"schema": original})
    with pytest.raises(ValueError, match="must declare Draft 2020-12"):
        comparison_key(changed, {"schema": changed})


def test_comparison_rejects_a_nested_dialect_in_unused_definitions() -> None:
    schema: Schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:example",
        "$defs": {"unused": {"$schema": "http://json-schema.org/draft-07/schema#"}},
    }
    with pytest.raises(ValueError, match=r"Nested \$schema"):
        comparison_key(schema, {"schema": schema})
