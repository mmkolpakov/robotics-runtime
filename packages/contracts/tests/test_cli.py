from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
import yaml

from robotics_runtime_contracts import validate_document
from robotics_runtime_contracts.cli import main
from robotics_runtime_contracts.qualification import validate_qualification_artifacts
from tests.support import qualification_specifications

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE = FIXTURES / "scenario" / "valid" / "simulation-realtime.yaml"


def test_cli_validates_yaml_document(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(FIXTURE)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "valid: acceptance-scenario.v1\n"
    assert captured.err == ""


def test_cli_reports_contract_path_for_invalid_document(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    document = tmp_path / "invalid.yaml"
    document.write_text(
        "schema_version: acceptance-scenario.v1\nunknown: true\n",
        encoding="utf-8",
    )

    assert main(["validate", str(document)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid: $" in captured.err


def test_cli_json_errors_have_stable_ids(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    document = tmp_path / "invalid.yaml"
    document.write_text("schema_version: acceptance-scenario.invalid\n", encoding="utf-8")

    assert main(["--format", "json", "validate", str(document)]) == 1

    error = json.loads(capsys.readouterr().err)["error"]
    assert error["error_id"] == "schema.unknown"
    assert error["message"].startswith("Unknown schema")


def test_cli_quiet_mode_has_no_success_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", "--quiet", str(FIXTURE)]) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_cli_validates_multiple_documents_in_one_process(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["validate", "--quiet", str(FIXTURE), str(FIXTURE)]) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_cli_rejects_schema_override_for_a_batch(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        main(
            [
                "validate",
                "--schema",
                "acceptance-scenario.v1",
                str(FIXTURE),
                str(FIXTURE),
            ]
        )
        == 2
    )

    captured = capsys.readouterr()
    assert "--schema requires exactly one document" in captured.err


def test_cli_rejects_an_incomplete_qualification_artifact_set(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        main(
            [
                "validate-qualification",
                "--artifact",
                f"scenario:scenario.json={FIXTURE}",
                "--quiet",
            ]
        )
        == 1
    )

    captured = capsys.readouterr()
    assert "requires exactly one acceptance_run" in captured.err


def test_cli_validates_a_complete_qualification_and_writes_exact_metadata(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    specifications = qualification_specifications("transport")
    artifacts = [
        value for specification in specifications for value in ("--artifact", specification)
    ]
    output = tmp_path / "validated-artifacts.json"

    assert main(["validate-qualification", *artifacts, "--quiet", "--output", str(output)]) == 0

    metadata = json.loads(output.read_text(encoding="utf-8"))
    assert metadata["run_id"] == "run-00000000-0000-4000-8000-000000000001"
    assert {item["subject_name"]: item["sha256"] for item in metadata["artifacts"]} == {
        specification.partition(":")[2].partition("=")[0]: hashlib.sha256(
            Path(specification.partition("=")[2]).read_bytes()
        ).hexdigest()
        for specification in specifications
    }
    assert capsys.readouterr().out == ""


def test_cli_rejects_a_noncanonical_qualification_subject(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        main(
            [
                "validate-qualification",
                "--artifact",
                f"scenario:../scenario.json={FIXTURE}",
                "--quiet",
            ]
        )
        == 2
    )

    assert "non-canonical qualification subject name" in capsys.readouterr().err


def test_cli_schema_override_reports_the_resolved_schema_without_root_version(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    metadata = validate_qualification_artifacts(qualification_specifications("inference"))
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {"name": item["subject_name"], "digest": {"sha256": item["sha256"]}}
            for item in metadata["artifacts"]
        ],
        "predicateType": (
            "https://robotics-runtime-contracts.dev/attestations/qualification-bundle/v1"
        ),
        "predicate": {
            "schema_version": "qualification-bundle.v1",
            "run_id": metadata["run_id"],
            "generated_at": metadata["generated_at"],
            "artifacts": [
                {"kind": item["kind"], "subject_name": item["subject_name"]}
                for item in metadata["artifacts"]
            ],
        },
    }
    path = tmp_path / "qualification-bundle.json"
    path.write_text(json.dumps(statement), encoding="utf-8")

    assert main(["validate", "--schema", "qualification-bundle.v1", str(path)]) == 0
    assert capsys.readouterr().out == "valid: qualification-bundle.v1\n"


def test_cli_describes_diffs_and_resolves_scenario_overlays(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["describe", "acceptance-scenario.v1"]) == 0
    description = json.loads(capsys.readouterr().out)
    assert description["schema"] == "acceptance-scenario.v1"
    assert len(description["sha256"]) == 64
    assert description["properties"]["scenario_id"]["type"] == "string"

    target = tmp_path / "target.yaml"
    target.write_text(
        FIXTURE.read_text(encoding="utf-8").replace("seed: 42", "seed: 43"),
        encoding="utf-8",
    )
    assert main(["diff", str(FIXTURE), str(target)]) == 0
    assert json.loads(capsys.readouterr().out) == {"seed": 43}

    overlay = tmp_path / "overlay.yaml"
    overlay.write_text("seed: 43\n", encoding="utf-8")
    resolved = tmp_path / "resolved.yaml"
    trace = tmp_path / "trace.json"
    assert (
        main(
            [
                "scenario",
                "resolve",
                str(FIXTURE),
                "--overlay",
                str(overlay),
                "--output",
                str(resolved),
                "--trace-output",
                str(trace),
            ]
        )
        == 0
    )
    assert yaml.safe_load(resolved.read_text(encoding="utf-8"))["seed"] == 43
    assert json.loads(trace.read_text(encoding="utf-8"))["resolved_sha256"]
    capsys.readouterr()


def test_cli_rejects_destructive_resolve_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    overlay = tmp_path / "overlay.yaml"
    overlay.write_text("seed: 43\n", encoding="utf-8")
    original = overlay.read_bytes()

    assert (
        main(
            [
                "scenario",
                "resolve",
                str(FIXTURE),
                "--overlay",
                str(overlay),
                "--output",
                str(overlay),
            ]
        )
        == 2
    )
    assert overlay.read_bytes() == original
    assert "must not overwrite" in capsys.readouterr().err

    output = tmp_path / "combined.json"
    assert (
        main(
            [
                "scenario",
                "resolve",
                str(FIXTURE),
                "--overlay",
                str(overlay),
                "--output",
                str(output),
                "--trace-output",
                str(output),
            ]
        )
        == 2
    )
    assert not output.exists()


def test_cli_rejects_unrepresentable_rfc7396_diff(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source.json"
    target = tmp_path / "target.json"
    source.write_text('{"value": 1}\n', encoding="utf-8")
    target.write_text('{"value": null}\n', encoding="utf-8")

    assert main(["diff", str(source), str(target)]) == 1
    assert "null denotes member removal" in capsys.readouterr().err


def test_cli_reports_argument_errors_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--format", "json", "validate"]) == 2

    payload = json.loads(capsys.readouterr().err)
    assert payload["error"]["error_id"] == "cli.arguments_invalid"


def test_cli_creates_a_valid_unsigned_permit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "permit.json"
    digest = "a" * 64
    assert (
        main(
            [
                "permit",
                "init",
                "--scenario-sha256",
                digest,
                "--subject-digest",
                f"sha256:{digest}",
                "--trust-policy-sha256",
                digest,
                "--environment",
                "hil",
                "--target-id",
                "controller-alpha",
                "--identity-kind",
                "udev_serial",
                "--identity-sha256",
                digest,
                "--hardware-scope",
                "controller",
                "--operator-id",
                "operator@example.org",
                "--approver-id",
                "approver@example.org",
                "--interlock-reference",
                "https://example.org/interlock/1",
                "--interlock-sha256",
                digest,
                "--output",
                str(output),
            ]
        )
        == 0
    )
    permit = json.loads(output.read_text(encoding="utf-8"))
    validate_document(permit)
    assert permit["allowed_physical_effect"] == "none"
    capsys.readouterr()


@pytest.mark.parametrize("output_name", ["source.json", "target.json"])
def test_cli_diff_output_cannot_replace_an_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    output_name: str,
) -> None:
    source = tmp_path / "source.json"
    target = tmp_path / "target.json"
    source.write_text('{"value": 1}\n', encoding="utf-8")
    target.write_text('{"value": 2}\n', encoding="utf-8")
    originals = {path: path.read_bytes() for path in (source, target)}

    arguments = ["diff", str(source), str(target), "--output", str(tmp_path / output_name)]

    assert main(arguments) == 2
    assert {path: path.read_bytes() for path in originals} == originals
    assert "diff outputs must not overwrite an input document" in capsys.readouterr().err


@pytest.mark.parametrize("link", ["hard", "symbolic"])
def test_cli_resolve_rejects_an_output_linked_to_the_base(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    link: str,
) -> None:
    base = tmp_path / "base.yaml"
    base.write_bytes(FIXTURE.read_bytes())
    overlay = tmp_path / "overlay.yaml"
    overlay.write_text("seed: 43\n", encoding="utf-8")
    output = tmp_path / "resolved.yaml"
    if link == "hard":
        os.link(base, output)
    else:
        output.symlink_to(base)
    original = base.read_bytes()

    arguments = ["scenario", "resolve", str(base), "--overlay", str(overlay)]

    assert main([*arguments, "--output", str(output)]) == 2
    assert base.read_bytes() == original
    assert "must not overwrite an input document" in capsys.readouterr().err


def test_cli_document_output_is_replaced_atomically(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source.json"
    target = tmp_path / "target.json"
    source.write_text('{"value": 1}\n', encoding="utf-8")
    target.write_text('{"value": 2}\n', encoding="utf-8")
    output = tmp_path / "patch.json"
    previous = tmp_path / "previous.json"
    output.write_text("{}\n", encoding="utf-8")
    os.link(output, previous)

    assert main(["diff", str(source), str(target), "--output", str(output)]) == 0

    assert json.loads(output.read_text(encoding="utf-8")) == {"value": 2}
    assert previous.read_text(encoding="utf-8") == "{}\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "patch.json",
        "previous.json",
        "source.json",
        "target.json",
    ]
    capsys.readouterr()


def test_cli_outputs_follow_symlinks_and_get_regular_modes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source.json"
    target = tmp_path / "target.json"
    source.write_text('{"value": 1}\n', encoding="utf-8")
    target.write_text('{"value": 2}\n', encoding="utf-8")
    shared = tmp_path / "shared"
    shared.mkdir()
    real = shared / "patch.json"
    real.write_text("{}\n", encoding="utf-8")
    link = tmp_path / "patch.json"
    link.symlink_to(real)
    previous = os.umask(0o022)
    try:
        assert main(["diff", str(source), str(target), "--output", str(link)]) == 0
    finally:
        os.umask(previous)

    assert link.is_symlink()
    assert json.loads(real.read_text(encoding="utf-8")) == {"value": 2}
    assert real.stat().st_mode & 0o777 == 0o644
    capsys.readouterr()


def test_cli_resolve_leaves_outputs_untouched_when_the_trace_path_is_a_directory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    overlay = tmp_path / "overlay.yaml"
    overlay.write_text("seed: 43\n", encoding="utf-8")
    output = tmp_path / "resolved.json"
    output.write_text("previous\n", encoding="utf-8")
    trace = tmp_path / "trace"
    trace.mkdir()

    arguments = ["scenario", "resolve", str(FIXTURE), "--overlay", str(overlay)]

    assert main([*arguments, "--output", str(output), "--trace-output", str(trace)]) == 1
    assert output.read_text(encoding="utf-8") == "previous\n"
    assert "output is a directory" in capsys.readouterr().err


def test_cli_resolve_output_cannot_replace_an_extension_schema(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    overlay = tmp_path / "overlay.yaml"
    overlay.write_text("seed: 43\n", encoding="utf-8")
    schema = tmp_path / "extension.schema.json"
    schema.write_text('{"type": "object"}\n', encoding="utf-8")
    original = schema.read_bytes()
    arguments = ["scenario", "resolve", str(FIXTURE), "--overlay", str(overlay)]
    extension = ["--extension-schema", f"https://example.org/ext.json={schema}"]

    assert main([*arguments, *extension, "--output", str(schema)]) == 2

    assert schema.read_bytes() == original
    assert "must not overwrite an input document" in capsys.readouterr().err
