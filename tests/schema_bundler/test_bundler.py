"""Generation and historical byte reproduction, independent of the working tree history."""

import gzip
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing.exceptions import Unresolvable

from scripts import bundle_schemas as bundler

FIXTURES = Path(__file__).parent / "fixtures"


def test_historical_sources_reproduce_every_core_byte(tmp_path: Path) -> None:
    archive = (FIXTURES / "baseline.json.gz").read_bytes()
    manifest = json.loads((FIXTURES / "baseline-manifest.json").read_bytes())
    assert sha256(archive).hexdigest() == manifest["archive_sha256"]
    snapshot = json.loads(gzip.decompress(archive))
    assert snapshot["commit"] == manifest["source_commit"]
    for group in ("sources", "resources"):
        digests = manifest["source_sha256" if group == "sources" else "resource_sha256"]
        assert set(snapshot[group]) == set(digests)
        for name, raw in snapshot[group].items():
            content = raw.encode()
            assert sha256(content).hexdigest() == digests[name]
            path = tmp_path / group / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    outputs = bundler.bundle(tmp_path / "sources", tmp_path / "resources")
    assert len(outputs) == 4
    assert sum(map(len, outputs.values())) == 84269
    for name, content in outputs.items():
        assert content == snapshot["resources"][name].encode()


def test_checked_in_cores_are_deterministic_and_current(tmp_path: Path) -> None:
    first = bundler.bundle()
    assert first == bundler.bundle()
    for name, content in first.items():
        assert content == (bundler.RESOURCES / name).read_bytes()
        assert b"\r" not in content
    args = ["--output", str(tmp_path)]
    assert bundler.main([*args, "--check"]) == 1
    assert list(tmp_path.iterdir()) == []
    assert bundler.main(args) == 0
    stamps = {path.name: path.stat().st_mtime_ns for path in tmp_path.iterdir()}
    assert bundler.main(args) == 0
    assert stamps == {path.name: path.stat().st_mtime_ns for path in tmp_path.iterdir()}
    assert bundler.main([*args, "--check"]) == 0
    path = tmp_path / next(iter(first))
    path.write_bytes(path.read_bytes() + b"\n")
    assert bundler.main([*args, "--check"]) == 1
    assert path.read_bytes().endswith(b"\n\n")


def test_empty_source_inventory_fails(tmp_path: Path) -> None:
    assert bundler.main(["--sources", str(tmp_path), "--check"]) == 1


def test_missing_one_core_source_fails(tmp_path: Path) -> None:
    name, value = next(iter(bundler.read_schemas(bundler.SOURCES).items()))
    (tmp_path / name).write_bytes(bundler.render(value))
    # Supply all fragments so the failure specifically concerns the core inventory.
    for fragment, schema in bundler.read_schemas(bundler.SOURCES).items():
        if fragment.startswith("fragments/"):
            path = tmp_path / fragment
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(bundler.render(schema))
    with pytest.raises(ValueError, match="inventory differs"):
        bundler.bundle(tmp_path)


def test_reference_lookup_uses_escaped_pointers_and_preserves_siblings() -> None:
    target: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": bundler.SOURCE_PREFIX + "fragments",
        "$defs": {"a/b~c": {"$ref": "urn:example:core#/$defs/value", "maxLength": 5}},
    }
    core: dict[str, Any] = {
        "$schema": target["$schema"],
        "$id": "urn:example:core",
        "$defs": {
            "value": {"type": "string"},
            "imported": {"$ref": target["$id"] + "#/$defs/a~1b~0c"},
        },
        "const": {"$ref": "urn:example:core#/$defs/literal-not-a-schema"},
    }
    originals = deepcopy((core, target))
    output = bundler.assemble(core, bundler.registry_for({"core": core, "target": target}))
    assert output["$defs"]["imported"] == {"$ref": "#/$defs/value", "maxLength": 5}
    assert output["const"] == core["const"]
    assert (core, target) == originals
    bundler.check_references({"core": output})


def test_import_siblings_are_rejected_instead_of_overwritten() -> None:
    core = next(iter(bundler.read_schemas(bundler.SOURCES).values()))
    definition = next(iter(core["$defs"].values()))
    definition["maxLength"] = 1
    with pytest.raises(ValueError, match="only .ref"):
        bundler.assemble(core, bundler.registry_for(bundler.read_schemas(bundler.SOURCES)))


def test_unknown_references_fail_without_network_retrieval() -> None:
    core = next(iter(bundler.read_schemas(bundler.RESOURCES).values()))
    core["$ref"] = "https://invalid.example/not-registered"
    with pytest.raises(Unresolvable):
        bundler.check_references({"core": core})


def test_duplicate_ids_fail() -> None:
    core = next(iter(bundler.read_schemas(bundler.RESOURCES).values()))
    with pytest.raises(ValueError, match="Duplicate"):
        bundler.registry_for({"first": core, "second": deepcopy(core)})


@pytest.mark.parametrize("extra", [{"$id": "urn:nested"}, {"$dynamicRef": "#node"}])
def test_unsupported_reference_scope_fails_explicitly(extra: dict[str, str]) -> None:
    core = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:example:core",
        "$defs": {"unsupported": extra},
    }
    with pytest.raises(ValueError, match="outside the core source format"):
        bundler.check_references({"core": core})


@pytest.mark.parametrize("target", ["object", None, 1, 1.0, ["integer"], {"type": 5}])
def test_existing_reference_target_must_itself_be_a_schema(target: Any) -> None:
    schema = {
        "$schema": bundler.DIALECT,
        "$id": "urn:example:core",
        "const": target,
        "$ref": "#/const",
    }
    # A valid outer schema does not establish that the resolved target is valid.
    Draft202012Validator.check_schema(schema)
    with pytest.raises(SchemaError):
        bundler.check_references({"core": schema})


@pytest.mark.parametrize("target", [True, False, {"type": "object"}])
def test_boolean_and_object_reference_targets_are_supported(target: Any) -> None:
    schema = {
        "$schema": bundler.DIALECT,
        "$id": "urn:example:core",
        "$defs": {"value": target},
        "$ref": "#/$defs/value",
    }
    bundler.check_references({"core": schema})
    assert Draft202012Validator(schema).is_valid({}) is (target is not False)


@pytest.mark.parametrize(
    "dialect", ["http://json-schema.org/draft-07/schema#", "urn:unsupported:dialect"]
)
@pytest.mark.parametrize("nested", [False, True])
def test_a_reference_cannot_introduce_an_unsupported_target_dialect(
    dialect: str, nested: bool
) -> None:
    target: dict[str, Any] = {"$schema": dialect, "type": "object"}
    if nested:
        target = {"$defs": {"nested": target}}
    schema = {
        "$schema": bundler.DIALECT,
        "$id": "urn:example:core",
        "const": target,
        "$ref": "#/const",
    }
    # Const remains instance data and cannot become an object-schema target.
    bundler.registry_for({"core": schema})
    with pytest.raises(ValueError, match="not a known schema location"):
        bundler.check_references({"core": schema})


@pytest.mark.parametrize("reference", ["#/type", "#/const"])
def test_invalid_target_fails_even_with_matching_output_bytes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], reference: str
) -> None:
    schema = {
        "$schema": bundler.DIALECT,
        "$id": "urn:example:core",
        "type": "object",
        "const": {"type": 5},
        "$defs": {"unused": {"$ref": reference}},
    }
    content = bundler.render(schema)
    paths = [tmp_path / group / "example-core.v1.schema.json" for group in ("src", "out")]
    for path in paths:
        path.parent.mkdir()
        path.write_bytes(content)
    args = ["--sources", str(paths[0].parent), "--resources", str(paths[1].parent)]
    assert bundler.main([*args, "--check"]) == 1
    assert bundler.main(args) == 1
    assert "Schema bundling failed:" in capsys.readouterr().err
    assert all(path.read_bytes() == content for path in paths)


@pytest.mark.parametrize(
    "target",
    [
        pytest.param({"$ref": "#/examples/0"}, id="chained-string-target"),
        pytest.param({"$id": "urn:example:hidden"}, id="hidden-id"),
        pytest.param({"$dynamicRef": "#hidden"}, id="hidden-dynamic-ref"),
        pytest.param({"$dynamicAnchor": "hidden"}, id="hidden-dynamic-anchor"),
        pytest.param({"type": "object"}, id="equal-but-distinct-schema"),
        pytest.param({}, id="empty-instance-object"),
    ],
)
def test_refs_into_instance_objects_fail_check_with_matching_bytes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], target: dict[str, Any]
) -> None:
    schema = {
        "$schema": bundler.DIALECT,
        "$id": "urn:example:core",
        "$defs": {"same": {"type": "object"}, "empty": {}},
        "const": target,
        "examples": ["object"],
        "$ref": "#/const",
    }
    # Both the root and the first target pass the metaschema. The target is
    # instance data, even when it is equal to a real definition elsewhere.
    Draft202012Validator.check_schema(schema)
    Draft202012Validator.check_schema(target)
    content = bundler.render(schema)
    paths = [tmp_path / group / "example-core.v1.schema.json" for group in ("src", "out")]
    for path in paths:
        path.parent.mkdir()
        path.write_bytes(content)
    args = ["--sources", str(paths[0].parent), "--resources", str(paths[1].parent), "--check"]
    assert bundler.main(args) == 1
    assert "not a known schema location" in capsys.readouterr().err
    assert all(path.read_bytes() == content for path in paths)


def test_build_imports_cannot_materialize_instance_objects(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fragment = {
        "$schema": bundler.DIALECT,
        "$id": bundler.SOURCE_PREFIX + "fragment",
        "const": {"type": "string"},
    }
    source = {
        "$schema": bundler.DIALECT,
        "$id": "urn:example:core",
        "$defs": {"imported": {"$ref": f"{fragment['$id']}#/const"}},
    }
    output = {**source, "$defs": {"imported": fragment["const"]}}
    for group, schema in (("src", source), ("out", output)):
        directory = tmp_path / group
        directory.mkdir()
        (directory / "example-core.v1.schema.json").write_bytes(bundler.render(schema))
    fragments = tmp_path / "src/fragments"
    fragments.mkdir()
    (fragments / "fragment.schema.json").write_bytes(bundler.render(fragment))
    args = ["--sources", str(tmp_path / "src"), "--resources", str(tmp_path / "out"), "--check"]
    assert bundler.main(args) == 1
    assert "not a known schema location" in capsys.readouterr().err
    assert (tmp_path / "out/example-core.v1.schema.json").read_bytes() == bundler.render(output)


@pytest.mark.parametrize("target", [True, False])
def test_boolean_targets_do_not_need_object_schema_locations(tmp_path: Path, target: bool) -> None:
    schema = {
        "$schema": bundler.DIALECT,
        "$id": "urn:example:core",
        "const": target,
        "$ref": "#/const",
    }
    content = bundler.render(schema)
    for group in ("src", "out"):
        directory = tmp_path / group
        directory.mkdir()
        (directory / "example-core.v1.schema.json").write_bytes(content)
    args = ["--sources", str(tmp_path / "src"), "--resources", str(tmp_path / "out"), "--check"]
    assert bundler.main(args) == 0


@pytest.mark.parametrize(
    "dialect", [None, "http://json-schema.org/draft-07/schema#", "urn:unsupported:dialect"]
)
def test_registry_requires_explicit_supported_root_dialect(dialect: str | None) -> None:
    schema: dict[str, Any] = {"$id": "urn:example:core"}
    if dialect is not None:
        schema["$schema"] = dialect
    with pytest.raises(ValueError, match="must declare Draft 2020-12"):
        bundler.registry_for({"core": schema})


@pytest.mark.parametrize(
    "dialect",
    [bundler.DIALECT, "http://json-schema.org/draft-07/schema#", "urn:unsupported:dialect"],
)
def test_registry_rejects_nested_dialect_declarations(dialect: str) -> None:
    schema = {
        "$schema": bundler.DIALECT,
        "$id": "urn:example:core",
        "$defs": {"unused": {"allOf": [{"$schema": dialect}]}},
    }
    with pytest.raises(ValueError, match=r"Nested \$schema"):
        bundler.registry_for({"core": schema})


def test_literal_dialect_declarations_are_instance_data() -> None:
    schema = {
        "$schema": bundler.DIALECT,
        "$id": "urn:example:core",
        "const": {"$schema": "urn:literal:dialect", "$ref": "urn:literal:reference"},
        "examples": [{"$schema": "urn:literal:dialect"}],
    }
    bundler.check_references({"core": schema})
    assert Draft202012Validator(schema).is_valid(schema["const"])


@pytest.mark.parametrize("nested", [False, True])
def test_unused_source_fragment_dialect_is_checked_before_assembly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], nested: bool
) -> None:
    core = {"$schema": bundler.DIALECT, "$id": "urn:example:core"}
    for group in ("src", "out"):
        directory = tmp_path / group
        directory.mkdir()
        (directory / "example-core.v1.schema.json").write_bytes(bundler.render(core))
    fragment: dict[str, Any] = {
        "$schema": bundler.DIALECT,
        "$id": bundler.SOURCE_PREFIX + "unused",
    }
    if nested:
        fragment["$defs"] = {"unused": {"$schema": "urn:unsupported:dialect"}}
    else:
        fragment["$schema"] = "http://json-schema.org/draft-07/schema#"
    fragments = tmp_path / "src/fragments"
    fragments.mkdir()
    (fragments / "unused.schema.json").write_bytes(bundler.render(fragment))
    assert (
        bundler.main(
            ["--sources", str(tmp_path / "src"), "--resources", str(tmp_path / "out"), "--check"]
        )
        == 1
    )
    assert "Schema bundling failed:" in capsys.readouterr().err


@pytest.mark.parametrize(
    "instance,valid",
    [
        ({"kind": "a", "payload": 1}, True),
        ({"kind": "b", "payload": 1}, False),
        ({"kind": "a", "payload": "bad"}, False),
        ({"kind": "a", "payload": 1, "extra": 0}, False),
        ({"kind": "a"}, True),
        ({"kind": "b"}, True),
    ],
)
def test_named_conditional_import_preserves_evaluated_properties(
    instance: dict[str, Any], valid: bool
) -> None:
    rule = {
        "if": {"properties": {"kind": {"const": "a"}}, "required": ["kind"]},
        "then": {"properties": {"payload": {"type": "integer"}}},
    }
    original: dict[str, Any] = {
        "$schema": bundler.DIALECT,
        "$id": "urn:example:core",
        "type": "object",
        "properties": {"kind": {"type": "string"}},
        "allOf": [rule],
        "unevaluatedProperties": False,
    }
    fragment = {
        "$schema": bundler.DIALECT,
        "$id": bundler.SOURCE_PREFIX + "fragment",
        "$defs": {"payloadWhenA": rule},
    }
    source = deepcopy(original)
    source["allOf"] = [{"$ref": "#/$defs/payloadWhenA"}]
    source["$defs"] = {
        "payloadWhenA": {"$ref": f"{fragment['$id']}#/$defs/payloadWhenA"},
    }
    assembled = bundler.assemble(
        source, bundler.registry_for({"core": source, "fragment": fragment})
    )
    bundler.check_references({"core": assembled})
    assert Draft202012Validator(original).is_valid(instance) is valid
    assert Draft202012Validator(assembled).is_valid(instance) is valid
