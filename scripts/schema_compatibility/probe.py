"""Run the public package validator in a separate, source-isolated Python process."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate object key: {key!r}")
        result[key] = value
    return result


def require_string_keys(value: Any) -> None:
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("Object keys must be strings")
        for child in value.values():
            require_string_keys(child)
    elif isinstance(value, list):
        for child in value:
            require_string_keys(child)


def fixture_document(path: Path) -> Any:
    """Decode frozen fixture values independently of a release's input syntax policy."""
    try:
        source = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            document = json.loads(source, object_pairs_hook=unique_object)
        else:
            parser = YAML(typ="safe", pure=True)
            parser.version = (1, 2)
            parser.allow_duplicate_keys = False
            document = parser.load(source)
        # The semantic corpus is JSON-valued. Reject cycles, implicit native
        # timestamps and non-finite values instead of changing their meaning.
        serialized = json.dumps(document, allow_nan=False)
        require_string_keys(document)
        return json.loads(serialized)
    except Exception as error:
        raise ValueError(f"{path.name}: fixture decoding failed: {error}") from error


def validate(source: Path, request: dict[str, Any]) -> dict[str, Any]:
    sys.path.insert(0, str(source.resolve()))
    contracts = importlib.import_module("robotics_runtime_contracts")
    origin = contracts.__file__
    if origin is None or not Path(origin).resolve().is_relative_to(source.resolve()):
        raise ValueError("Validator import escaped the selected source tree")
    documents = request.get("documents", {})
    for name, path in request.get("files", {}).items():
        documents[name] = fixture_document(Path(path))
    if not documents:
        raise ValueError("Semantic regression corpus is empty")
    for name, document in documents.items():
        original = json.dumps(document, sort_keys=True, allow_nan=False)
        try:
            contracts.validate_document(document)
        except Exception as error:
            raise ValueError(f"{name}: {type(error).__name__}: {error}") from error
        if json.dumps(document, sort_keys=True, allow_nan=False) != original:
            raise ValueError(f"Validator mutated regression document: {name}")
    return {"origin": origin, "documents": documents}


def main() -> int:
    try:
        result = validate(Path(sys.argv[1]), json.load(sys.stdin))
        print(json.dumps(result, allow_nan=False))
        return 0
    except Exception as error:
        print(f"Semantic regression failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
