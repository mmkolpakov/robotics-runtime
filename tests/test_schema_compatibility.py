"""D10 mutation witnesses and the real released Git/schema/semantic baseline."""

from __future__ import annotations

import json
import shutil
import subprocess
from copy import deepcopy
from hashlib import sha1, sha256
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing.exceptions import Unresolvable

from scripts import check_schema_compatibility as gate
from scripts.bundle_schemas import DIALECT, ROOT, Schema, read_schemas
from scripts.schema_compatibility import history, semantic
from scripts.schema_compatibility.probe import fixture_document
from scripts.schema_compatibility.structure import (
    Context,
    Expansion,
    ReviewRequired,
    check_structure,
    compare,
)


def schema(body: Schema) -> Schema:
    return {"$schema": DIALECT, "$id": "urn:example:document", **body}


def comparison(before: Schema, after: Schema, *, input_document: bool = False) -> None:
    left = Expansion({"document": before}).root(before)
    right = Expansion({"document": after}).root(after)
    compare(left, right, Context("document", input_document))


def catalog(role: str = "acceptance_result") -> Schema:
    return {"contract_set": "v1", "roles": {role: "document.v1"}, "internal_resources": []}


@pytest.fixture(scope="module")
def published(tmp_path_factory: pytest.TempPathFactory) -> Path:
    release = history.baseline(ROOT)
    return history.extract(ROOT, release, tmp_path_factory.mktemp("published25"))


def test_actual_published_git_baseline_and_semantics(published: Path) -> None:
    release = history.baseline(ROOT)
    assert (
        release.commit
        == history.git(ROOT, "rev-parse", f"refs/tags/{release.tag}^{{commit}}").decode().strip()
    )
    resources = published / "src/robotics_runtime_contracts/schemas"
    tree_path = f"{release.prefix}src/robotics_runtime_contracts/schemas/"
    records = history.git(ROOT, "ls-tree", "-r", release.commit, tree_path).decode().splitlines()
    blobs = {line.split("\t")[1].removeprefix(tree_path): line.split()[2] for line in records}
    assert blobs.keys() == {path.name for path in resources.iterdir()}
    for path in resources.iterdir():
        raw = path.read_bytes()
        assert sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() == blobs[path.name]
    result = gate.check(ROOT)
    assert release.commit in result
    assert "retained schemas" in result
    if release.tag == history.LEGACY_TAG:
        assert "29 retained schemas; 16 semantic cases" in result


@pytest.mark.parametrize(
    "old,new,instance",
    [
        ({"type": "object"}, {"type": "object", "required": ["x"]}, {}),
        (
            {"properties": {"x": {"type": "integer"}}, "additionalProperties": False},
            {"properties": {}, "additionalProperties": False},
            {"x": 1},
        ),
        ({"type": "number"}, {"type": "integer"}, 1.5),
        ({"const": True}, {"const": 1}, True),
        ({"enum": [True, "a"]}, {"enum": [1, "a"]}, True),
        ({"enum": ["a", "b"]}, {"enum": ["a"]}, "b"),
        ({"pattern": "^[ab]$"}, {"pattern": "^a$"}, "b"),
        ({"minimum": 0}, {"minimum": 1}, 0),
        ({"maximum": 10}, {"maximum": 9}, 10),
        ({"minLength": 1}, {"minLength": 2}, "a"),
        ({"maxItems": 2}, {"maxItems": 1}, [1, 2]),
        ({"additionalProperties": True}, {"additionalProperties": False}, {"x": 1}),
        ({}, {"if": {"type": "object"}, "then": {"required": ["x"]}}, {}),
        (
            {"properties": {}, "additionalProperties": True},
            {"properties": {"x": {"type": "string"}}, "additionalProperties": True},
            {"x": 1},
        ),
    ],
    ids=[
        "required",
        "removed-property",
        "type",
        "const-bool-int",
        "enum-bool-int",
        "enum-narrowing",
        "pattern",
        "minimum",
        "maximum",
        "minLength",
        "maxItems",
        "additionalProperties",
        "conditional",
        "optional-in-open-object",
    ],
)
def test_old_valid_witness_is_rejected_by_mutation(old: Schema, new: Schema, instance: Any) -> None:
    before, after = schema(old), schema(new)
    assert Draft202012Validator(before).is_valid(instance)
    assert not Draft202012Validator(after).is_valid(instance)
    with pytest.raises(ReviewRequired):
        comparison(before, after, input_document=True)


def test_reference_sibling_evaluated_annotation_regression() -> None:
    before = schema(
        {
            "$defs": {"fields": {"properties": {"x": {"type": "integer"}}}},
            "$ref": "#/$defs/fields",
            "unevaluatedProperties": False,
        }
    )
    after = schema(
        {
            "allOf": [
                {"properties": {"x": {"type": "integer"}}},
                {"unevaluatedProperties": False},
            ]
        }
    )
    assert Draft202012Validator(before).is_valid({"x": 1})
    assert not Draft202012Validator(after).is_valid({"x": 1})
    with pytest.raises(ReviewRequired, match="evaluation scope"):
        comparison(before, after)


@pytest.mark.parametrize("keyword", ["oneOf", "not", "if", "contains"])
def test_input_enum_addition_is_not_allowed_in_nonmonotone_context(keyword: str) -> None:
    bodies: dict[str, tuple[Schema, Any]] = {
        "oneOf": ({"oneOf": [{"enum": ["a"]}, {"enum": ["b"]}]}, "b"),
        "not": ({"not": {"enum": ["a"]}}, "b"),
        "if": ({"if": {"enum": ["a"]}, "then": False}, "b"),
        "contains": ({"contains": {"enum": ["a"]}, "maxContains": 1}, ["a", "b"]),
    }
    body, witness = bodies[keyword]
    before, after = schema(body), schema(deepcopy(body))
    target = after[keyword][0] if keyword == "oneOf" else after[keyword]
    target["enum"].append("b")
    assert Draft202012Validator(before).is_valid(witness)
    assert not Draft202012Validator(after).is_valid(witness)
    with pytest.raises(ReviewRequired):
        comparison(before, after, input_document=True)


def test_additive_optional_property_in_closed_object_and_input_enum() -> None:
    before = schema(
        {
            "type": "object",
            "properties": {"kind": {"enum": ["a"]}},
            "additionalProperties": False,
            "required": ["kind"],
        }
    )
    after = deepcopy(before)
    after["properties"]["hint"] = {"type": "string"}
    after["properties"]["kind"]["enum"].append("b")
    comparison(before, after, input_document=True)
    for document in ({"kind": "a"}, {"kind": "a", "hint": "help"}, {"kind": "b"}):
        assert Draft202012Validator(after).is_valid(document)
    with pytest.raises(ReviewRequired, match="enum"):
        comparison(before, after)  # Output-enum additions violate D10.


def test_annotations_only_at_schema_locations_and_typed_literal_data() -> None:
    before = schema({"const": {"title": True, "examples": [1]}})
    after = {**before, "title": "New title", "description": "New docs", "examples": [False]}
    comparison(before, after)
    after = deepcopy(after)
    after["const"]["title"] = 1
    with pytest.raises(ReviewRequired, match="const"):
        comparison(before, after)


@pytest.mark.parametrize("keyword", ["default", "$comment", "minimum"])
def test_changes_outside_d10_allowlist_need_review_even_if_widening(keyword: str) -> None:
    before = schema({keyword: "old" if keyword == "$comment" else 1})
    after = schema({keyword: "new" if keyword == "$comment" else 0})
    with pytest.raises(ReviewRequired):
        comparison(before, after, input_document=True)


@pytest.mark.parametrize(
    "body",
    [
        {"$defs": {"unused": {"futureKeyword": True}}},
        {"$defs": {"cycle": {"$ref": "#/$defs/cycle"}}},
        {"$ref": "https://unavailable.example/schema"},
        {"$defs": {"unused": {"$schema": "http://json-schema.org/draft-07/schema#"}}},
        {"$defs": {"unused": {"$id": "urn:nested"}}},
        {"$dynamicRef": "#"},
        {"$anchor": "root"},
        {"$ref": "#/type", "type": "string"},
        {"$ref": "#/const", "const": {"$ref": "#/examples/0"}, "examples": ["object"]},
        {"$ref": "#/const", "const": {"$id": "urn:hidden"}},
        {"$ref": "#/const", "const": {"$dynamicRef": "#"}},
        {"$schema": "http://json-schema.org/draft-07/schema#"},
    ],
    ids=[
        "unknown",
        "cycle",
        "remote",
        "nested-dialect",
        "nested-id",
        "dynamic",
        "anchor",
        "string-target",
        "chained-instance-target",
        "hidden-id",
        "hidden-dynamic",
        "dialect",
    ],
)
def test_unsupported_domain_fails_closed(body: Schema) -> None:
    with pytest.raises((ValueError, SchemaError, Unresolvable)):
        comparison(schema({}), schema(body))


def test_reference_aliases_may_change_without_normalizing_primitive_constraints() -> None:
    before = schema({"$defs": {"old": {"type": "string", "minLength": 1}}, "$ref": "#/$defs/old"})
    after = schema({"$defs": {"new": {"type": "string", "minLength": 1}}, "$ref": "#/$defs/new"})
    comparison(before, after)
    after["$defs"]["new"]["minLength"] = 2
    with pytest.raises(ReviewRequired):
        comparison(before, after)


def test_new_roles_are_allowed_but_existing_roles_and_ids_are_frozen() -> None:
    before = {"document.v1.schema.json": schema({"type": "string"})}
    after = {**before, "another.v1.schema.json": schema({"$id": "urn:new", "type": "integer"})}
    new_catalog = catalog()
    new_catalog["roles"]["another"] = "another.v1"
    assert check_structure(before, after, catalog(), new_catalog) == 1
    renamed = deepcopy(new_catalog)
    renamed["roles"]["renamed"] = renamed["roles"].pop("acceptance_result")
    with pytest.raises(ReviewRequired, match="role"):
        check_structure(before, after, catalog(), renamed)
    changed = deepcopy(before)
    changed["document.v1.schema.json"]["$id"] = "urn:changed"
    with pytest.raises(ReviewRequired, match=r"\$id"):
        check_structure(before, changed, catalog(), catalog())


def test_shared_input_and_output_enum_cannot_evade_output_policy() -> None:
    shared = schema({"$id": "urn:common", "$defs": {"kind": {"enum": ["a"]}}})
    before = {
        "document.v1.schema.json": schema({"$ref": "urn:common#/$defs/kind"}),
        "output.v1.schema.json": schema({"$id": "urn:output", "$ref": "urn:common#/$defs/kind"}),
        "common.v1.schema.json": shared,
    }
    roles = catalog("acceptance_scenario")
    roles["roles"]["acceptance_result"] = "output.v1"
    roles["internal_resources"] = ["common.v1"]
    after = deepcopy(before)
    after["common.v1.schema.json"]["$defs"]["kind"]["enum"].append("b")
    with pytest.raises(ReviewRequired, match="output.v1.schema.json/enum"):
        check_structure(before, after, roles, roles)


def test_semantic_only_mutation_is_caught_with_unchanged_schemas(
    published: Path, tmp_path: Path
) -> None:
    candidate = tmp_path / "candidate"
    shutil.copytree(ROOT / "packages/contracts/src", candidate / "src")
    path = candidate / "src/robotics_runtime_contracts/semantics.py"
    source = path.read_text(encoding="utf-8")
    declaration = "def validate_semantics(schema_name: str, document: Mapping[str, Any]) -> None:\n"
    assert source.count(declaration) == 1
    mutation = (
        '    if schema_name == "campaign-summary.v1":\n        raise ValueError("mutation25")\n'
    )
    path.write_text(source.replace(declaration, declaration + mutation), encoding="utf-8")
    assert read_schemas(candidate / "src/robotics_runtime_contracts/schemas") == read_schemas(
        ROOT / "packages/contracts/src/robotics_runtime_contracts/schemas"
    )
    with pytest.raises(ReviewRequired, match="legacy-shortfall.json.*mutation25"):
        semantic.check_semantics(published, candidate)


def test_semantic_probe_uses_selected_source_despite_pythonpath(
    published: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "packages/contracts/src"))
    response = semantic.probe(published / "src", {"documents": semantic.regressions()})
    assert Path(response["origin"]).is_relative_to(published)
    assert response["documents"] == semantic.regressions()


def test_published_alias_fixture_is_validated_as_values_without_rewriting_bytes(
    published: Path, tmp_path: Path
) -> None:
    # Keep this regression even after a newer release removes fixture aliases.
    frozen_bytes = history.git(
        ROOT, "show", f"{history.LEGACY_COMMIT}:tests/fixtures/model-artifact/valid/onnx.yaml"
    )
    original = tmp_path / "onnx.yaml"
    original.write_bytes(frozen_bytes)
    assert b"*id001" in frozen_bytes
    response = semantic.probe(published / "src", {"files": {"onnx": str(original)}})
    document = response["documents"]["onnx"]
    assert document == fixture_document(original)
    assert original.read_bytes() == frozen_bytes
    # The current public file loader still rejects aliases: compatibility of
    # document values does not weaken its input syntax or resource limits.
    from robotics_runtime_contracts import load_mapping
    from robotics_runtime_contracts.serialization import DocumentParseError

    with pytest.raises(DocumentParseError, match="aliases"):
        load_mapping(original)
    candidate = ROOT / "packages/contracts/src"
    assert semantic.probe(candidate, {"documents": response["documents"]})["documents"] == {
        "onnx": document
    }


def test_fixture_decoder_preserves_yaml12_json_values(tmp_path: Path) -> None:
    path = tmp_path / "values.yaml"
    path.write_text(
        'source: &values [yes, 010, true, 1.25, null, "2026-09-09"]\ncopy: *values\n',
        encoding="utf-8",
    )
    assert fixture_document(path) == {
        "source": ["yes", 10, True, 1.25, None, "2026-09-09"],
        "copy": ["yes", 10, True, 1.25, None, "2026-09-09"],
    }


@pytest.mark.parametrize("value", ["1_000", "0b10", "2026-09-09T00:00:00Z"])
def test_fixture_decoder_keeps_core_strings_accepted_by_public_writer(
    published: Path, tmp_path: Path, value: str
) -> None:
    from robotics_runtime_contracts import load_mapping
    from robotics_runtime_contracts.serialization import dumps_yaml

    original = published / "tests/fixtures/model-artifact/valid/onnx.yaml"
    document = fixture_document(original)
    document["build"]["version"] = value
    path = tmp_path / "core-string.yaml"
    path.write_text(dumps_yaml(document), encoding="utf-8")
    assert load_mapping(path) == document
    assert fixture_document(path) == document
    response = semantic.probe(published / "src", {"files": {"core-string": str(path)}})
    assert response["documents"]["core-string"]["build"]["version"] == value


def test_merge_key_is_a_literal_core_string(tmp_path: Path) -> None:
    path = tmp_path / "literal.yaml"
    path.write_text("build: {<<: {tool: onnx}, tool: different}\n", encoding="utf-8")
    assert fixture_document(path) == {"build": {"<<": {"tool": "onnx"}, "tool": "different"}}


@pytest.mark.parametrize(
    "suffix,source",
    [
        ("yaml", "value: 1\nvalue: 2\n"),
        ("yaml", "value: &cycle [*cycle]\n"),
        ("yaml", "value: .inf\n"),
        ("yaml", "value: !!timestamp 2026-09-09T00:00:00Z\n"),
        ("yaml", "value: {1: coerced}\n"),
        ("yaml", "value: !!set {a: null}\n"),
        ("yaml", "build: {<<: {tool: onnx}, tool: 17, tool: onnx}\n"),
        ("yaml", "build: {!!merge <<: {tool: onnx}, tool: 17, tool: onnx}\n"),
        ("yaml", "value: !!int 1_000\n"),
        ("yaml", "%YAML 1.1\n---\nvalue: 010\n"),
        ("json", '{"value": 1, "value": 2}'),
        ("json", '{"value": NaN}'),
        ("json", '{"value": 1,}'),
    ],
)
def test_fixture_decoder_rejects_ambiguous_or_non_json_values(
    tmp_path: Path, suffix: str, source: str
) -> None:
    path = tmp_path / f"invalid.{suffix}"
    path.write_text(source, encoding="utf-8")
    with pytest.raises(ValueError, match=f"invalid.{suffix}: fixture decoding failed"):
        fixture_document(path)


def test_missing_or_corrupt_semantic_regressions_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(semantic, "FIXTURES", tmp_path)
    (tmp_path / "provenance.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ReviewRequired, match="empty"):
        semantic.regressions()
    (tmp_path / "provenance.json").write_text('{"x.json":{"sha256":"bad"}}', encoding="utf-8")
    (tmp_path / "x.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ReviewRequired, match="bytes changed"):
        semantic.regressions()


def init_repo(root: Path) -> None:
    history.git(root, "init", "--quiet")
    history.git(
        root,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "--quiet",
        "--allow-empty",
        "-m",
        "fixture",
    )


def test_missing_and_moved_legacy_tag_fail_closed(tmp_path: Path) -> None:
    init_repo(tmp_path)
    with pytest.raises(ReviewRequired, match="fetch"):
        history.baseline(tmp_path)
    history.git(tmp_path, "tag", history.LEGACY_TAG)
    with pytest.raises(ReviewRequired, match="moved"):
        history.baseline(tmp_path)


def test_stable_release_selection_uses_numeric_versions_and_checks_metadata(tmp_path: Path) -> None:
    init_repo(tmp_path)
    path = tmp_path / "packages/contracts/pyproject.toml"
    path.parent.mkdir(parents=True)
    path.write_text('[project]\nversion="0.17.0"\n', encoding="utf-8")
    history.git(tmp_path, "add", ".")
    history.git(
        tmp_path,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "release fixture",
    )
    history.git(tmp_path, "tag", "contracts-v0.17.0")
    history.git(tmp_path, "tag", "contracts-v0.9.0")
    history.git(tmp_path, "tag", "contracts-v0.18.0rc1")
    assert history.baseline(tmp_path).tag == "contracts-v0.17.0"
    history.git(tmp_path, "tag", "contracts-v0.18.0")
    with pytest.raises(ReviewRequired, match="version mismatch"):
        history.baseline(tmp_path)


def test_shallow_history_is_not_silently_accepted(tmp_path: Path) -> None:
    source, clone = tmp_path / "source", tmp_path / "clone"
    source.mkdir()
    init_repo(source)
    subprocess.run(
        ["git", "clone", "--quiet", "--depth=1", source.as_uri(), str(clone)], check=True
    )
    with pytest.raises(ReviewRequired, match="Shallow history"):
        history.baseline(clone)


def test_actual_main_fails_closed_for_history_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    init_repo(tmp_path)
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    assert gate.main() == 1
    assert "review_required" in capsys.readouterr().err


def test_actual_main_rejects_break_even_with_updated_candidate_digests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    candidate = tmp_path / "packages/contracts"
    shutil.copytree(ROOT / "packages/contracts/src", candidate / "src")
    resources = candidate / "src/robotics_runtime_contracts/schemas"
    name = "acceptance-result.v1.schema.json"
    changed = json.loads((resources / name).read_bytes())
    changed["required"].append("mutation25")
    (resources / name).write_text(json.dumps(changed), encoding="utf-8")
    digests = {path.name: sha256(path.read_bytes()).hexdigest() for path in resources.iterdir()}
    (candidate / "docs").mkdir()
    (candidate / "docs/schema-digests.json").write_text(json.dumps(digests), encoding="utf-8")
    release = history.baseline(ROOT)
    monkeypatch.setattr(gate, "baseline", lambda _root: release)
    monkeypatch.setattr(gate, "extract", lambda _root, tag, dest: history.extract(ROOT, tag, dest))
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    assert gate.main() == 1
    diagnostic = capsys.readouterr().err
    assert "review_required" in diagnostic
    assert "required" in diagnostic


def test_optional_property_in_empty_closed_object() -> None:
    before = schema({"type": "object", "additionalProperties": False})
    after = {**before, "properties": {"x": {"type": "integer"}}}
    comparison(before, after)
    assert Draft202012Validator(before).is_valid({})
    assert Draft202012Validator(after).is_valid({"x": 1})


def test_pattern_property_prevents_unsafe_optional_addition() -> None:
    before = schema(
        {
            "properties": {},
            "patternProperties": {"^x": {"type": "integer"}},
            "additionalProperties": False,
        }
    )
    after = {**before, "properties": {"x": {"type": "string"}}}
    assert Draft202012Validator(before).is_valid({"x": 1})
    assert not Draft202012Validator(after).is_valid({"x": 1})
    with pytest.raises(ReviewRequired, match="object context"):
        comparison(before, after)


@pytest.mark.parametrize("value", [True, False])
def test_boolean_reference_targets_and_escaped_pointers(value: bool) -> None:
    before = schema({"$defs": {"a/b~c": value}, "$ref": "#/$defs/a~1b~0c"})
    after = schema({"$defs": {"renamed": value}, "$ref": "#/$defs/renamed"})
    comparison(before, after)
    assert Expansion({"document": before}).root(before) is value
