from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Any, NoReturn, Protocol, cast

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError, best_match
from jsonschema.protocols import Validator
from jsonschema.validators import validator_for
from referencing import Registry
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012, Schema, SchemaRegistry, SchemaResource

from robotics_runtime_contracts.catalog import internal_schema_names
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


class _ReferenceResolver(Protocol):
    def lookup(self, ref: str) -> _ResolvedReference: ...

    def in_subresource(self, subresource: SchemaResource) -> _ReferenceResolver: ...

    def dynamic_scope(self) -> Iterable[tuple[str, SchemaRegistry]]: ...


class _ResolvedReference(Protocol):
    @property
    def contents(self) -> Schema: ...

    @property
    def resolver(self) -> _ReferenceResolver: ...


class _ResolverValidatorFactory(Protocol):
    def __call__(
        self,
        schema: Schema,
        *,
        format_checker: FormatChecker,
        registry: SchemaRegistry,
        _resolver: _ReferenceResolver,
    ) -> Validator: ...


@dataclass(frozen=True)
class _CheckedReference:
    contents: Schema
    resolver: _ReferenceResolver


@dataclass(frozen=True)
class _CheckedResolver:
    resolver: _ReferenceResolver
    schema_name: str
    declaration_path: str

    def lookup(self, ref: str) -> _ResolvedReference:
        try:
            resolved = self.resolver.lookup(ref)
        except (Unresolvable, ValueError, TypeError) as error:
            _fail(
                self.schema_name,
                self.declaration_path,
                f"schema reference cannot be evaluated: {error}",
            )
        try:
            if isinstance(resolved.contents, Mapping):
                validator_for(resolved.contents, default=Draft202012Validator).check_schema(
                    dict(resolved.contents)
                )
            else:
                Draft202012Validator.check_schema(resolved.contents)
        except SchemaError as error:
            _fail(
                self.schema_name,
                self.declaration_path,
                f"schema reference cannot be evaluated: {error}",
            )
        return _CheckedReference(resolved.contents, replace(self, resolver=resolved.resolver))

    def in_subresource(self, subresource: SchemaResource) -> _CheckedResolver:
        resolver = self.resolver.in_subresource(subresource)
        return self if resolver is self.resolver else replace(self, resolver=resolver)

    def dynamic_scope(self) -> Iterable[tuple[str, SchemaRegistry]]:
        return self.resolver.dynamic_scope()


def _extension_validation_error(
    schema_name: str,
    schema: Mapping[str, Any],
    instance: Any,
    declaration_path: str,
) -> ValidationError | None:
    resource = DRAFT202012.create_resource(schema)
    registry = Registry().with_resource(resource.id() or "", resource)
    resolver = _CheckedResolver(
        registry.resolver_with_root(resource), schema_name, declaration_path
    )
    # jsonschema 4.26 has no public per-lookup hook for local references. Keep its
    # private resolver injection here; evolve/descend retain this adapter even
    # across $schema dialect changes. All resolution stays in referencing.
    validator = cast(_ResolverValidatorFactory, Draft202012Validator)(
        schema, format_checker=FormatChecker(), registry=registry, _resolver=resolver
    )
    try:
        validation_error: ValidationError | None = best_match(validator.iter_errors(instance))
        return validation_error
    except RecursionError as error:
        _fail(schema_name, declaration_path, f"schema reference cannot be evaluated: {error}")


def _load_extension_schema(
    schema_name: str,
    declaration: Mapping[str, str],
    path: str,
    schema_documents: Mapping[str, bytes | str],
) -> dict[str, Any]:
    namespace = declaration["namespace"]
    uri = declaration["schema_uri"]
    try:
        raw_document = schema_documents[uri]
    except KeyError:
        message = "schema document was not supplied"
        if namespace in schema_documents:
            message = (
                f"schema document key must equal schema_uri {uri!r}, not namespace {namespace!r}"
            )
        _fail(
            schema_name,
            f"{path}.schema_uri",
            message,
        )
    raw_bytes = raw_document if isinstance(raw_document, bytes) else raw_document.encode("utf-8")
    if sha256(raw_bytes).hexdigest() != declaration["sha256"]:
        _fail(
            schema_name,
            f"{path}.sha256",
            "schema digest does not match",
        )

    try:
        extension_schema = loads_mapping(raw_bytes, source_name="extension-schema.json")
    except ContractError as error:
        _fail(
            schema_name,
            path,
            f"schema must be UTF-8 JSON: {error}",
        )
    if extension_schema.get("$id") != uri:
        _fail(
            schema_name,
            f"{path}.schema_uri",
            "must match the schema $id",
        )

    _reject_external_references(schema_name, extension_schema)
    try:
        Draft202012Validator.check_schema(extension_schema)
    except SchemaError as error:
        _fail(
            schema_name,
            path,
            f"invalid Draft 2020-12 schema: {error}",
        )

    return extension_schema


def _validate_payload(
    schema_name: str,
    document: Mapping[str, Any],
    path: str,
    schema_documents: Mapping[str, bytes | str] | None,
) -> None:
    declarations = document.get("extension_schemas", [])
    extensions = document.get("extensions", {})
    if not declarations and not extensions:
        return
    declared_namespaces = [item["namespace"] for item in declarations]
    if len(declared_namespaces) != len(set(declared_namespaces)):
        _fail(schema_name, f"{path}.extension_schemas", "namespaces must be unique")
    if set(declared_namespaces) != set(extensions):
        _fail(
            schema_name,
            f"{path}.extensions",
            "extension payload namespaces must exactly match extension_schemas",
        )
    if not isinstance(schema_documents, Mapping):
        _fail(
            schema_name,
            f"{path}.extension_schemas",
            "declared extensions require supplied schema documents",
        )
    for index, declaration in enumerate(declarations):
        declaration_path = f"{path}.extension_schemas[{index}]"
        extension_schema = _load_extension_schema(
            schema_name, declaration, declaration_path, schema_documents
        )
        namespace = declaration["namespace"]
        validation_error = _extension_validation_error(
            schema_name, extension_schema, extensions[namespace], declaration_path
        )
        if validation_error is not None:
            suffix = validation_error.json_path.removeprefix("$")
            _fail(
                schema_name,
                f"{path}.extensions[{json.dumps(namespace, ensure_ascii=False)}]{suffix}",
                validation_error.message,
            )


_LEGACY_UNPINNED_SCHEMAS = frozenset(
    {
        "acceptance-result.v1",
        "dataset-manifest.v1",
        "evidence-index.v1",
        "execution-permit.v1",
        "execution-verification.v1",
        "model-artifact-manifest.v1",
        "runtime-manifest.v1",
    }
)


def validate_extensions(
    schema_name: str,
    document: Mapping[str, Any],
    schema_documents: Mapping[str, bytes | str] | None,
) -> None:
    """Validate schema-checked public document extensions entirely offline.

    Seven v1 roles historically accepted unpinned payloads. Absence of the new
    extension_schemas field preserves that behavior; its presence opts into
    digest verification and exact namespace matching. New roles are strict.
    The in-toto statement carries extensions inside its predicate.
    """
    if schema_name in internal_schema_names():
        return
    if schema_name in _LEGACY_UNPINNED_SCHEMAS and "extension_schemas" not in document:
        return
    if schema_name == "qualification-bundle.v1":
        _validate_payload(schema_name, document["predicate"], "$.predicate", schema_documents)
    else:
        _validate_payload(schema_name, document, "$", schema_documents)


__all__ = ["ExtensionValidationError", "validate_extensions"]
