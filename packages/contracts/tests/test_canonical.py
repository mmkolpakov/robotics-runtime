from __future__ import annotations

import io
import json
import sys
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

import robotics_runtime_contracts as contracts
from robotics_runtime_contracts import ContractError, dumps_canonical, file_sha256
from robotics_runtime_contracts import serialization as ser


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        (None, b"null"),
        (True, b"true"),
        (False, b"false"),
        (1, b"1"),
        (1.0, b"1.0"),
        (0.0, b"0.0"),
        (-0.0, b"-0.0"),
        (1e-7, b"1e-07"),
        (1e-6, b"1e-06"),
        (1e20, b"1e+20"),
        (5e-324, b"5e-324"),
        (1.7976931348623157e308, b"1.7976931348623157e+308"),
        ('é\n\t\b\r\f\x00\\"/', b'"\xc3\xa9\\n\\t\\b\\r\\f\\u0000\\\\\\"/"'),
        (
            {"z": [3, True, 1, {"b": 0, "a": None}], "a": {}},
            b'{"a":{},"z":[3,true,1,{"a":null,"b":0}]}',
        ),
        ({"\U00010000": 1, "\ue000": 2}, '{"\ue000":2,"\U00010000":1}'.encode()),
    ],
)
def test_profile_golden_bytes(document: object, expected: bytes) -> None:
    assert dumps_canonical(document) == expected
    assert not expected.startswith(b"\xef\xbb\xbf")
    assert not expected.endswith(b"\n")


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (2**53 - 1, b"9007199254740991"),
        (2**53, b"9007199254740992"),
        (2**53 + 1, b"9007199254740993"),
        (-(2**53 + 1), b"-9007199254740993"),
        (2**63 - 1, b"9223372036854775807"),
        (-(2**63), b"-9223372036854775808"),
        (2**64, b"18446744073709551616"),
        (1785067200123456789, b"1785067200123456789"),
        (1785067200123456790, b"1785067200123456790"),
    ],
)
def test_integer_tokens_are_exact_without_a_53_or_64_bit_cap(number: int, expected: bytes) -> None:
    encoded = dumps_canonical({"ns": number})
    assert encoded == b'{"ns":' + expected + b"}"
    decoded = json.loads(encoded)["ns"]
    assert type(decoded) is int and decoded == number


def test_adjacent_ns_and_boolean_numeric_types_remain_distinct() -> None:
    values = [1785067200123456789, 1785067200123456790, True, 1, 1.0, -0.0, 0.0]
    outputs = [dumps_canonical({"value": value}) for value in values]
    assert len(set(outputs)) == len(values)
    assert len({sha256(output).digest() for output in outputs}) == len(values)


@pytest.mark.parametrize(
    "value", [b"x", bytearray(b"x"), (1, 2), {1, 2}, Decimal("1.25"), Path("x"), object()]
)
def test_non_json_types_have_their_member_path(value: object) -> None:
    with pytest.raises(ContractError) as caught:
        dumps_canonical({"items": [{"a.b": value}]})
    assert caught.value.error_id == "input.invalid_type"
    assert caught.value.json_path == '$.items[0]["a.b"]'


@pytest.mark.parametrize("key", [1, True, None, 1.5, ("x",)])
def test_keys_are_rejected_instead_of_coerced_or_skipped(key: Any) -> None:
    with pytest.raises(ContractError) as caught:
        dumps_canonical({"outer": {key: 1}})
    assert caught.value.error_id == "input.invalid_type"
    assert caught.value.json_path == "$.outer"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_error_reuses_the_existing_error_family(value: float) -> None:
    with pytest.raises(contracts.NonFiniteNumberError) as caught:
        dumps_canonical({"samples": [0, value]})
    assert caught.value.error_id == "input.non_finite_number"
    assert caught.value.json_path == "$.samples[1]"


@pytest.mark.parametrize("text", ["\ud800", "\udfff", "text\ud800", "\ud83d\ude00"])
def test_surrogate_code_points_are_rejected_without_normalizing_strings(text: str) -> None:
    with pytest.raises(ContractError) as caught:
        dumps_canonical({"text": text})
    assert caught.value.error_id == "input.invalid_unicode"
    assert caught.value.json_path == "$.text"
    with pytest.raises(ContractError) as key_error:
        dumps_canonical({text: 1})
    assert key_error.value.error_id == "input.invalid_unicode"
    assert key_error.value.json_path == f"$[{json.dumps(text)}]"


def test_valid_escaped_surrogate_pair_loads_as_a_unicode_scalar() -> None:
    assert (
        dumps_canonical(contracts.loads_mapping('{"x":"\\ud83d\\ude00"}'))
        == b'{"x":"\xf0\x9f\x98\x80"}'
    )
    assert dumps_canonical({"text": "e\u0301"}) != dumps_canonical({"text": "é"})


def test_depth_and_node_boundaries_match_the_document_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ser, "MAX_DOCUMENT_DEPTH", 3)
    assert dumps_canonical({"a": {"b": 1}}) == b'{"a":{"b":1}}'
    with pytest.raises(ContractError) as depth_error:
        dumps_canonical({"a": {"b": {"c": 1}}})
    assert depth_error.value.error_id == "input.limit_exceeded"
    assert depth_error.value.json_path == "$.a.b.c"
    monkeypatch.setattr(ser, "MAX_DOCUMENT_NODES", 3)
    assert dumps_canonical({"a": 1}) == b'{"a":1}'  # object, key, value
    with pytest.raises(ContractError) as node_error:
        dumps_canonical({"a": 1, "b": 2})
    assert node_error.value.error_id == "input.limit_exceeded"
    assert node_error.value.json_path == "$.b"


def test_cycles_and_deep_values_fail_as_contract_errors() -> None:
    cycle: list[object] = []
    cycle.append(cycle)
    deep: object = 0
    for _ in range(1500):
        deep = [deep]
    for value in (cycle, deep):
        with pytest.raises(ContractError) as caught:
            dumps_canonical(value)
        assert caught.value.error_id == "input.limit_exceeded"
        assert caught.value.json_path is not None


def test_shared_containers_are_expanded_with_the_node_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared = {"x": 1}
    assert dumps_canonical([shared, shared]) == b'[{"x":1},{"x":1}]'
    monkeypatch.setattr(ser, "MAX_DOCUMENT_NODES", 6)
    with pytest.raises(ContractError, match="node limit"):
        dumps_canonical([shared, shared])


def test_byte_limit_counts_utf8_and_escaped_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ser, "MAX_DOCUMENT_BYTES", 10)
    assert dumps_canonical({"a": "é"}) == b'{"a":"\xc3\xa9"}'
    for value in ({"a": "éé"}, {"a": "\x00"}, ["abc", "def"]):
        with pytest.raises(ContractError) as caught:
            dumps_canonical(value)
        assert caught.value.error_id == "input.limit_exceeded"
        assert caught.value.json_path == "$"
    for scalar in ("a" * 11, "é" * 6, 10**11, 2**41):
        with pytest.raises(ContractError) as member:
            dumps_canonical({"a": scalar})
        assert member.value.error_id == "input.limit_exceeded"
        assert member.value.json_path == "$.a"


def _guard_diagnostic_chunks(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    original = json.dumps
    chunks: list[int] = []

    def bounded_dumps(value: object, *, ensure_ascii: bool = True) -> str:
        assert type(value) is str
        assert len(value) <= 4096, "diagnostics must not escape an entire large key"
        chunks.append(len(value))
        return original(value, ensure_ascii=ensure_ascii)

    monkeypatch.setattr(json, "dumps", bounded_dumps)
    return chunks


@pytest.mark.parametrize("character", ["a", "\x00", "é"])
def test_oversized_keys_fail_at_the_containing_object_before_path_escaping(
    character: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Use the real 8 MiB limit: both oversized character count and UTF-8 size.
    key = character * (ser.MAX_DOCUMENT_BYTES // len(character.encode("utf-8")) + 1)
    chunks = _guard_diagnostic_chunks(monkeypatch)
    with pytest.raises(ContractError) as caught:
        dumps_canonical({"outer": {key: None}})
    assert caught.value.error_id == "input.limit_exceeded"
    assert caught.value.json_path == "$.outer"
    assert chunks == []


@pytest.mark.parametrize(
    ("character", "escape_size", "error_id"),
    [
        ("\x00", 6, "input.invalid_type"),
        ("\ud800", 6, "input.invalid_unicode"),
        ("\U0001f600", 12, "input.invalid_type"),
    ],
)
def test_large_escaped_key_diagnostics_keep_the_enclosing_path(
    character: str, escape_size: int, error_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = character * (ser.MAX_DOCUMENT_BYTES // escape_size + 1)
    chunks = _guard_diagnostic_chunks(monkeypatch)
    with pytest.raises(ContractError) as caught:
        dumps_canonical({"outer": {key: {"nested": [object()]}}})
    assert caught.value.error_id == error_id
    # Descendants must not append misleading names/indexes after an omitted key.
    assert caught.value.json_path == "$.outer"
    assert len(chunks) > 1
    if character == "\x00":
        with pytest.raises(ContractError) as output_error:
            dumps_canonical({key: None})
        assert output_error.value.error_id == "input.limit_exceeded"
        assert output_error.value.json_path == "$"


@pytest.mark.parametrize("character", ["a", "é", "\U0001f600"])
def test_legitimate_keys_near_eight_mib_keep_exact_bytes_without_rendering_paths(
    character: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    overhead = len(b'{"outer":{"":[0.0]}}')
    key = character * ((ser.MAX_DOCUMENT_BYTES - overhead) // len(character.encode("utf-8")))
    document = {"outer": {key: [0.0]}}
    expected = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert ser.MAX_DOCUMENT_BYTES - 4 < len(expected) <= ser.MAX_DOCUMENT_BYTES
    chunks = _guard_diagnostic_chunks(monkeypatch)
    assert dumps_canonical(document) == expected
    assert chunks == []
    assert document == {"outer": {key: [0.0]}}


@pytest.mark.parametrize("prefix_size", [4095, 4096, 4097])
def test_chunk_boundaries_preserve_standard_json_path_escaping(
    prefix_size: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = "x" * prefix_size + ('"\\\n\t\b\r\f\x00\x1f\x7fé\U0001f600' * 400)
    expected = f"$.outer[{json.dumps(key)}]"
    chunks = _guard_diagnostic_chunks(monkeypatch)
    with pytest.raises(ContractError) as caught:
        dumps_canonical({"outer": {key: object()}})
    assert caught.value.error_id == "input.invalid_type"
    assert caught.value.json_path == expected
    assert len(chunks) > 1


@pytest.mark.parametrize("extra", [-1, 0])
def test_path_budget_counts_utf8_prefix_and_accepts_the_exact_boundary(
    extra: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    outer, key = "ééé", "\U0001f600\U0001f600"
    expected = f"$.{outer}[{json.dumps(key)}]"
    byte_limit = len(expected.encode("utf-8")) + extra
    monkeypatch.setattr(ser, "MAX_DOCUMENT_BYTES", byte_limit)
    assert json.loads(dumps_canonical({outer: {key: 0}})) == {outer: {key: 0}}
    with pytest.raises(ContractError) as caught:
        dumps_canonical({outer: {key: object()}})
    assert caught.value.error_id == "input.invalid_type"
    assert caught.value.json_path == (f"$.{outer}" if extra < 0 else expected)


@pytest.mark.parametrize("extra", [2, 3])
def test_index_path_budget_retains_the_last_complete_ancestor(
    extra: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = "\U0001f600\U0001f600"
    expected = f"$[{json.dumps(key)}]"
    monkeypatch.setattr(ser, "MAX_DOCUMENT_BYTES", len(expected) + extra)
    assert json.loads(dumps_canonical({key: [[0]]})) == {key: [[0]]}
    with pytest.raises(ContractError) as caught:
        dumps_canonical({key: [[object()]]})
    assert caught.value.error_id == "input.invalid_type"
    assert caught.value.json_path == (expected + "[0]" if extra == 3 else expected)


def test_interpreter_integer_conversion_limit_is_not_changed() -> None:
    limit = sys.get_int_max_str_digits()
    if limit == 0:
        pytest.skip("interpreter decimal conversion limit is disabled")
    with pytest.raises(ContractError) as caught:
        dumps_canonical({"n": 10**limit})
    assert caught.value.error_id == "input.limit_exceeded"
    assert caught.value.json_path == "$.n"
    assert sys.get_int_max_str_digits() == limit


def test_repeated_strings_hit_the_byte_budget_before_the_node_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ser, "MAX_DOCUMENT_BYTES", 16)
    with pytest.raises(ContractError) as caught:
        dumps_canonical(["123456789"] * ser.MAX_DOCUMENT_NODES)
    assert caught.value.error_id == "input.limit_exceeded"
    assert caught.value.json_path == "$[1]"


def test_raw_hash_reads_bounded_chunks_without_the_document_size_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = bytes(range(256)) * (ser.MAX_DOCUMENT_BYTES // 256 + 1)
    reads: list[int] = []

    class BoundedRead(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            assert size is not None and 0 < size <= 1024 * 1024
            reads.append(size)
            return super().read(size)

    def open_binary(path: Path, mode: str) -> BoundedRead:
        assert mode == "rb"
        return BoundedRead(content)

    monkeypatch.setattr(Path, "open", open_binary)
    assert file_sha256("evidence.bin") == sha256(content).hexdigest()
    assert len(reads) > 8


def test_raw_hash_preserves_nonjson_bytes_and_io_errors(tmp_path: Path) -> None:
    path = tmp_path / "raw.bin"
    content = b'\xff\x00{"a":1,"a":2}\r\n'
    path.write_bytes(content)
    assert file_sha256(path) == sha256(content).hexdigest()
    assert path.read_bytes() == content
    with pytest.raises(FileNotFoundError):
        file_sha256(tmp_path / "missing")


def test_public_exports_do_not_add_a_document_digest() -> None:
    assert contracts.dumps_canonical is dumps_canonical
    assert contracts.file_sha256 is file_sha256
    assert "dumps_canonical" in contracts.__all__ and "file_sha256" in contracts.__all__
    assert not hasattr(contracts, "document_digest")
