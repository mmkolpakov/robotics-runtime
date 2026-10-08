"""Capture reviewed fixture inventory and JSON requests using the public loader."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from scripts.schema_compatibility import history
from scripts.schema_compatibility.probe import execute
from scripts.schema_compatibility.structure import ReviewRequired, token

FIXTURES = Path(__file__).resolve().parents[2] / "tests/schema_compatibility/fixtures"


def read_corpus() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    provenance = json.loads((FIXTURES / "corpus-provenance.json").read_bytes())
    if not provenance["files"]:
        raise ReviewRequired("Frozen corpus provenance is empty")
    for name, record in provenance["files"].items():
        raw = (FIXTURES / name).read_bytes()
        if len(raw) != record["size_bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
            raise ReviewRequired(f"Frozen corpus bytes changed: {name}")
    base = FIXTURES / provenance["tag"]
    inventory = json.loads((base / "inventory.json").read_bytes())
    documents = json.loads((base / "documents.json").read_bytes())
    contexts = json.loads((base / "contexts.json").read_bytes())
    for name, digest in contexts["document_sha256"].items():
        if hashlib.sha256(token(documents[name]).encode()).hexdigest() != digest:
            raise ReviewRequired(f"Frozen JSON value changed: {name}")
    if inventory["tag"] != provenance["tag"] or inventory["commit"] != provenance["commit"]:
        raise ReviewRequired("Frozen inventory and provenance disagree")
    if documents.keys() != contexts["document_sha256"].keys():
        raise ReviewRequired("Frozen JSON value inventory differs")
    identifiers = [case["id"] for case in contexts["cases"]]
    if len(set(identifiers)) != len(identifiers) or set(identifiers) != set(contexts["expected"]):
        raise ReviewRequired("Frozen case and expected-outcome inventories differ")
    return inventory, documents, contexts


def retained_inventory(root: Path, inventory: dict[str, Any]) -> None:
    """Classify every input; keep original evidence and fixture bytes exact."""
    entries = inventory["entries"]
    actual = {
        path.relative_to(root).as_posix()
        for name in inventory["roots"]
        for path in (root / name).rglob("*")
        if path.is_file()
    }
    if actual != {entry["path"] for entry in entries}:
        raise ReviewRequired("Published fixture inventory changed; review explicit classifications")
    for entry in entries:
        path = root / entry["path"]
        if path.is_symlink():
            raise ReviewRequired(f"Fixture is a symlink: {entry['path']}")
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        # Documentation has no semantic or artifact binding in this corpus.
        # Record its current source bytes; every retained asset stays exact.
        if entry["classification"] != "documentation" and (
            digest != entry["raw_sha256"] or len(raw) != entry["size_bytes"]
        ):
            raise ReviewRequired(f"Frozen fixture bytes changed: {entry['path']}")
        entry["raw_sha256"], entry["size_bytes"] = digest, len(raw)


def capture(root: Path, source: Path) -> dict[str, Any]:
    """Replay reviewed JSON values; never decode semantic YAML in either probe."""
    inventory, documents, contexts = read_corpus()
    retained_inventory(root, inventory)
    request = {"documents": documents, "cases": contexts["cases"]}
    response = execute(source, request)
    if token(response["documents"]) != token(documents):
        raise ReviewRequired("Baseline changed the frozen JSON values")
    for case in contexts["cases"]:
        expected = contexts["expected"][case["id"]]
        if token(response["outcomes"][case["id"]]) != token(expected):
            raise ReviewRequired(f"Frozen baseline outcome changed: {case['id']}")
    for entry in inventory["entries"]:
        if "document" in entry:
            name = entry["document"]
            entry["value_sha256"] = hashlib.sha256(
                token(response["documents"][name]).encode()
            ).hexdigest()
            entry["outcome"] = response["outcomes"][name]
    return {
        "inventory": inventory,
        "request": request,
        "expected": response["outcomes"],
        "origin": response["origin"],
    }


def legacy_corpus() -> dict[str, Any]:
    """Retain the historical decoder's reviewed JSON output without that decoder."""
    read_corpus()
    corpus: dict[str, Any] = json.loads((FIXTURES / "legacy-corpus.json").read_bytes())
    if corpus["commit"] != history.LEGACY_COMMIT or corpus["tag"] != history.LEGACY_TAG:
        raise ReviewRequired("Historical corpus identity differs")
    return corpus


def capture_legacy(root: Path, source: Path) -> dict[str, Any]:
    corpus = legacy_corpus()
    retained_inventory(root, corpus)
    response = execute(source, corpus["request"])
    if token(response["documents"]) != token(corpus["request"]["documents"]):
        raise ReviewRequired("Historical baseline changed the frozen JSON values")
    if token(response["outcomes"]) != token(corpus["expected"]):
        raise ReviewRequired("Historical baseline outcome changed")
    return {"request": corpus["request"], "expected": corpus["expected"]}


def syntax_request() -> dict[str, Any]:
    cases = json.loads((FIXTURES / "raw-syntax.json").read_bytes())["cases"]
    for case in cases:
        if hashlib.sha256(case["raw"].encode()).hexdigest() != case["raw_sha256"]:
            raise ReviewRequired(f"Raw syntax witness changed: {case['id']}")
    return {"documents": {}, "cases": cases}


def historical_snapshot() -> dict[str, Any]:
    """Release-only IDs distinguish historical witnesses from current cases."""
    corpus = legacy_corpus()
    prefix = "historical/"
    request = {
        "documents": {
            prefix + name: value for name, value in corpus["request"]["documents"].items()
        },
        "cases": [
            {**case, "id": prefix + case["id"], "document": prefix + case["document"]}
            for case in corpus["request"]["cases"]
        ],
    }
    entries = [
        {**entry, "document": prefix + entry["document"]} if "document" in entry else dict(entry)
        for entry in corpus["entries"]
    ]
    return {
        "request": request,
        "expected": {prefix + name: value for name, value in corpus["expected"].items()},
        "inventory": {
            **{name: corpus[name] for name in ("tag", "commit", "roots")},
            "entries": entries,
        },
    }


def _capture_release_semantics(
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    from scripts.schema_compatibility.dataset_migration import dataset_migration
    from scripts.schema_compatibility.semantic import verify_response

    original_contexts = None
    with TemporaryDirectory(prefix="release-dataset-witness-") as temporary:
        published = history.extract(root, history.baseline(root), Path(temporary) / "published")
        transition = dataset_migration(
            root, history.baseline(root), published, root / "packages/contracts"
        )
        if transition is None:
            inventory, documents, contexts = read_corpus()
            request = {"documents": documents, "cases": contexts["cases"]}
            before = execute(published / "src", request)
            verify_response(request, before["outcomes"], before)
            current = execute(root / "packages/contracts/src", request)
            verify_response(request, before["outcomes"], current)
            snapshot = {
                "inventory": inventory,
                "request": request,
                "expected": current["outcomes"],
                "origin": current["origin"],
            }
            snapshot["inventory"]["raw_fixture_source"] = {
                "tag": inventory["tag"],
                "commit": inventory["commit"],
            }
            for entry in snapshot["inventory"]["entries"]:
                if "document" in entry:
                    name = entry["document"]
                    entry["outcome"] = current["outcomes"][name]
                    entry["value_sha256"] = hashlib.sha256(
                        token(current["documents"][name]).encode()
                    ).hexdigest()
            historical = historical_snapshot()
            before_historical = execute(published / "src", historical["request"])
            verify_response(historical["request"], before_historical["outcomes"], before_historical)
            response = execute(root / "packages/contracts/src", historical["request"])
            verify_response(historical["request"], before_historical["outcomes"], response)
            historical["expected"] = response["outcomes"]
            for entry in historical["inventory"]["entries"]:
                if "document" in entry:
                    name = entry["document"]
                    entry["outcome"] = response["outcomes"][name]
                    entry["value_sha256"] = hashlib.sha256(
                        token(response["documents"][name]).encode()
                    ).hexdigest()
        else:
            original = transition.historical_source(root, Path(temporary) / "original")
            snapshot = capture(original.parents[1], original / "src")
            historical = historical_snapshot()
            original_contexts = {
                "published": {
                    "tag": transition.row["before"]["tag"],
                    "commit": transition.row["before"]["commit"],
                    "request": snapshot["request"],
                    "expected": snapshot["expected"],
                },
                "historical": deepcopy(historical),
                "dataset_migration": transition.row,
            }
            current = execute(root / "packages/contracts/src", snapshot["request"])
            verify_response(
                snapshot["request"],
                snapshot["expected"],
                current,
                dataset_transition=transition,
            )
            snapshot["expected"] = current["outcomes"]
            for entry in snapshot["inventory"]["entries"]:
                if "document" in entry:
                    entry["outcome"] = current["outcomes"][entry["document"]]
            legacy = legacy_corpus()
            legacy_response = execute(root / "packages/contracts/src", legacy["request"])
            verify_response(
                legacy["request"],
                legacy["expected"],
                legacy_response,
                dataset_transition=transition,
            )
            historical["expected"] = {
                "historical/" + name: value for name, value in legacy_response["outcomes"].items()
            }
            snapshot["inventory"]["raw_fixture_source"] = {
                "tag": transition.row["before"]["tag"],
                "commit": transition.row["before"]["commit"],
            }
    return snapshot, historical, original_contexts


def write_release(root: Path, plan: dict[str, Any], output: Path) -> None:
    commit = history.git(root, "rev-parse", "HEAD").decode().strip()
    tree = history.git(root, "rev-parse", "HEAD^{tree}").decode().strip()
    key = plan.get("key")
    if key not in {"contracts", "harness"}:
        raise ReviewRequired("Release corpus plan must select a workspace package")
    package_tree = history.git(root, "rev-parse", f"HEAD:packages/{key}").decode().strip()
    if (plan["commit"], plan["tree"]) != (commit, package_tree):
        raise ReviewRequired("Release corpus source differs from the validated plan")
    dirty = history.git(
        root,
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        ".",
        ":(exclude,literal).codegraph",
    )
    if dirty.strip():
        raise ReviewRequired("Release corpus source must be clean")
    if output.exists():
        raise FileExistsError(output)
    snapshot, historical, original_contexts = _capture_release_semantics(root)
    snapshot["inventory"].update(tag=plan["candidate"], commit=plan["commit"])
    snapshot["inventory"]["historical"] = historical["inventory"]
    documents = {**snapshot["request"]["documents"], **historical["request"]["documents"]}
    contexts = {
        "cases": snapshot["request"]["cases"] + historical["request"]["cases"],
        "expected": {**snapshot["expected"], **historical["expected"]},
    }
    raw = syntax_request()
    syntax = execute(root / "packages/contracts/src", raw)
    for case in raw["cases"]:
        if token(syntax["outcomes"][case["id"]]) != token(case["expected"]):
            raise ReviewRequired(f"Raw loader/dumper behavior changed: {case['id']}")
    output.mkdir(parents=True, exist_ok=False)
    contents = {
        "semantic-inventory.json": snapshot["inventory"],
        "semantic-documents.json": documents,
        "semantic-contexts.json": contexts,
        "raw-syntax.json": raw,
    }
    if original_contexts is not None:
        contents["semantic-old-tool-contexts.json"] = original_contexts
    for name, value in contents.items():
        (output / name).write_text(
            json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    files = {
        name: {
            "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest(),
            "size_bytes": (output / name).stat().st_size,
        }
        for name in contents
    }
    provenance = {
        "candidate": plan["candidate"],
        "commit": plan["commit"],
        "tree": plan["tree"],
        "repository_tree": tree,
        "contracts_commit": plan["contracts_commit"],
        "files": files,
        "baseline": json.loads((FIXTURES / "corpus-provenance.json").read_bytes()),
        "scope": (
            "JSON semantic/link outcomes and separate raw loader/dumper witnesses; "
            "not raw artifact/signature verification."
        ),
    }
    (output / "semantic-provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    write_release(
        Path(__file__).resolve().parents[2],
        json.loads(arguments.plan.read_bytes()),
        arguments.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
