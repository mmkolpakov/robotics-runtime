from __future__ import annotations

import io
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
import yaml

from robotics_runtime_contracts import (
    DocumentParseError,
    ExtensionValidationError,
    NonFiniteNumberError,
    load_mapping,
    loads_mapping,
    validate_document,
)
from robotics_runtime_contracts import serialization as ser
from robotics_runtime_contracts.cli import _write_document, main
from robotics_runtime_contracts.qualification import QualificationError, load_qualification_artifact
from tests.test_extensions import SCHEMA_URI, extension_schema, scenario_with_extension


@pytest.mark.parametrize(
    "text",
    [
        "yes",
        "no",
        "on",
        "off",
        "YES",
        "Off",
        "1:30",
        "0b10",
        "1_000",
        "2024-01-01",
        "2024-01-01T00:00:00Z",
    ],
)
def test_yaml_11_implicit_values_remain_strings(text: str) -> None:
    assert loads_mapping(f"value: {text}\n") == {"value": text}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("True", True),
        ("FALSE", False),
        ("null", None),
        ("~", None),
        ("", None),
        ("010", 10),
        ("+010", 10),
        ("-010", -10),
        ("0o10", 8),
        ("0x1f", 31),
        ("1.10", 1.1),
        ("1e2", 100.0),
        (".5", 0.5),
        ("0.", 0.0),
    ],
)
def test_yaml_12_core_scalar_types(text: str, expected: Any) -> None:
    value = loads_mapping(f"value: {text}\n")["value"]
    assert type(value) is type(expected)
    assert value == expected


def test_core_loader_does_not_change_host_pyyaml_behavior() -> None:
    assert loads_mapping("flag: yes\n")["flag"] == "yes"
    assert yaml.safe_load("flag: yes\n")["flag"] is True


def test_yaml_writer_preserves_core_ambiguous_strings_and_emits_no_aliases(tmp_path: Path) -> None:
    shared = {"x": ["0o10", "1e2", "true", "null", "yes", "1:30", "2024-01-01"]}
    document = {"a": shared, "b": shared}
    path = _write_document(tmp_path / "document.yaml", document)
    assert load_mapping(path) == document
    assert load_mapping(path)["a"]["x"][0] == "0o10"


@pytest.mark.parametrize(
    "value",
    [
        "!!timestamp 2024-01-01",
        "!!bool yes",
        "!!int 1:30",
        "!!int 0b11",
        "!!float 1_000",
        "!!binary aGVsbG8=",
        "!!set {a: null}",
        "!custom text",
        "!<str> text",
    ],
)
def test_non_core_or_invalid_explicit_tags_are_rejected(value: str) -> None:
    with pytest.raises(DocumentParseError) as caught:
        loads_mapping(f"value: {value}\n")
    assert caught.value.error_id == "input.parse_failed"
    assert caught.value.json_path == "$.value"


def test_explicit_core_tags_and_literal_merge_key() -> None:
    assert loads_mapping("a: !!str true\nb: !!int 010\nc: {<<: {x: 1}}\n") == {
        "a": "true",
        "b": 10,
        "c": {"<<": {"x": 1}},
    }


@pytest.mark.parametrize(
    "source", ["a: &a [*a]\n", "a: &a {x: 1}\nb: *a\n", "a: &a {x: 1}\nb: {<<: *a}\n"]
)
def test_aliases_are_rejected_before_expansion(source: str) -> None:
    with pytest.raises(DocumentParseError) as caught:
        loads_mapping(source)
    assert caught.value.error_id == "input.yaml_alias"


@pytest.mark.parametrize("source", ['{"a": 1, "a": 2}', '{"a": 1, "\\u0061": 2}', "a: 1\na: 2\n"])
def test_duplicate_keys_are_rejected(source: str) -> None:
    with pytest.raises(DocumentParseError) as caught:
        loads_mapping(source)
    assert caught.value.error_id == "input.duplicate_key"
    assert caught.value.json_path == "$.a"


@pytest.mark.parametrize("source", ['{"x": [{"a.b": 1, "a.b": 2}]}', "x:\n- {a.b: 1, a.b: 2}\n"])
def test_nested_duplicates_have_unambiguous_paths(source: str) -> None:
    with pytest.raises(DocumentParseError) as caught:
        loads_mapping(
            source, source_name="document.yaml" if source.startswith("x:") else "document.json"
        )
    assert caught.value.json_path == '$.x[0]["a.b"]'


@pytest.mark.parametrize("source", ["yes: 1\ntrue: 2\n", "1: value\n", "? [a, b]\n: value\n"])
def test_yaml_mapping_keys_must_be_json_strings(source: str) -> None:
    with pytest.raises(DocumentParseError, match="keys must be strings"):
        loads_mapping(source)


@pytest.mark.parametrize("source", ['{"a": 1,}', "a: 1", "{a: 1}", "{'a': 1}"])
def test_json_never_falls_back_to_yaml(source: str, tmp_path: Path) -> None:
    path = tmp_path / "invalid.JSON"
    path.write_text(source, encoding="utf-8")
    with pytest.raises(DocumentParseError):
        load_mapping(path)


@pytest.mark.parametrize(
    "source",
    [
        b'{"value": NaN}',
        b'{"value": Infinity}',
        b'{"value": -Infinity}',
        b'{"value": 1e999}',
        b"value: .inf",
        b"value: -.Inf",
        b"value: .NAN",
        b"value: 1e999",
    ],
)
def test_nonfinite_numbers_are_rejected_with_a_path(source: bytes) -> None:
    with pytest.raises(NonFiniteNumberError) as caught:
        loads_mapping(source)
    assert caught.value.error_id == "input.non_finite_number"
    assert caught.value.json_path == "$.value"


@pytest.mark.parametrize("source", [b"value: \xff", b"[1, 2]", b"null", b"a: 1\n---\nb: 2"])
def test_bad_encoding_roots_and_multiple_documents(source: bytes) -> None:
    with pytest.raises(DocumentParseError):
        loads_mapping(source)


def test_document_byte_limit_is_utf8_and_checked_before_parsing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ser, "MAX_DOCUMENT_BYTES", 10)
    assert loads_mapping('{"a": 1}  ') == {"a": 1}
    for source in ('{"a": 1}   ', '{"a":"éé"}', b'{"a": 1}   '):
        with pytest.raises(DocumentParseError) as caught:
            loads_mapping(source)
        assert caught.value.error_id == "input.limit_exceeded"
    path = tmp_path / "large.json"
    path.write_bytes(b" " * 1000)
    with pytest.raises(DocumentParseError, match="10 UTF-8 bytes"):
        load_mapping(path)
    stream = io.BytesIO(b" " * 1000)
    with pytest.raises(DocumentParseError):
        ser.read_document_stream(stream)
    assert stream.tell() == 11


@pytest.mark.parametrize("suffix", ["json", "yaml"])
def test_nesting_and_node_limits_have_acceptance_boundaries(
    suffix: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ser, "MAX_DOCUMENT_DEPTH", 3)
    name = f"document.{suffix}"
    assert loads_mapping('{"a": {"b": 1}}', source_name=name) == {"a": {"b": 1}}
    with pytest.raises(DocumentParseError) as caught:
        loads_mapping('{"a": {"b": {"c": 1}}}', source_name=name)
    assert caught.value.error_id == "input.limit_exceeded"
    monkeypatch.setattr(ser, "MAX_DOCUMENT_NODES", 3)
    assert loads_mapping('{"a": 1}', source_name=name) == {"a": 1}
    with pytest.raises(DocumentParseError) as caught:
        loads_mapping('{"a": 1, "b": 2}', source_name=name)
    assert caught.value.error_id == "input.limit_exceeded"


@pytest.mark.parametrize("suffix", ["json", "yaml"])
def test_adversarial_deep_input_does_not_escape_as_recursion_error(suffix: str) -> None:
    source = '{"a":' * 1500 + "0" + "}" * 1500
    with pytest.raises(DocumentParseError) as caught:
        loads_mapping(source, source_name=f"document.{suffix}")
    assert caught.value.error_id == "input.limit_exceeded"


def test_cli_diff_of_unquoted_yaml_timestamps(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "a.yaml"
    target = tmp_path / "b.yaml"
    source.write_text("created_at: 2024-01-01T00:00:00Z\n", encoding="utf-8")
    target.write_text("created_at: 2024-01-02T00:00:00Z\n", encoding="utf-8")
    assert main(["diff", str(source), str(target)]) == 0
    captured = capsys.readouterr()
    assert not captured.err
    assert json.loads(captured.out) == {"created_at": "2024-01-02T00:00:00Z"}


def test_qualification_preserves_parse_diagnostics(tmp_path: Path) -> None:
    path = tmp_path / "scenario.json"
    path.write_text('{"schema_version": "x", "schema_version": "y"}', encoding="utf-8")
    with pytest.raises(QualificationError) as caught:
        load_qualification_artifact(f"scenario:scenario.json={path}", {})
    assert caught.value.error_id == "input.duplicate_key"
    assert caught.value.json_path == "$.schema_version"


def test_digest_pinned_extension_schemas_use_strict_json() -> None:
    scenario = scenario_with_extension()
    raw = extension_schema()[:-1] + b',"type":"array"}'
    declarations: Any = scenario["extension_schemas"]
    declarations[0]["sha256"] = sha256(raw).hexdigest()
    with pytest.raises(ExtensionValidationError, match="duplicate object key") as caught:
        validate_document(scenario, extension_schemas={SCHEMA_URI: raw})
    assert caught.value.json_path == "$.extension_schemas[0]"
