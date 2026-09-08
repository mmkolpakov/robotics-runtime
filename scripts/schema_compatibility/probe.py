"""Run the public package validator in a separate, source-isolated Python process."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any


def validate(source: Path, request: dict[str, Any]) -> dict[str, Any]:
    sys.path.insert(0, str(source.resolve()))
    contracts = importlib.import_module("robotics_runtime_contracts")
    origin = contracts.__file__
    if origin is None or not Path(origin).resolve().is_relative_to(source.resolve()):
        raise ValueError("Validator import escaped the selected source tree")
    documents = request.get("documents", {})
    for name, path in request.get("files", {}).items():
        documents[name] = contracts.load_mapping(Path(path))
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
