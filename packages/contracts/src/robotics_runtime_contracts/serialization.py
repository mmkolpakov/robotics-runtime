from __future__ import annotations

import json
import re
from collections.abc import Mapping
from math import isfinite
from pathlib import Path
from typing import Any, BinaryIO, NoReturn

import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from robotics_runtime_contracts.errors import ContractError

MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
MAX_DOCUMENT_DEPTH = 64
MAX_DOCUMENT_NODES = 100_000


class DocumentParseError(ContractError):
    """Raised when a JSON or YAML document cannot be loaded as an object."""

    error_id = "input.parse_failed"


class NonFiniteNumberError(ContractError):
    """Raised when a document contains a number forbidden by RFC 8259."""

    error_id = "input.non_finite_number"


def ensure_finite_numbers(value: Any, path: str = "$") -> None:
    """Reject NaN and infinities before schema or policy evaluation."""

    if isinstance(value, float) and not isfinite(value):
        raise NonFiniteNumberError(f"{path}: non-finite numbers are not valid JSON", json_path=path)
    if isinstance(value, Mapping):
        for key, item in value.items():
            ensure_finite_numbers(item, _member_path(path, str(key)))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            ensure_finite_numbers(item, f"{path}[{index}]")


def _member_path(path: str, key: str) -> str:
    return f"{path}.{key}" if key.isidentifier() else f"{path}[{json.dumps(key)}]"


def _limit(message: str, path: str = "$") -> NoReturn:
    raise DocumentParseError(message, error_id="input.limit_exceeded", json_path=path)


def _check_size(source: str | bytes) -> None:
    if len(source) > MAX_DOCUMENT_BYTES:
        _limit(f"document exceeds {MAX_DOCUMENT_BYTES} UTF-8 bytes")
    if isinstance(source, str) and len(source.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        _limit(f"document exceeds {MAX_DOCUMENT_BYTES} UTF-8 bytes")


def read_document_stream(stream: BinaryIO) -> bytes:
    """Read at most the document byte limit plus one sentinel byte."""

    source = stream.read(MAX_DOCUMENT_BYTES + 1)
    _check_size(source)
    return source


def read_document_bytes(path: str | Path) -> bytes:
    with Path(path).expanduser().open("rb") as stream:
        return read_document_stream(stream)


def _duplicate(key: str, path: str) -> NoReturn:
    raise DocumentParseError(
        f"duplicate object key: {key!r}", error_id="input.duplicate_key", json_path=path
    )


class _ObjectPairs(list[tuple[str, Any]]):
    """Keep JSON object entries intact until duplicate detection has a full path."""


def _json_value(value: Any, path: str, depth: int, count: list[int]) -> Any:
    count[0] += 1
    if depth > MAX_DOCUMENT_DEPTH or count[0] > MAX_DOCUMENT_NODES:
        _limit("document exceeds nesting or node limit", path)
    if isinstance(value, _ObjectPairs):
        result: dict[str, Any] = {}
        for key, item in value:
            child_path = _member_path(path, key)
            if key in result:
                _duplicate(key, child_path)
            _json_value(key, child_path, depth + 1, count)
            result[key] = _json_value(item, child_path, depth + 1, count)
        return result
    if isinstance(value, list):
        return [_json_value(item, f"{path}[{i}]", depth + 1, count) for i, item in enumerate(value)]
    ensure_finite_numbers(value, path)
    return value


# YAML 1.2.2 section 10.3.2. Order matters: decimal integers precede floats.
_CORE_PATTERNS = {
    "null": re.compile(r"^(?:null|Null|NULL|~|)$"),
    "bool": re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    "int": re.compile(r"^(?:[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)$"),
    "float": re.compile(
        r"^(?:[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?"
        r"|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$"
    ),
}
_TAG_PREFIX = "tag:yaml.org,2002:"


class _CoreLoader(yaml.SafeLoader):
    # Do not mutate SafeLoader's YAML 1.1 resolver table in the host process.
    yaml_implicit_resolvers = {
        None: [(_TAG_PREFIX + tag, pattern) for tag, pattern in _CORE_PATTERNS.items()]
    }

    def __init__(self, stream: str) -> None:
        super().__init__(stream)
        self._depth = 0
        self._nodes = 0

    def compose_node(self, parent: Any, index: Any) -> Node | None:
        # PyYAML's public parser event method is unannotated in types-PyYAML.
        event = self.peek_event()  # type: ignore[no-untyped-call]
        if isinstance(event, AliasEvent):
            raise DocumentParseError("YAML aliases are not allowed", error_id="input.yaml_alias")
        self._depth += 1
        self._nodes += 1
        try:
            if self._depth > MAX_DOCUMENT_DEPTH or self._nodes > MAX_DOCUMENT_NODES:
                _limit("document exceeds nesting or node limit")
            return super().compose_node(parent, index)
        finally:
            self._depth -= 1


class _CoreDumper(yaml.SafeDumper):
    yaml_implicit_resolvers = _CoreLoader.yaml_implicit_resolvers

    def ignore_aliases(self, data: Any) -> bool:
        return True


def dumps_yaml(document: Mapping[str, Any]) -> str:
    """Quote strings according to the loader's core schema and emit no aliases."""

    ensure_finite_numbers(document)
    return yaml.dump(dict(document), Dumper=_CoreDumper, sort_keys=False)


def _yaml_mapping(node: MappingNode, path: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = _yaml_value(key_node, path)
        if not isinstance(key, str):
            raise DocumentParseError("object keys must be strings", json_path=path)
        child_path = _member_path(path, key)
        if key in result:
            _duplicate(key, child_path)
        result[key] = _yaml_value(value_node, child_path)
    return result


def _yaml_scalar(node: ScalarNode, path: str) -> Any:
    tag = node.tag.removeprefix(_TAG_PREFIX)
    text = node.value
    if tag == "str":
        return text
    if tag in _CORE_PATTERNS and _CORE_PATTERNS[tag].fullmatch(text):
        if tag == "null":
            return None
        if tag == "bool":
            return text.lower() == "true"
        if tag == "int":
            return int(text, 8 if text.startswith("0o") else 16 if text.startswith("0x") else 10)
        number = float(text.lower().replace(".inf", "inf").replace(".nan", "nan"))
        ensure_finite_numbers(number, path)
        return number
    raise DocumentParseError(f"unsupported or invalid YAML core tag: {node.tag}", json_path=path)


def _yaml_value(node: Node, path: str = "$") -> Any:
    # Construct only the JSON data model. PyYAML's constructors would accept
    # YAML 1.1 explicit tags, merge keys, non-string keys and Python dates.
    if isinstance(node, MappingNode) and node.tag == _TAG_PREFIX + "map":
        return _yaml_mapping(node, path)
    if isinstance(node, SequenceNode) and node.tag == _TAG_PREFIX + "seq":
        return [_yaml_value(item, f"{path}[{i}]") for i, item in enumerate(node.value)]
    if isinstance(node, ScalarNode) and node.tag.startswith(_TAG_PREFIX):
        return _yaml_scalar(node, path)
    raise DocumentParseError(f"unsupported or invalid YAML core tag: {node.tag}", json_path=path)


def loads_mapping(
    source: str | bytes,
    *,
    source_name: str = "document",
) -> dict[str, Any]:
    """Load bounded, duplicate-free JSON or YAML 1.2 core data as an object."""

    try:
        _check_size(source)
        text = source.decode("utf-8") if isinstance(source, bytes) else source
        suffix = Path(source_name).suffix.lower()
        use_json = suffix == ".json" or (
            suffix not in {".yaml", ".yml"} and text.lstrip().startswith(("{", "["))
        )
        if use_json:
            value = _json_value(json.loads(text, object_pairs_hook=_ObjectPairs), "$", 1, [0])
        else:
            node = yaml.compose(text, Loader=_CoreLoader)
            value = _yaml_value(node) if node is not None else None
    except ContractError:
        raise
    except RecursionError as error:
        raise DocumentParseError(
            "document exceeds parser nesting limit", error_id="input.limit_exceeded"
        ) from error
    except (UnicodeError, ValueError, yaml.YAMLError) as error:
        raise DocumentParseError(f"cannot parse {source_name}: {error}") from error
    if not isinstance(value, dict):
        raise DocumentParseError(f"{source_name} must contain an object", json_path="$")
    return value


def load_mapping(path: str | Path) -> dict[str, Any]:
    """Load a bounded JSON or YAML object from disk."""

    document_path = Path(path).expanduser()
    return loads_mapping(read_document_bytes(document_path), source_name=str(document_path))


__all__ = [
    "DocumentParseError",
    "NonFiniteNumberError",
    "ensure_finite_numbers",
    "load_mapping",
    "loads_mapping",
]
