"""Project deterministic JSON and raw file hashes; this profile is not RFC 8785."""

from __future__ import annotations

import io
import json
from hashlib import sha256
from pathlib import Path

from robotics_runtime_contracts import serialization as _serialization
from robotics_runtime_contracts.errors import ContractError


def _check_string(value: str, path: str) -> int:
    if len(value) > _serialization.MAX_DOCUMENT_BYTES:
        _serialization._limit("string exceeds the document byte limit", path)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ContractError(
            "strings must contain Unicode scalar values, without surrogate code points",
            error_id="input.invalid_unicode",
            json_path=path,
        ) from error
    if len(encoded) > _serialization.MAX_DOCUMENT_BYTES:
        _serialization._limit("string exceeds the document UTF-8 byte limit", path)
    return len(encoded)


def _check_integer(value: int, path: str) -> int:
    # Reject clearly oversized integers before decimal conversion, without
    # changing the interpreter's process-wide integer conversion limit.
    if value.bit_length() > 4 * _serialization.MAX_DOCUMENT_BYTES:
        _serialization._limit("integer exceeds the document byte limit", path)
    try:
        size = len(str(value))
    except ValueError as error:
        raise ContractError(
            "integer exceeds the interpreter's decimal conversion limit",
            error_id="input.limit_exceeded",
            json_path=path,
        ) from error
    if size > _serialization.MAX_DOCUMENT_BYTES:
        _serialization._limit("integer exceeds the document byte limit", path)
    return size


def _check_scalar(value: object, path: str) -> int:
    if type(value) is str:
        return _check_string(value, path)
    elif type(value) is int:
        return _check_integer(value, path)
    elif type(value) is float:
        _serialization.ensure_finite_numbers(value, path)
    elif value is not None and type(value) is not bool:
        raise ContractError(
            f"unsupported JSON value type: {type(value).__name__}",
            error_id="input.invalid_type",
            json_path=path,
        )
    return 1  # Lower bound for finite floats, booleans and null.


def _check_value(value: object, path: str, depth: int, budget: list[int]) -> None:
    # Count nodes and a byte lower bound before encoding. The latter also
    # bounds work on shared strings; the encoder enforces exact output size.
    budget[0] += 1
    if depth > _serialization.MAX_DOCUMENT_DEPTH or budget[0] > _serialization.MAX_DOCUMENT_NODES:
        _serialization._limit("document exceeds nesting or node limit", path)
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise ContractError(
                    "object keys must be strings",
                    error_id="input.invalid_type",
                    json_path=path,
                )
            child_path = _serialization._member_path(path, key)
            _check_value(key, child_path, depth + 1, budget)
            _check_value(child, child_path, depth + 1, budget)
    elif type(value) is list:
        for index, child in enumerate(value):
            _check_value(child, f"{path}[{index}]", depth + 1, budget)
    else:
        budget[1] += _check_scalar(value, path)
        if budget[1] > _serialization.MAX_DOCUMENT_BYTES:
            _serialization._limit("document values exceed the UTF-8 byte limit", path)


def dumps_canonical(document: object) -> bytes:
    """Return project deterministic JSON, NOT RFC 8785/JCS.

    Built-in JSON containers/scalars become compact UTF-8 without a BOM or
    newline. Keys sort by Unicode code point; array order and exact integers
    are preserved. Finite floats use native JSON spelling, including -0.0.
    SPEC17 byte/depth/node bounds apply; invalid values raise ContractError.
    """

    _check_value(document, "$", 1, [0, 0])
    encoder = json.JSONEncoder(
        ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    )
    output = io.BytesIO()
    for chunk in encoder.iterencode(document):
        encoded = chunk.encode("utf-8")
        if output.tell() + len(encoded) > _serialization.MAX_DOCUMENT_BYTES:
            _serialization._limit("serialized document exceeds the UTF-8 byte limit")
        output.write(encoded)
    return output.getvalue()


def file_sha256(path: str | Path) -> str:
    """Hash the original file bytes in bounded chunks; propagate file I/O errors.

    No JSON parsing or serialization is involved, and the document byte limit
    does not restrict artifact size. Home paths are expanded before opening.
    """

    digest = sha256()
    with Path(path).expanduser().open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["dumps_canonical", "file_sha256"]
