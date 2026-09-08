"""Assemble the core schema definitions and check their packaged bytes offline."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "packages/contracts"
SOURCES = PACKAGE / "schemas/src"
RESOURCES = PACKAGE / "src/robotics_runtime_contracts/schemas"
SOURCE_PREFIX = "urn:robotics-runtime-contracts:build:"
DIALECT = "https://json-schema.org/draft/2020-12/schema"
Schema = dict[str, Any]


def read_schemas(directory: Path) -> dict[str, Schema]:
    """Read schema objects without depending on the installed contracts package."""
    result: dict[str, Schema] = {}
    for path in sorted(directory.rglob("*.schema.json")):
        value = json.loads(path.read_bytes())
        if not isinstance(value, dict) or not isinstance(value.get("$id"), str):
            raise ValueError(f"Schema needs an explicit $id: {path}")
        result[path.relative_to(directory).as_posix()] = value
    if not result:
        raise ValueError(f"No schemas found in {directory}")
    return result


def registry_for(schemas: dict[str, Schema]) -> Registry[Any]:
    for schema in schemas.values():
        check_dialect(schema)
    resources = [(value["$id"], Resource.from_contents(value)) for value in schemas.values()]
    if len({uri for uri, _ in resources}) != len(resources):
        raise ValueError("Duplicate schema $id")
    return Registry().with_resources(resources)


def subschemas(schema: Schema) -> Iterator[Schema]:
    """Visit Draft 2020-12 schema locations without guessing nested dialects."""
    pending = [DRAFT202012.create_resource(schema)]
    while pending:
        resource = pending.pop()
        if isinstance(resource.contents, dict):
            yield resource.contents
        pending.extend(
            DRAFT202012.create_resource(child)
            for child in DRAFT202012.subresources_of(resource.contents)
        )


def check_dialect(schema: Schema) -> None:
    """Require the one supported root dialect; nested declarations are unsupported."""
    if schema.get("$schema") != DIALECT:
        raise ValueError(f"Schema must declare Draft 2020-12: {schema.get('$id')}")
    for node in subschemas(schema):
        if node is not schema and "$schema" in node:
            raise ValueError(
                f"Nested $schema is outside the core source format: {schema.get('$id')}"
            )


def schema_locations(registry: Registry[Any]) -> set[int]:
    """Identify schema objects by location, never by equality with instance data."""
    return {id(node) for resource in registry.values() for node in subschemas(resource.contents)}


def check_target(target: Any, locations: set[int], reference: str) -> None:
    """Reject objects outside the dialect's schema locations, including chained refs."""
    Draft202012Validator.check_schema(target)
    if isinstance(target, dict) and id(target) not in locations:
        raise ValueError(f"Reference target is not a known schema location: {reference}")


def check_references(schemas: dict[str, Schema]) -> None:
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    registry = registry_for(schemas)
    locations = schema_locations(registry)
    for name, schema in schemas.items():
        resolver = registry.resolver(schema["$id"])
        for node in subschemas(schema):
            # This assembler's sources use absolute resource IDs and static refs.
            # Reject new scoping features instead of silently rebasing them.
            if node is not schema and "$id" in node:
                raise ValueError(f"Nested $id is outside the core source format: {name}")
            if "$dynamicRef" in node or "$dynamicAnchor" in node:
                raise ValueError(f"Dynamic references are outside the core source format: {name}")
            if "$ref" in node:
                target = resolver.lookup(node["$ref"]).contents
                check_target(target, locations, node["$ref"])


def assemble(schema: Schema, registry: Registry[Any]) -> Schema:
    """Materialize explicit definition imports; referencing owns all URI/pointer lookup.

    Fragment bodies refer to final resource IDs. Only direct $defs entries may
    import build resources. Keeping ordinary references intact avoids flattening
    sibling constraints or accidentally changing JSON Schema evaluation scope.
    """
    result = deepcopy(schema)
    locations = schema_locations(registry)
    for name, definition in result.get("$defs", {}).items():
        if not isinstance(definition, dict):
            raise ValueError(f"Core definitions must be schema objects: {name}")
        reference = definition.get("$ref", "")
        if reference.startswith(SOURCE_PREFIX):
            if set(definition) != {"$ref"}:
                raise ValueError(f"Definition import must contain only $ref: {name}")
            resolved = registry.resolver(schema["$id"]).lookup(reference).contents
            check_target(resolved, locations, reference)
            if not isinstance(resolved, dict):
                raise ValueError(f"Definition import must resolve to a schema object: {name}")
            result["$defs"][name] = deepcopy(resolved)
    prefix = schema["$id"] + "#"
    for node in subschemas(result):
        reference = node.get("$ref", "")
        if reference.startswith(SOURCE_PREFIX):
            raise ValueError(f"Unassembled build reference: {reference}")
        if reference.startswith(prefix):
            node["$ref"] = "#" + reference.removeprefix(prefix)
    return result


def render(schema: Schema) -> bytes:
    """Preserve authored key order; emit the historical two-space UTF-8/LF format."""
    return (json.dumps(schema, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def bundle(sources: Path = SOURCES, resources: Path = RESOURCES) -> dict[str, bytes]:
    inputs = read_schemas(sources)
    registry = registry_for(inputs)
    outputs = {
        name: assemble(schema, registry)
        for name, schema in inputs.items()
        if "/" not in name and name.endswith("-core.v1.schema.json")
    }
    packaged = read_schemas(resources)
    expected = {name for name in packaged if name.endswith("-core.v1.schema.json")}
    if not outputs or set(outputs) != expected:
        raise ValueError(f"Core source inventory differs: expected {sorted(expected)}")
    check_references(packaged | outputs)
    return {name: render(schema) for name, schema in outputs.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail on drift without writing files")
    parser.add_argument("--sources", type=Path, default=SOURCES)
    parser.add_argument("--resources", type=Path, default=RESOURCES)
    parser.add_argument("--output", type=Path, help="Alternate generation directory")
    args = parser.parse_args(argv)
    try:
        outputs = bundle(args.sources, args.resources)
        destination = args.output or args.resources
        changed = [
            name
            for name, content in outputs.items()
            if not (destination / name).is_file() or (destination / name).read_bytes() != content
        ]
        if args.check:
            for name in changed:
                print(f"Schema differs: {name}", file=sys.stderr)
        else:
            destination.mkdir(parents=True, exist_ok=True)
            for name in changed:
                (destination / name).write_bytes(outputs[name])
        action = "stale" if args.check else "written"
        print(f"Core schemas: {len(outputs)} checked, {len(changed)} {action}")
        return int(args.check and bool(changed))
    except (OSError, ValueError, Unresolvable, SchemaError) as error:
        print(f"Schema bundling failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
