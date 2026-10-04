"""Compare identical frozen JSON/context requests in source-isolated public APIs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.schema_compatibility import snapshot
from scripts.schema_compatibility.probe import execute as probe
from scripts.schema_compatibility.structure import ReviewRequired, token

FIXTURES = Path(__file__).resolve().parents[2] / "tests/schema_compatibility/fixtures"


def regressions() -> dict[str, Any]:
    manifest = json.loads((FIXTURES / "provenance.json").read_bytes())
    if not manifest:
        raise ReviewRequired("Frozen semantic regression manifest is empty")
    documents = {}
    for name, provenance in manifest.items():
        raw = (FIXTURES / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != provenance["sha256"]:
            raise ReviewRequired(f"Frozen semantic regression bytes changed: {name}")
        documents[f"regression/{name}"] = json.loads(raw)
    return documents


def published_documents(published: Path) -> dict[str, str]:
    inventory, _, _ = snapshot.read_corpus()
    root = published.parents[1]
    return {
        entry["path"]: str(root / entry["path"])
        for entry in inventory["entries"]
        if "document" in entry
    }


def compare_request(source: Path, request: dict[str, Any], expected: dict[str, Any]) -> None:
    response = probe(source, request)
    if token(response["documents"]) != token(request["documents"]):
        raise ReviewRequired("Candidate changed the semantic regression corpus")
    for case in request["cases"]:
        name = case["id"]
        if token(response["outcomes"][name]) != token(expected[name]):
            raise ReviewRequired(f"Public outcome changed: {name}")


def check_semantics(published: Path, candidate: Path, *, legacy: bool = False) -> int:
    if legacy:
        captured = snapshot.capture_legacy(published, published / "src")
        compare_request(candidate / "src", captured["request"], captured["expected"])
        # Current raw-input restrictions do not retroactively rewrite legacy YAML.
        return len(captured["request"]["cases"])
    captured = snapshot.capture(published.parents[1], published / "src")
    # Both probes receive the same JSON values, descriptors and raw registry bytes.
    # Neither semantic probe decodes YAML or decides which cases survive.
    request = captured["request"]
    compare_request(candidate / "src", request, captured["expected"])
    historical = snapshot.legacy_corpus()
    compare_request(published / "src", historical["request"], historical["expected"])
    compare_request(candidate / "src", historical["request"], historical["expected"])
    raw = snapshot.syntax_request()
    expected = {case["id"]: case["expected"] for case in raw["cases"]}
    compare_request(published / "src", raw, expected)
    compare_request(candidate / "src", raw, expected)
    return len(request["cases"]) + len(historical["request"]["cases"]) + len(raw["cases"])
