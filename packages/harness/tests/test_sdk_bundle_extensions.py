from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from robotics_runtime_contracts import load_mapping, validate_document

from robotics_acceptance_harness.documents import (
    BundleValidationError,
    DocumentSource,
    load_bundle,
    load_document,
)

FIXTURES = Path(__file__).parent / "fixtures/simulation"
NAMESPACE = "org.example.sdk"
URI = "https://example.org/schemas/sdk.v1.schema.json"


def test_runtime_extensions_reach_the_product_context_with_their_pinned_schema(
    tmp_path: Path,
) -> None:
    schema = json.dumps(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": URI,
            "type": "object",
            "properties": {"frame": {"type": "string"}},
            "required": ["frame"],
            "additionalProperties": False,
        }
    ).encode()
    runtime = load_mapping(FIXTURES / "runtime.yaml")
    runtime["extensions"] = {NAMESPACE: {"frame": "map"}}
    runtime["extension_schemas"] = [
        {"namespace": NAMESPACE, "schema_uri": URI, "sha256": hashlib.sha256(schema).hexdigest()}
    ]
    registry = {URI: schema}
    validate_document(runtime, extension_schemas=registry)
    path = tmp_path / "runtime.json"
    path.write_text(json.dumps(runtime), encoding="utf-8")
    bundle = load_bundle(FIXTURES / "scenario.yaml", runtime_path=path, extension_schemas=registry)
    assert bundle.runtime.data["extensions"][NAMESPACE]["frame"] == "map"
    source = DocumentSource(path, registry)
    registry.clear()
    assert load_document(source).data["extensions"][NAMESPACE]["frame"] == "map"
    with pytest.raises(BundleValidationError, match="schema registry was supplied twice"):
        load_document(source, extension_schemas={URI: schema})
    with pytest.raises(BundleValidationError, match="sha256"):
        load_bundle(
            FIXTURES / "scenario.yaml", runtime_path=path, extension_schemas={URI: schema + b" "}
        )
