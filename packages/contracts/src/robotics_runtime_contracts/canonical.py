"""Project deterministic JSON and raw file hashes; this profile is not RFC 8785."""

from __future__ import annotations

import io
import json
from hashlib import sha256
from math import isfinite
from pathlib import Path

from robotics_runtime_contracts import serialization as _serialization
from robotics_runtime_contracts.errors import ContractError

_Path = tuple[str | int, ...]


def _write_member(output: io.StringIO, key: str, remaining: int) -> int | None:
    if key.isidentifier():
        size = 1 + len(key.encode("utf-8"))
        if size > remaining:
            return None
        output.write(".")
        output.write(key)
        return size
    if remaining < 4:  # Reserve brackets and quotes, including for an empty key.
        return None
    output.write('["')
    size = 4
    # JSON string escaping is compositional. Let the standard encoder escape
    # bounded pieces, without allocating a potentially 12x-expanded whole key.
    for offset in range(0, len(key), 4096):
        escaped = json.dumps(key[offset : offset + 4096], ensure_ascii=True)[1:-1]
        size += len(escaped)  # ensure_ascii=True makes characters equal bytes.
        if size > remaining:
            return None
        output.write(escaped)
    output.write('"]')
    return size


def _render_path(path: _Path) -> str:
    # Validation keeps references to keys, not a copy of every ancestor path.
    # Only an error renders a diagnostic, stopping at the last complete member.
    output = io.StringIO()
    output.write("$")
    remaining = _serialization.MAX_DOCUMENT_BYTES - 1
    for member in path:
        checkpoint = output.tell()
        if isinstance(member, str):
            size = _write_member(output, member, remaining)
        else:
            suffix = f"[{member}]"
            size = len(suffix) if len(suffix) <= remaining else None
            if size is not None:
                output.write(suffix)
        if size is None:
            output.seek(checkpoint)
            output.truncate()
            break
        remaining -= size
    return output.getvalue()


def _check_string(value: str, path: _Path, *, key: bool = False) -> int:
    if len(value) > _serialization.MAX_DOCUMENT_BYTES:
        _serialization._limit("string exceeds the document byte limit", _render_path(path))
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ContractError(
            "strings must contain Unicode scalar values, without surrogate code points",
            error_id="input.invalid_unicode",
            json_path=_render_path((*path, value) if key else path),
        ) from error
    if len(encoded) > _serialization.MAX_DOCUMENT_BYTES:
        _serialization._limit("string exceeds the document UTF-8 byte limit", _render_path(path))
    return len(encoded)


def _check_integer(value: int, path: _Path) -> int:
    # Reject clearly oversized integers before decimal conversion, without
    # changing the interpreter's process-wide integer conversion limit.
    if value.bit_length() > 4 * _serialization.MAX_DOCUMENT_BYTES:
        _serialization._limit("integer exceeds the document byte limit", _render_path(path))
    try:
        size = len(str(value))
    except ValueError as error:
        raise ContractError(
            "integer exceeds the interpreter's decimal conversion limit",
            error_id="input.limit_exceeded",
            json_path=_render_path(path),
        ) from error
    if size > _serialization.MAX_DOCUMENT_BYTES:
        _serialization._limit("integer exceeds the document byte limit", _render_path(path))
    return size


def _check_scalar(value: object, path: _Path) -> int:
    if type(value) is str:
        return _check_string(value, path)
    elif type(value) is int:
        return _check_integer(value, path)
    elif type(value) is float:
        if not isfinite(value):
            _serialization.ensure_finite_numbers(value, _render_path(path))
    elif value is not None and type(value) is not bool:
        raise ContractError(
            f"unsupported JSON value type: {type(value).__name__}",
            error_id="input.invalid_type",
            json_path=_render_path(path),
        )
    return 1  # Lower bound for finite floats, booleans and null.


def _check_value(value: object, path: _Path, depth: int, budget: list[int]) -> None:
    # Count nodes and a byte lower bound before encoding. The latter also
    # bounds work on shared strings; the encoder enforces exact output size.
    budget[0] += 1
    if depth > _serialization.MAX_DOCUMENT_DEPTH or budget[0] > _serialization.MAX_DOCUMENT_NODES:
        _serialization._limit("document exceeds nesting or node limit", _render_path(path))
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise ContractError(
                    "object keys must be strings",
                    error_id="input.invalid_type",
                    json_path=_render_path(path),
                )
            # Reject oversized keys at their containing object before retaining
            # the child path. The scalar visit still counts key nodes and bytes.
            _check_string(key, path, key=True)
            child_path = (*path, key)
            _check_value(key, child_path, depth + 1, budget)
            _check_value(child, child_path, depth + 1, budget)
    elif type(value) is list:
        for index, child in enumerate(value):
            _check_value(child, (*path, index), depth + 1, budget)
    else:
        budget[1] += _check_scalar(value, path)
        if budget[1] > _serialization.MAX_DOCUMENT_BYTES:
            _serialization._limit("document values exceed the UTF-8 byte limit", _render_path(path))


def dumps_canonical(document: object) -> bytes:
    """Return project deterministic JSON, NOT RFC 8785/JCS.

    Built-in JSON containers/scalars become compact UTF-8 without a BOM or
    newline. Keys sort by Unicode code point; array order and exact integers
    are preserved. Finite floats use native JSON spelling, including -0.0.
    SPEC17 byte/depth/node bounds apply; invalid values raise ContractError.
    """

    _check_value(document, (), 1, [0, 0])
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
