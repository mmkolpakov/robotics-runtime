"""Generation and historical byte reproduction, independent of the working tree history."""

import gzip
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
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
