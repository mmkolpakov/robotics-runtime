"""Attach host-owned observations with the existing extension API and exact public writer."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

from robotics_runtime_contracts import load_mapping, validate_document
from robotics_runtime_contracts.writers import protect_inputs, write_document

NAMESPACE = "org.robotics.runtime.host"
SCHEMA_URI = "urn:robotics:host:composition:v1"


def verify_references(value: object) -> set[Path]:
    references: set[Path] = set()
    if isinstance(value, list):
        for child in value:
            references.update(verify_references(child))
    elif isinstance(value, dict):
        if {"uri", "sha256", "size_bytes"} <= value.keys():
            parts = urlsplit(value["uri"])
            if parts.scheme != "file" or parts.netloc or parts.query or parts.fragment:
                raise ValueError("host producer requires local retained file evidence")
            path = Path(url2pathname(parts.path))
            raw = path.read_bytes()
            references.add(path.resolve())
            if sha256(raw).hexdigest() != value["sha256"] or len(raw) != value["size_bytes"]:
                raise ValueError(f"observed reference does not match retained bytes: {path}")
        for child in value.values():
            references.update(verify_references(child))

    return references


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--composition", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    protect_inputs(args.output, [args.template, args.composition, args.schema])
    schema = args.schema.read_bytes()
    document = dict(load_mapping(args.template))
    composition = load_mapping(args.composition)
    references = verify_references(composition)
    protect_inputs(args.output, [args.template, args.composition, args.schema, *references])
    extensions = dict(document.get("extensions", {}))
    if NAMESPACE in extensions:
        raise ValueError("host composition already exists")
    extensions[NAMESPACE] = composition
    document["extensions"] = extensions
    declarations = list(document.get("extension_schemas", []))
    declarations.append(
        {"namespace": NAMESPACE, "schema_uri": SCHEMA_URI, "sha256": sha256(schema).hexdigest()}
    )
    document["extension_schemas"] = declarations
    validate_document(document, extension_schemas={SCHEMA_URI: schema})
    write_document(document, args.output, extension_schemas={SCHEMA_URI: schema})


if __name__ == "__main__":
    main()
