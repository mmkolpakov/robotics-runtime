from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import Any, NoReturn

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, best_match
from referencing import Registry
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012

from robotics_runtime_contracts.errors import ContractError
from robotics_runtime_contracts.semantics import SemanticValidationError
from robotics_runtime_contracts.serialization import loads_mapping


class ExtensionValidationError(SemanticValidationError):
    """Raised when a declared domain extension cannot be verified."""

    error_id = "extension.validation_failed"


def _fail(schema_name: str, path: str, message: str) -> NoReturn:
    raise ExtensionValidationError(schema_name, path, message)


_SINGLE_SUBSCHEMA_KEYWORDS = frozenset(
    {
        "additionalProperties",
        "contains",
        "contentSchema",
        "else",
        "if",
        "items",
        "not",
        "propertyNames",
        "then",
        "unevaluatedItems",
        "unevaluatedProperties",
    }
)
_SUBSCHEMA_ARRAY_KEYWORDS = frozenset({"allOf", "anyOf", "oneOf", "prefixItems"})
_SUBSCHEMA_MAP_KEYWORDS = frozenset(
    {"$defs", "definitions", "dependentSchemas", "patternProperties", "properties"}
)


def _reject_external_references(schema_name: str, schema: object, path: str = "$") -> None:
    if isinstance(schema, bool) or not isinstance(schema, dict):
        return

    for keyword in ("$ref", "$dynamicRef"):
        reference = schema.get(keyword)
        if reference is not None and (
            not isinstance(reference, str) or not reference.startswith("#")
        ):
            _fail(
                schema_name,
                f"{path}.{keyword}",
                "external schema references are not allowed",
            )

    for keyword in _SINGLE_SUBSCHEMA_KEYWORDS:
        if keyword in schema:
            _reject_external_references(schema_name, schema[keyword], f"{path}.{keyword}")
    for keyword in _SUBSCHEMA_ARRAY_KEYWORDS:
        value = schema.get(keyword)
        if isinstance(value, list):
            for index, child in enumerate(value):
                _reject_external_references(
                    schema_name,
                    child,
                    f"{path}.{keyword}[{index}]",
                )
    for keyword in _SUBSCHEMA_MAP_KEYWORDS:
        value = schema.get(keyword)
        if isinstance(value, dict):
            for name, child in value.items():
                _reject_external_references(
                    schema_name,
                    child,
                    f"{path}.{keyword}.{name}",
                )


def validate_extensions(
    schema_name: str,
    document: Mapping[str, Any],
    schema_documents: Mapping[str, bytes | str] | None,
) -> None:
    """Validate declared scenario extensions without performing network access."""

    if not schema_name.startswith("acceptance-scenario."):
        return

    declarations = document.get("extension_schemas", [])
    extensions = document.get("extensions", {})
    if not declarations and not extensions:
        return
    if not isinstance(schema_documents, Mapping):
        _fail(
            schema_name,
            "$.extension_schemas",
            "declared extensions require supplied schema documents",
        )

    declared_namespaces = [item["namespace"] for item in declarations]
    if len(declared_namespaces) != len(set(declared_namespaces)):
        _fail(schema_name, "$.extension_schemas", "namespaces must be unique")
    if set(declared_namespaces) != set(extensions):
        _fail(
            schema_name,
            "$.extensions",
            "extension payload namespaces must exactly match extension_schemas",
        )

    for index, declaration in enumerate(declarations):
        namespace = declaration["namespace"]
        uri = declaration["schema_uri"]
        try:
            raw_document = schema_documents[uri]
        except KeyError:
            message = "schema document was not supplied"
            if namespace in schema_documents:
                message = (
                    f"schema document key must equal schema_uri {uri!r}, "
                    f"not namespace {namespace!r}"
                )
            _fail(
                schema_name,
                f"$.extension_schemas[{index}].schema_uri",
                message,
            )
        raw_bytes = (
            raw_document if isinstance(raw_document, bytes) else raw_document.encode("utf-8")
        )
        if sha256(raw_bytes).hexdigest() != declaration["sha256"]:
            _fail(
                schema_name,
                f"$.extension_schemas[{index}].sha256",
                "schema digest does not match",
            )

        try:
            extension_schema = loads_mapping(raw_bytes, source_name="extension-schema.json")
        except ContractError as error:
            _fail(
                schema_name,
                f"$.extension_schemas[{index}]",
                f"schema must be UTF-8 JSON: {error}",
            )
        if extension_schema.get("$id") != uri:
            _fail(
                schema_name,
                f"$.extension_schemas[{index}].schema_uri",
                "must match the schema $id",
            )

        _reject_external_references(schema_name, extension_schema)
        try:
            Draft202012Validator.check_schema(extension_schema)
        except SchemaError as error:
            _fail(
                schema_name,
                f"$.extension_schemas[{index}]",
                f"invalid Draft 2020-12 schema: {error}",
            )

        registry = Registry().with_resource(uri, DRAFT202012.create_resource(extension_schema))
        try:
            validation_error = best_match(
                Draft202012Validator(
                    extension_schema,
                    format_checker=FormatChecker(),
                    registry=registry,
                ).iter_errors(extensions[namespace])
            )
        except (Unresolvable, RecursionError) as error:
            _fail(
                schema_name,
                f"$.extension_schemas[{index}]",
                f"schema reference cannot be evaluated: {error}",
            )
        if validation_error is not None:
            suffix = validation_error.json_path.removeprefix("$")
            _fail(
                schema_name,
                f"$.extensions.{namespace}{suffix}",
                validation_error.message,
            )


__all__ = ["ExtensionValidationError", "validate_extensions"]
