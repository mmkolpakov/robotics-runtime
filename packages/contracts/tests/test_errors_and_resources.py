from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest
from jsonschema import Draft202012Validator

import robotics_runtime_contracts as contracts
from robotics_runtime_contracts import ContractError, load_mapping
from robotics_runtime_contracts._qualification import QualificationError
from robotics_runtime_contracts._timestamps import parse_timestamp
from robotics_runtime_contracts.cli import CLIArgumentError, main
from robotics_runtime_contracts.document_ops import _resolve_property
from tests.test_cli import FIXTURE
from tests.test_extensions import SCHEMA_URI, extension_schema, scenario_with_extension


def test_all_exported_contract_errors_share_the_value_error_boundary() -> None:
    for name in contracts.__all__:
        value = getattr(contracts, name)
        if isinstance(value, type) and issubclass(value, Exception):
            assert issubclass(value, ContractError), name
            assert value.error_id
    for error_type in (QualificationError, CLIArgumentError):
        error = error_type("failure", json_path="$.item")
        assert isinstance(error, ValueError)
        assert isinstance(error, ContractError)
        assert error.error_id and error.json_path == "$.item"


@pytest.mark.parametrize("command", ["describe", "validate"])
@pytest.mark.parametrize("error_type", [KeyError, RuntimeError, TypeError, ValueError])
def test_cli_catches_unexpected_failures_in_dispatch_and_success_output(
    command: str,
    error_type: type[Exception],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(*args: Any, **kwargs: Any) -> None:
        raise error_type("injected defect")

    name = "describe_schema" if command == "describe" else "_emit"
    monkeypatch.setattr(f"robotics_runtime_contracts.cli.{name}", fail)
    argument = "acceptance-scenario.v1" if command == "describe" else str(FIXTURE)
    assert main(["--format=json", command, argument]) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err)["error"]["error_id"] == "internal.error"
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    "arguments",
    [
        ["validate", "-", "-"],
        ["validate", str(FIXTURE), "--extension-schema", "invalid"],
        ["validate-qualification", "--artifact", "invalid"],
    ],
)
def test_cli_argument_combinations_have_exit_two(
    arguments: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--format", "json", *arguments]) == 2
    assert json.loads(capsys.readouterr().err)["error"]["error_id"] == "cli.arguments_invalid"


def test_resolve_expands_home_for_inputs_outputs_and_trace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "base.yaml").write_bytes(FIXTURE.read_bytes())
    (tmp_path / "overlay.json").write_text('{"seed": 43}', encoding="utf-8")
    assert (
        main(
            [
                "scenario",
                "resolve",
                "~/base.yaml",
                "--overlay",
                "~/overlay.json",
                "--output",
                "~/resolved.json",
                "--trace-output",
                "~/trace.json",
            ]
        )
        == 0
    )
    output = tmp_path / "resolved.json"
    assert load_mapping(output)["seed"] == 43
    trace = load_mapping(tmp_path / "trace.json")
    assert trace["resolved_sha256"] == sha256(output.read_bytes()).hexdigest()
    assert Path(trace["resolved"]) == output
    assert not (tmp_path / "~").exists()
    capsys.readouterr()


def test_schema_validation_selects_the_relevant_anyof_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = Draft202012Validator(
        {
            "anyOf": [
                {"type": "object", "properties": {"n": {"type": "integer"}}},
                {"type": "array"},
            ]
        }
    )
    monkeypatch.setattr(contracts, "_validator", lambda _: validator)
    with pytest.raises(contracts.ContractValidationError) as caught:
        contracts.validate_document({"n": "wrong"}, "acceptance-scenario.v1")
    assert caught.value.error_id == "schema.validation_failed"
    assert caught.value.json_path == "$.n"
    assert "integer" in caught.value.validation_message


@pytest.mark.parametrize("reference", ["#/$defs/missing", "#missing-anchor", "#"])
def test_extension_reference_failures_are_contract_errors(
    reference: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scenario = scenario_with_extension()
    schema = json.loads(extension_schema())
    schema["properties"]["item_id"] = {"$ref": reference}
    if reference == "#":
        schema["$ref"] = "#"
    raw = json.dumps(schema).encode()
    declarations: Any = scenario["extension_schemas"]
    declarations[0]["sha256"] = sha256(raw).hexdigest()
    with pytest.raises(contracts.ExtensionValidationError) as caught:
        contracts.validate_document(scenario, extension_schemas={SCHEMA_URI: raw})
    assert caught.value.error_id == "extension.validation_failed"
    assert caught.value.json_path == "$.extension_schemas[0]"
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(scenario), encoding="utf-8")
    schema_path = tmp_path / "schema.json"
    schema_path.write_bytes(raw)
    assert (
        main(
            [
                "--format=json",
                "validate",
                str(path),
                "--extension-schema",
                f"{SCHEMA_URI}={schema_path}",
            ]
        )
        == 1
    )
    assert json.loads(capsys.readouterr().err)["error"]["error_id"] == "extension.validation_failed"


def test_property_lookup_understands_anchors_escaped_pointers_and_scoped_ids() -> None:
    schema: dict[str, Any] = {
        "$id": "https://example.org/root",
        "$defs": {
            "a/b~c": {"$anchor": "named", "type": "integer"},
            "nested": {
                "$id": "child",
                "$defs": {"value": {"type": "string"}},
                "$ref": "#/$defs/value",
            },
        },
    }
    assert _resolve_property({"$ref": "#named"}, current_schema=schema)["type"] == "integer"
    assert (
        _resolve_property({"$ref": "#/$defs/a~1b~0c"}, current_schema=schema)["type"] == "integer"
    )
    assert _resolve_property({"$ref": "child"}, current_schema=schema)["type"] == "string"


@pytest.mark.parametrize("reference", ["#absent", "#/$defs/absent", "#"])
def test_property_lookup_reports_missing_or_cyclic_references(reference: str) -> None:
    schema = {"$id": "https://example.org/root", "$ref": reference}
    with pytest.raises(ContractError) as caught:
        _resolve_property(schema, current_schema=schema)
    assert caught.value.error_id == "schema.reference_invalid"


@pytest.mark.parametrize(
    "value", ["2026-09-07T00:00:00Z", "2026-09-07t00:00:00z", "2026-09-07T03:00:00+03:00"]
)
def test_common_timestamp_parser_compares_offsets(value: str) -> None:
    assert parse_timestamp(value) == datetime(2026, 9, 7, tzinfo=UTC)


@pytest.mark.parametrize("value", ["bad", "2026-09-07T00:00:00"])
def test_common_timestamp_parser_has_structured_errors(value: str) -> None:
    with pytest.raises(ContractError) as caught:
        parse_timestamp(value, json_path="$.created_at")
    assert caught.value.error_id == "input.invalid_timestamp"
    assert caught.value.json_path == "$.created_at"


def test_schema_paths_survive_zip_import_until_process_exit(tmp_path: Path) -> None:
    source = Path(contracts.__file__).parent
    archive_path = tmp_path / "contracts.zip"
    with ZipFile(archive_path, "w") as archive:
        for path in source.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, Path(source.name) / path.relative_to(source))
    script = """
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import robotics_runtime_contracts as c
assert sys.argv[1] in c.__file__
directory = c.schema_dir()
assert isinstance(directory, Path) and directory.is_dir()
paths = {name: c.schema_path(name) for name in c.schema_resource_names()}
for name, path in paths.items():
    assert path.is_file() and path.parent == directory
    assert c.load_schema(name)["$id"]
print(json.dumps({"directory": str(directory), "digests": {
    name: c.schema_digest(name) for name in paths
}}))
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(archive_path)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["digests"] == {
        name: contracts.schema_digest(name) for name in contracts.schema_resource_names()
    }
    assert not Path(payload["directory"]).exists()
