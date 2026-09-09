"""Shared raw-byte extension schema and document data for public API tests."""

import json
from copy import deepcopy
from hashlib import sha256
from typing import Any

SCHEMA_URI = "https://schemas.example.org/mission.v1.schema.json"
NAMESPACE = "org.example.mission"
RAW_SCHEMA = json.dumps(
    {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_URI,
        "type": "object",
        "additionalProperties": False,
        "required": ["mission_id"],
        "properties": {"mission_id": {"type": "string", "minLength": 1}},
    },
    sort_keys=True,
).encode()
SCHEMAS = {SCHEMA_URI: RAW_SCHEMA}


def with_extension(document: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(document)
    result["extension_schemas"] = [
        {"namespace": NAMESPACE, "schema_uri": SCHEMA_URI, "sha256": sha256(RAW_SCHEMA).hexdigest()}
    ]
    result["extensions"] = {NAMESPACE: {"mission_id": "mission-42"}}
    return result
