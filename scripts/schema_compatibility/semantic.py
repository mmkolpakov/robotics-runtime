"""Compare identical frozen JSON/context requests in source-isolated public APIs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from scripts.schema_compatibility import snapshot
from scripts.schema_compatibility.probe import execute as probe
from scripts.schema_compatibility.structure import ReviewRequired, token

if TYPE_CHECKING:
    from scripts.schema_compatibility.dataset_migration import DatasetMigration


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


def compare_request(
    source: Path,
    request: dict[str, Any],
    expected: dict[str, Any],
    *,
    dataset_transition: DatasetMigration | None = None,
) -> None:
    response = probe(source, request)
    verify_response(request, expected, response, dataset_transition=dataset_transition)


def verify_response(
    request: dict[str, Any],
    expected: dict[str, Any],
    response: dict[str, Any],
    *,
    dataset_transition: DatasetMigration | None = None,
) -> None:
    if token(response["documents"]) != token(request["documents"]):
        raise ReviewRequired("Candidate changed the semantic regression corpus")
    refusals = (
        dataset_transition.refusals(request, expected) if dataset_transition is not None else {}
    )
    for case in request["cases"]:
        name = case["id"]
        actual = response["outcomes"][name]
        if name in refusals:
            readable = {key: actual.get(key) for key in ("exception", "error_id", "message")}
            if (
                actual.get("status") != "rejected"
                or token(readable) != token(refusals[name]["refusal"])
                or hashlib.sha256(token(actual).encode()).hexdigest()
                != refusals[name]["new_outcome_sha256"]
            ):
                raise ReviewRequired(f"Dataset migration clean refusal changed: {name}")
            continue
        if token(actual) != token(expected[name]):
            raise ReviewRequired(f"Public outcome changed: {name}")


def check_semantics(
    published: Path,
    candidate: Path,
    *,
    legacy: bool = False,
    dataset_transition: DatasetMigration | None = None,
) -> int:
    if legacy:
        captured = snapshot.capture_legacy(published, published / "src")
        compare_request(candidate / "src", captured["request"], captured["expected"])
        # Current raw-input restrictions do not retroactively rewrite legacy YAML.
        return len(captured["request"]["cases"])
    if dataset_transition is not None:
        captured = snapshot.capture(published.parents[1], published / "src")
    else:
        _, documents, contexts = snapshot.read_corpus()
        request = {"documents": documents, "cases": contexts["cases"]}
        response = probe(published / "src", request)
        verify_response(request, response["outcomes"], response)
        captured = {"request": request, "expected": response["outcomes"]}
    # Both probes receive the same JSON values, descriptors and raw registry bytes.
    # Neither semantic probe decodes YAML or decides which cases survive.
    request = captured["request"]
    compare_request(
        candidate / "src", request, captured["expected"], dataset_transition=dataset_transition
    )
    historical = snapshot.legacy_corpus()
    if dataset_transition is None:
        # Historical request bytes stay frozen; compare the current published reader's
        # actual outcomes, without recasting an earlier schema generation as compatible.
        response = probe(published / "src", historical["request"])
        expected = response["outcomes"]
        verify_response(historical["request"], expected, response)
    else:
        expected = historical["expected"]
        compare_request(published / "src", historical["request"], expected)
    compare_request(
        candidate / "src", historical["request"], expected, dataset_transition=dataset_transition
    )
    raw = snapshot.syntax_request()
    expected = {case["id"]: case["expected"] for case in raw["cases"]}
    compare_request(published / "src", raw, expected)
    compare_request(candidate / "src", raw, expected)
    return len(request["cases"]) + len(historical["request"]["cases"]) + len(raw["cases"])
