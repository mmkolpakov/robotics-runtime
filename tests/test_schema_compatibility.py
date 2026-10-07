"""D10 mutation witnesses and the real released Git/schema/semantic baseline."""

from __future__ import annotations

import json
import shutil
import subprocess
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha1, sha256
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing.exceptions import Unresolvable

from scripts import check_schema_compatibility as gate
from scripts.bundle_schemas import DIALECT, ROOT, Schema, read_schemas
from scripts.release.plan import create_plan, project
from scripts.schema_compatibility import history, semantic, snapshot
from scripts.schema_compatibility.dataset_migration import DatasetMigration
from scripts.schema_compatibility.probe import execute
from scripts.schema_compatibility.structure import (
    Context,
    Expansion,
    ReviewRequired,
    check_structure,
    compare,
    token,
)

type DatasetCandidate = tuple[Path, Path, DatasetMigration]
FROZEN_DATASET_RELEASE = history.Baseline(
    "contracts-v0.18.3", "ecfb0446fddad70e8ab1094694dddacfeb496d53", "packages/contracts/"
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
    return history.extract(ROOT, FROZEN_DATASET_RELEASE, tmp_path_factory.mktemp("published25"))


def test_actual_published_git_baseline_and_semantics(tmp_path: Path) -> None:
    release = history.baseline(ROOT)
    published = history.extract(ROOT, release, tmp_path / "latest-published")
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
        assert "29 retained schemas; 67 semantic cases" in result


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


def discriminated_union() -> Schema:
    return schema(
        {
            "oneOf": [
                {
                    "type": "object",
                    "required": ["kind"],
                    "additionalProperties": False,
                    "properties": {"kind": {"const": kind}},
                }
                for kind in ("none", "inference")
            ]
        }
    )


def test_optional_property_in_disjoint_oneof_preserves_old_instances() -> None:
    before = discriminated_union()
    after = deepcopy(before)
    after["oneOf"][0]["properties"]["description"] = {"type": "string"}
    comparison(before, after, input_document=True)
    for document in ({"kind": "none"}, {"kind": "inference"}):
        assert Draft202012Validator(before).is_valid(document)
        assert Draft202012Validator(after).is_valid(document)
    assert Draft202012Validator(after).is_valid({"kind": "none", "description": "robot"})


@pytest.mark.parametrize(
    "mutation", ["optional-tag", "duplicate-tag", "numeric-tag", "missing-type"]
)
def test_oneof_without_proven_string_discriminator_stays_frozen(mutation: str) -> None:
    before = discriminated_union()
    first, second = before["oneOf"]
    if mutation == "optional-tag":
        first["required"] = []
    elif mutation == "duplicate-tag":
        second["properties"]["kind"]["const"] = "none"
    elif mutation == "numeric-tag":
        first["properties"]["kind"]["const"] = 1
        second["properties"]["kind"]["const"] = 1.0
    else:
        del first["type"]
    after = deepcopy(before)
    after["oneOf"][0]["properties"]["description"] = {"type": "string"}
    with pytest.raises(ReviewRequired, match="frozen"):
        comparison(before, after, input_document=True)


def test_discriminated_union_cannot_hide_new_required_property_or_changed_tag() -> None:
    before = discriminated_union()
    after = deepcopy(before)
    after["oneOf"][0]["properties"]["description"] = {"type": "string"}
    after["oneOf"][0]["required"].append("description")
    assert not Draft202012Validator(after).is_valid({"kind": "none"})
    with pytest.raises(ReviewRequired):
        comparison(before, after, input_document=True)
    after = deepcopy(before)
    after["oneOf"][0]["properties"]["kind"]["const"] = "different"
    with pytest.raises(ReviewRequired, match="const"):
        comparison(before, after, input_document=True)


def test_discriminated_union_inside_not_remains_frozen() -> None:
    before = schema({"not": discriminated_union()})
    del before["not"]["$id"]
    del before["not"]["$schema"]
    after = deepcopy(before)
    after["not"]["oneOf"][0]["properties"]["description"] = {"type": "string"}
    witness = {"kind": "none", "description": "robot"}
    assert Draft202012Validator(before).is_valid(witness)
    assert not Draft202012Validator(after).is_valid(witness)
    with pytest.raises(ReviewRequired, match="frozen"):
        comparison(before, after, input_document=True)


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


def test_semantic_gate_replays_published_qualification_documents(
    published: Path, tmp_path: Path
) -> None:
    names = semantic.published_documents(published)
    assert "packages/contracts/tests/fixtures/qualification/transport/clock-relation.json" in names
    assert any(name.startswith("packages/contracts/consumer-examples/") for name in names)
    assert any("/invalid/" in name for name in names)
    assert any(name.startswith("packages/harness/tests/fixtures/") for name in names)
    candidate = tmp_path / "candidate"
    shutil.copytree(ROOT / "packages/contracts/src", candidate / "src")
    path = candidate / "src/robotics_runtime_contracts/semantics.py"
    source = path.read_text(encoding="utf-8")
    declaration = "def _validate_clock_relation(document: Mapping[str, Any]) -> None:\n"
    assert source.count(declaration) == 1
    mutation = '    raise ValueError("clock-relation-mutation")\n'
    path.write_text(source.replace(declaration, declaration + mutation), encoding="utf-8")
    with pytest.raises(ReviewRequired, match="clock-relation.json.*clock-relation-mutation"):
        semantic.check_semantics(published, candidate)


def test_semantic_probe_uses_selected_source_despite_pythonpath(
    published: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "packages/contracts/src"))
    documents = semantic.regressions()
    request = {
        "documents": documents,
        "cases": [{"id": name, "operation": "document", "document": name} for name in documents],
    }
    response = execute(published / "src", request)
    assert Path(response["origin"]).is_relative_to(published)
    assert response["documents"] == documents
    assert all(value == {"status": "accepted"} for value in response["outcomes"].values())


def test_published_alias_values_are_frozen_without_rewriting_raw_bytes(tmp_path: Path) -> None:
    frozen = semantic.regressions()["regression/legacy-alias.json"]
    assert frozen["model_id"] == "org.example.detector.onnx"
    assert frozen["source"]["inputs"][0]["shape"] == ["batch", 3, 640, 640]
    assert frozen["target"]["inputs"] == frozen["source"]["inputs"]
    raw = history.git(
        ROOT, "show", f"{history.LEGACY_COMMIT}:tests/fixtures/model-artifact/valid/onnx.yaml"
    )
    original = tmp_path / "onnx.yaml"
    original.write_bytes(raw)
    from robotics_runtime_contracts import DocumentParseError, load_mapping

    with pytest.raises(DocumentParseError, match="aliases"):
        load_mapping(original)
    assert original.read_bytes() == raw
    release = history.Baseline(history.LEGACY_TAG, history.LEGACY_COMMIT, "")
    old = history.extract(ROOT, release, tmp_path / "historical")
    request = {
        "documents": {"alias": frozen},
        "cases": [{"id": "alias", "operation": "document", "document": "alias"}],
    }
    expected = {"alias": {"status": "accepted"}}
    semantic.compare_request(old / "src", request, expected)
    semantic.compare_request(ROOT / "packages/contracts/src", request, expected)


def test_corpus_classifies_all_four_roots_and_preserves_contexts() -> None:
    inventory, documents, contexts = snapshot.read_corpus()
    assert len(inventory["entries"]) == 139
    assert len({entry["path"] for entry in inventory["entries"]}) == 139
    assert inventory["roots"] == [
        "packages/contracts/tests/fixtures",
        "packages/contracts/consumer-examples",
        "packages/harness/tests/fixtures",
        "packages/harness/tests/live/fixtures",
    ]
    fixtures = [entry for entry in inventory["entries"] if "document" in entry]
    assert len(fixtures) == 92
    assert sum(entry["outcome"]["status"] == "rejected" for entry in fixtures) == 12
    assert (
        len(
            [
                entry
                for entry in inventory["entries"]
                if entry["classification"] == "composition_descriptor_context"
            ]
        )
        == 3
    )
    ids = {case["id"] for case in contexts["cases"]}
    assert len(ids) == 288
    assert len([name for name in ids if name.startswith("role/")]) == 26
    assert len([name for name in ids if name.startswith("qualification/contradiction/")]) == 16
    assert {
        "workload/missing",
        "workload/mismatch",
        "workload/match",
        "workload/unpinned-absent",
        "workload/unpinned-present",
    } <= ids
    for entry in fixtures:
        assert entry["document"] in documents
        assert entry["outcome"] == contexts["expected"][entry["document"]]


def test_negative_fixture_cannot_silently_become_accepted(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    shutil.copytree(ROOT / "packages/contracts/src", candidate / "src")
    path = candidate / "src/robotics_runtime_contracts/__init__.py"
    source = path.read_text()
    needle = "    ensure_finite_numbers(document)\n"
    assert source.count(needle) == 1
    source = source.replace(
        needle,
        '    if document.get("schema_version") == "dataset-manifest.v1":\n        return\n'
        + needle,
    )
    path.write_text(source)
    _, documents, contexts = snapshot.read_corpus()
    identifier = "fixture/packages/contracts/tests/fixtures/dataset/invalid/s3-without-version.yaml"
    case = next(case for case in contexts["cases"] if case["id"] == identifier)
    request = {"documents": {case["document"]: documents[case["document"]]}, "cases": [case]}
    with pytest.raises(ReviewRequired, match="s3-without-version"):
        semantic.compare_request(
            candidate / "src", request, {identifier: contexts["expected"][identifier]}
        )


def test_workload_link_refusal_cannot_be_lost_with_unchanged_schemas(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    shutil.copytree(ROOT / "packages/contracts/src", candidate / "src")
    path = candidate / "src/robotics_runtime_contracts/workloads.py"
    source = path.read_text()
    needle = '    expected = scenario.get("workload", {}).get("robot_description_sha256")\n'
    assert source.count(needle) == 1
    path.write_text(source.replace(needle, "    return\n" + needle))
    _, documents, contexts = snapshot.read_corpus()
    case = next(case for case in contexts["cases"] if case["id"] == "workload/mismatch")
    request = {
        "documents": {name: documents[name] for name in [case["scenario"], case["runtime"]]},
        "cases": [case],
    }
    with pytest.raises(ReviewRequired, match="workload/mismatch"):
        semantic.compare_request(
            candidate / "src", request, {case["id"]: contexts["expected"][case["id"]]}
        )


def test_unexpected_probe_error_is_not_an_expected_rejection() -> None:
    request = {"documents": {}, "cases": [{"id": "unknown", "operation": "unknown"}]}
    with pytest.raises(ReviewRequired, match="Unknown corpus operation"):
        execute(ROOT / "packages/contracts/src", request)


def test_raw_syntax_is_a_separate_fixed_public_loader_and_dumper_corpus(published: Path) -> None:
    request = snapshot.syntax_request()
    assert len(request["cases"]) == 20
    expected = {case["id"]: case["expected"] for case in request["cases"]}
    assert expected["syntax/14"]["value"] == {"source": ["yes", 10, True, 1.25, None, "2026-09-09"]}
    assert expected["syntax/16"]["status"] == "rejected"
    assert expected["syntax/16"]["error_id"] == "input.yaml_alias"
    semantic.compare_request(published / "src", request, expected)
    semantic.compare_request(ROOT / "packages/contracts/src", request, expected)


@pytest.mark.parametrize("value", ["1_000", "0b10", "2026-09-09T00:00:00Z"])
def test_public_writer_keeps_core_strings(value: str) -> None:
    from robotics_runtime_contracts import loads_mapping
    from robotics_runtime_contracts.serialization import dumps_yaml

    document = {"version": value, "time_ns": 9007199254740993, "boolean": True, "float": 1.0}
    assert loads_mapping(dumps_yaml(document)) == document
    assert isinstance(loads_mapping(dumps_yaml(document))["float"], float)


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


def test_frozen_corpus_identity_fails_before_public_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shutil.copytree(snapshot.FIXTURES, tmp_path / "fixtures")
    fixture_root = tmp_path / "fixtures"
    path = fixture_root / "contracts-v0.18.2/documents.json"
    path.write_bytes(path.read_bytes() + b" ")
    monkeypatch.setattr(snapshot, "FIXTURES", fixture_root)
    with pytest.raises(ReviewRequired, match="Frozen corpus bytes changed"):
        snapshot.read_corpus()


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


def test_retained_raw_fixture_change_fails_before_semantic_probe(
    published: Path, tmp_path: Path
) -> None:
    root = tmp_path / "baseline"
    shutil.copytree(published.parents[1], root)
    raw = root / "packages/contracts/tests/fixtures/dataset/valid/camera-mcap.yaml"
    raw.write_bytes(raw.read_bytes() + b"\n")
    with pytest.raises(ReviewRequired, match="Frozen fixture bytes changed.*camera-mcap"):
        snapshot.capture(root, published / "src")


def test_historical_corpus_keeps_all_inventory_bytes_and_json_values(
    tmp_path: Path, dataset_transition_candidate: DatasetCandidate
) -> None:
    release = history.Baseline(history.LEGACY_TAG, history.LEGACY_COMMIT, "")
    published = history.extract(ROOT, release, tmp_path / "historical")
    captured = snapshot.capture_legacy(published, published / "src")
    corpus = snapshot.legacy_corpus()
    assert len(corpus["entries"]) == 105
    assert len(captured["request"]["cases"]) == 67
    _, candidate, witness = dataset_transition_candidate
    semantic.compare_request(
        candidate / "src",
        captured["request"],
        captured["expected"],
        dataset_transition=witness,
    )


def test_release_corpus_retains_raw_identity_and_source_plan(tmp_path: Path) -> None:
    root = tmp_path / "source"
    history.git(ROOT, "clone", "--quiet", "--no-hardlinks", str(ROOT), str(root))
    # Local search indexes are not producer, package or corpus inputs.
    (root / ".codegraph").mkdir()
    (root / ".codegraph/index").write_bytes(b"local index")
    plan = asdict(
        create_plan(
            root, f"contracts-v{project(root, 'contracts')['version']}", event="workflow_dispatch"
        )
    )
    assert (
        plan["tree"] == history.git(root, "rev-parse", "HEAD:packages/contracts").decode().strip()
    )
    assert plan["tree"] != history.git(root, "rev-parse", "HEAD^{tree}").decode().strip()
    output = tmp_path / "release-corpus"
    snapshot.write_release(root, plan, output)
    provenance = json.loads((output / "semantic-provenance.json").read_bytes())
    for name in ("candidate", "commit", "tree", "contracts_commit"):
        assert provenance[name] == plan[name]
    assert (
        provenance["repository_tree"]
        == history.git(root, "rev-parse", "HEAD^{tree}").decode().strip()
    )
    for name, identity in provenance["files"].items():
        raw = (output / name).read_bytes()
        assert len(raw) == identity["size_bytes"]
        assert sha256(raw).hexdigest() == identity["sha256"]
    inventory = json.loads((output / "semantic-inventory.json").read_bytes())
    assert inventory["commit"] == plan["commit"]
    assert inventory["tag"] == plan["candidate"]
    raw_source = inventory["raw_fixture_source"]
    assert raw_source == {
        "tag": "contracts-v0.18.3",
        "commit": "ecfb0446fddad70e8ab1094694dddacfeb496d53",
    }
    for entry in inventory["entries"]:
        raw = history.git(root, "show", f"{raw_source['commit']}:{entry['path']}")
        assert entry["raw_sha256"] == sha256(raw).hexdigest()
        assert entry["size_bytes"] == len(raw)
    _, documents, _ = snapshot.read_corpus()
    historical = snapshot.historical_snapshot()
    expected_documents = {**documents, **historical["request"]["documents"]}
    assert token(json.loads((output / "semantic-documents.json").read_bytes())) == token(
        expected_documents
    )
    contexts = json.loads((output / "semantic-contexts.json").read_bytes())
    assert len(contexts["cases"]) == 355
    assert len(contexts["expected"]) == 355
    assert len({case["id"] for case in contexts["cases"]}) == 355
    emitted = {
        "documents": json.loads((output / "semantic-documents.json").read_bytes()),
        "cases": contexts["cases"],
    }
    semantic.compare_request(root / "packages/contracts/src", emitted, contexts["expected"])
    assert len(inventory["historical"]["entries"]) == 105
    with pytest.raises(FileExistsError):
        snapshot.write_release(root, plan, output)

    producer = root / "scripts/schema_compatibility/probe.py"
    original = producer.read_bytes()
    producer.write_bytes(original + b"# temporary fixture edit")
    with pytest.raises(ReviewRequired, match="Release corpus source must be clean"):
        snapshot.write_release(root, plan, tmp_path / "dirty-corpus")
    assert not (tmp_path / "dirty-corpus").exists()
    producer.write_bytes(original)
    (root / "json.py").write_bytes(b"# unreviewed importable input")
    with pytest.raises(ReviewRequired, match="Release corpus source must be clean"):
        snapshot.write_release(root, plan, tmp_path / "untracked-corpus")
    assert not (tmp_path / "untracked-corpus").exists()


@pytest.mark.parametrize("changed", ["commit", "repository_tree", "other_package_tree"])
def test_release_corpus_rejects_a_mismatched_source_plan(tmp_path: Path, changed: str) -> None:
    root = tmp_path / "source"
    history.git(ROOT, "clone", "--quiet", "--no-hardlinks", str(ROOT), str(root))
    plan = asdict(
        create_plan(
            root, f"contracts-v{project(root, 'contracts')['version']}", event="workflow_dispatch"
        )
    )
    if changed == "commit":
        plan["commit"] = "0" * 40
    else:
        ref = "HEAD^{tree}" if changed == "repository_tree" else "HEAD:packages/harness"
        plan["tree"] = history.git(root, "rev-parse", ref).decode().strip()
    with pytest.raises(ReviewRequired, match="source differs from the validated plan"):
        snapshot.write_release(root, plan, tmp_path / "mismatched")
    assert not (tmp_path / "mismatched").exists()


@pytest.fixture
def dataset_transition_candidate(published: Path, tmp_path: Path) -> DatasetCandidate:
    import tomllib

    from scripts.schema_compatibility.dataset_migration import dataset_migration

    root = tmp_path / "dataset-train"
    history.git(ROOT, "clone", "--quiet", "--no-hardlinks", str(ROOT), str(root))
    candidate = root / "packages/contracts"
    shutil.rmtree(candidate / "src")
    shutil.copytree(ROOT / "packages/contracts/src", candidate / "src")
    raw = (ROOT / "packages/contracts/pyproject.toml").read_text()
    current = tomllib.loads(raw)["project"]["version"]
    (candidate / "pyproject.toml").write_text(
        raw.replace(f'version = "{current}"', 'version = "0.19.0"', 1)
    )
    harness = root / "packages/harness"
    harness.mkdir(parents=True, exist_ok=True)
    (harness / "pyproject.toml").write_text('[project]\nversion = "0.20.0"\n')
    witness = dataset_migration(root, FROZEN_DATASET_RELEASE, published, candidate)
    assert witness is not None
    return root, candidate, witness


def dataset_structure(
    published: Path, candidate: Path, witness: DatasetMigration | None = None
) -> int:
    old = published / "src/robotics_runtime_contracts/schemas"
    new = candidate / "src/robotics_runtime_contracts/schemas"
    return check_structure(
        read_schemas(old),
        read_schemas(new),
        json.loads((old / "catalog.v1.json").read_bytes()),
        json.loads((new / "catalog.v1.json").read_bytes()),
        dataset_transition=witness,
    )


def test_exact_dataset_migration_requires_the_explicit_raw_witness(
    published: Path, dataset_transition_candidate: DatasetCandidate
) -> None:
    from dataclasses import replace

    _, candidate, witness = dataset_transition_candidate
    with pytest.raises(ReviewRequired, match="role"):
        dataset_structure(published, candidate)
    count = dataset_structure(published, candidate, witness)
    assert count == len(read_schemas(published / "src/robotics_runtime_contracts/schemas")) - 1
    with pytest.raises(ReviewRequired, match="SHA256"):
        dataset_structure(published, candidate, replace(witness, after_raw=b"changed"))


@pytest.mark.parametrize("mutation", ["another-role", "another-id", "dataset-body"])
def test_dataset_witness_cannot_bypass_other_role_or_resource_changes(
    published: Path, dataset_transition_candidate: DatasetCandidate, mutation: str
) -> None:
    _, candidate, witness = dataset_transition_candidate
    resources = candidate / "src/robotics_runtime_contracts/schemas"
    if mutation == "another-role":
        path = resources / "catalog.v1.json"
        body = json.loads(path.read_bytes())
        body["roles"]["acceptance_result"] = body["roles"]["acceptance_run"]
    elif mutation == "another-id":
        path = resources / "acceptance-result.v1.schema.json"
        body = json.loads(path.read_bytes())
        body["$id"] = "urn:changed"
    else:
        path = resources / "dataset-manifest.v2.schema.json"
        body = json.loads(path.read_bytes())
        body["description"] = "unreviewed dataset schema bytes"
    path.write_text(json.dumps(body))
    with pytest.raises(ReviewRequired):
        dataset_structure(published, candidate, witness)


def test_dataset_migration_refuses_wrong_package_train(
    published: Path, dataset_transition_candidate: DatasetCandidate
) -> None:
    from scripts.schema_compatibility.dataset_migration import dataset_migration

    root, candidate, _ = dataset_transition_candidate
    (root / "packages/harness/pyproject.toml").write_text('[project]\nversion = "0.19.2"\n')
    with pytest.raises(ReviewRequired, match="train"):
        dataset_migration(root, FROZEN_DATASET_RELEASE, published, candidate)


def test_dataset_migration_replays_all_native_cases_without_changing_historical_facts(
    published: Path, dataset_transition_candidate: DatasetCandidate
) -> None:
    _, candidate, witness = dataset_transition_candidate
    before = {path: path.read_bytes() for path in semantic.FIXTURES.rglob("*") if path.is_file()}
    assert semantic.check_semantics(published, candidate, dataset_transition=witness) == 375
    assert all(path.read_bytes() == raw for path, raw in before.items())


def test_dataset_migration_still_catches_unrelated_semantic_mutation(
    published: Path, dataset_transition_candidate: DatasetCandidate
) -> None:
    _, candidate, witness = dataset_transition_candidate
    path = candidate / "src/robotics_runtime_contracts/semantics.py"
    source = path.read_text()
    declaration = "def validate_semantics(schema_name: str, document: Mapping[str, Any]) -> None:\n"
    assert source.count(declaration) == 1
    mutation = (
        '    if schema_name == "campaign-summary.v1":\n'
        '        raise ValueError("unrelated-mutation")\n'
    )
    path.write_text(source.replace(declaration, declaration + mutation))
    with pytest.raises(ReviewRequired, match="unrelated-mutation"):
        semantic.check_semantics(published, candidate, dataset_transition=witness)


def test_dataset_refusal_hashes_do_not_bless_another_rejection(
    published: Path, dataset_transition_candidate: DatasetCandidate, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, candidate, witness = dataset_transition_candidate
    captured = snapshot.capture(published.parents[1], published / "src")
    response = execute(candidate / "src", captured["request"])
    name = next(iter(witness.row["semantic"]["published"]["refusals"]))
    response["outcomes"][name]["message"] = "unrelated failure"
    monkeypatch.setattr(semantic, "probe", lambda *_args: response)
    with pytest.raises(ReviewRequired, match="clean refusal changed"):
        semantic.compare_request(
            candidate / "src", captured["request"], captured["expected"], dataset_transition=witness
        )


def test_dataset_migration_missing_or_bad_row_fails_closed(
    published: Path,
    dataset_transition_candidate: DatasetCandidate,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.schema_compatibility import dataset_migration as migration

    root, candidate, _ = dataset_transition_candidate
    missing = tmp_path / "missing/dataset_migration.py"
    monkeypatch.setattr(migration, "__file__", str(missing))
    with pytest.raises(FileNotFoundError):
        migration.dataset_migration(root, FROZEN_DATASET_RELEASE, published, candidate)
    missing.parent.mkdir()
    row = json.loads((ROOT / "scripts/schema_compatibility/dataset-v2-migration.json").read_bytes())
    row["role"] = "acceptance_result"
    missing.with_name("dataset-v2-migration.json").write_text(json.dumps(row))
    with pytest.raises(ReviewRequired, match="Unsupported dataset migration"):
        migration.dataset_migration(root, FROZEN_DATASET_RELEASE, published, candidate)


def test_dataset_refusal_labels_cannot_disagree_with_the_pinned_native_outcome(
    published: Path, dataset_transition_candidate: DatasetCandidate
) -> None:
    from dataclasses import replace

    _, candidate, witness = dataset_transition_candidate
    captured = snapshot.capture(published.parents[1], published / "src")
    row = deepcopy(witness.row)
    name = next(iter(row["semantic"]["published"]["refusals"]))
    row["semantic"]["published"]["refusals"][name]["refusal"]["message"] = "misleading label"
    changed = replace(witness, row=row)
    with pytest.raises(ReviewRequired, match="clean refusal changed"):
        semantic.compare_request(
            candidate / "src", captured["request"], captured["expected"], dataset_transition=changed
        )


def test_dataset_release_snapshot_keeps_old_facts_and_new_refusals_separate(tmp_path: Path) -> None:
    root = tmp_path / "dataset-source"
    history.git(ROOT, "clone", "--quiet", "--no-hardlinks", "--no-tags", str(ROOT), str(root))
    history.git(
        root,
        "fetch",
        "--quiet",
        "--no-tags",
        str(ROOT),
        "refs/tags/contracts-v0.18.3:refs/tags/contracts-v0.18.3",
    )
    for key in ("contracts", "harness"):
        source = ROOT / f"packages/{key}/src"
        target = root / f"packages/{key}/src"
        shutil.rmtree(target)
        shutil.copytree(source, target)
        shutil.copyfile(
            ROOT / f"packages/{key}/pyproject.toml", root / f"packages/{key}/pyproject.toml"
        )
    fixtures = root / "packages/contracts/tests/fixtures"
    shutil.rmtree(fixtures)
    shutil.copytree(ROOT / "packages/contracts/tests/fixtures", fixtures)
    history.git(root, "add", "packages")
    history.git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "commit",
        "--no-gpg-sign",
        "-m",
        "Record canonical dataset fixtures",
        "--allow-empty",
    )
    plan = asdict(create_plan(root, "contracts-v0.19.0", event="workflow_dispatch"))
    output = tmp_path / "dataset-release"
    snapshot.write_release(root, plan, output)
    inventory = json.loads((output / "semantic-inventory.json").read_bytes())
    assert inventory["raw_fixture_source"] == {
        "tag": "contracts-v0.18.3",
        "commit": "ecfb0446fddad70e8ab1094694dddacfeb496d53",
    }
    original = json.loads((output / "semantic-old-tool-contexts.json").read_bytes())
    frozen = snapshot.legacy_corpus()
    assert original["historical"]["expected"] == snapshot.historical_snapshot()["expected"]
    assert original["published"]["expected"]["role/dataset_manifest"]["status"] == "accepted"
    current = json.loads((output / "semantic-contexts.json").read_bytes())
    assert current["expected"]["role/dataset_manifest"]["status"] == "rejected"
    for entry in inventory["entries"]:
        if "document" in entry:
            assert entry["outcome"] == current["expected"][entry["document"]]
    dataset = "legacy/tests/fixtures/dataset/valid/camera-mcap.yaml"
    assert frozen["expected"][dataset]["status"] == "accepted"
    assert current["expected"]["historical/" + dataset]["error_id"] == "schema.unknown"
    assert original["historical"]["expected"]["historical/" + dataset]["status"] == "accepted"

    # Creating the contracts tag must not make the subsequent train snapshot
    # reinterpret old witnesses or bypass v2-to-v2 structural checks.
    history.git(
        root,
        "fetch",
        "--quiet",
        "--no-tags",
        str(ROOT),
        "refs/tags/contracts-v0.19.0:refs/tags/contracts-v0.19.0",
    )
    later = tmp_path / "after-contracts-tag"
    snapshot.write_release(root, plan, later)
    assert (later / "semantic-old-tool-contexts.json").read_bytes() == (
        output / "semantic-old-tool-contexts.json"
    ).read_bytes()
    later_inventory = json.loads((later / "semantic-inventory.json").read_bytes())
    later_contexts = json.loads((later / "semantic-contexts.json").read_bytes())
    for entry in later_inventory["entries"]:
        if "document" in entry:
            assert entry["outcome"] == later_contexts["expected"][entry["document"]]
    from scripts.schema_compatibility.dataset_migration import dataset_migration

    release = history.baseline(root)
    published = history.extract(root, release, tmp_path / "v2-published")
    witness = dataset_migration(root, release, published, root / "packages/contracts")
    assert witness is not None
    assert dataset_structure(published, root / "packages/contracts", witness) == len(
        read_schemas(published / "src/robotics_runtime_contracts/schemas")
    )
    assert (
        semantic.check_semantics(published, root / "packages/contracts", dataset_transition=witness)
        == 375
    )


def test_published_v2_keeps_harness_patch_releases_independent(
    tmp_path: Path, dataset_transition_candidate: DatasetCandidate
) -> None:
    from scripts.schema_compatibility.dataset_migration import dataset_migration

    root, candidate, _ = dataset_transition_candidate
    release = history.baseline(ROOT)
    published_v2 = history.extract(ROOT, release, tmp_path / "published-v2")
    (root / "packages/harness/pyproject.toml").write_text('[project]\nversion = "0.20.1"\n')
    wrong = history.Baseline(release.tag, "0" * 40, release.prefix)
    with pytest.raises(ReviewRequired, match="published baseline differs"):
        dataset_migration(root, wrong, published_v2, candidate)
    witness = dataset_migration(root, release, published_v2, candidate)
    assert witness is not None
    assert dataset_structure(published_v2, candidate, witness) == len(
        read_schemas(published_v2 / "src/robotics_runtime_contracts/schemas")
    )
    assert semantic.check_semantics(published_v2, candidate, dataset_transition=witness) == 375

    schema_path = (
        candidate / "src/robotics_runtime_contracts/schemas/dataset-manifest.v2.schema.json"
    )
    schema_path.write_bytes(schema_path.read_bytes() + b" ")
    with pytest.raises(ReviewRequired, match="SHA256"):
        dataset_migration(root, release, published_v2, candidate)
