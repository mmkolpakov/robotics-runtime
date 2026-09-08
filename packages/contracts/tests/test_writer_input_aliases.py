"""Extension-schema inputs survive every producer and output-alias form."""

import os
from pathlib import Path

import pytest

from robotics_runtime_contracts import load_mapping
from robotics_runtime_contracts.cli import main
from robotics_runtime_contracts.writers import (
    add_evidence_artifact,
    create_evidence_index,
    write_evidence_draft,
)
from tests.support import qualification_specifications
from tests.test_recording_writer import recording
from tests.test_writers import EXAMPLE, artifact_metadata, index_template, json_file


def commands(directory: Path) -> dict[str, list[str]]:
    source = json_file(directory / "observation.json", {"value": 1})
    draft = add_evidence_artifact(
        create_evidence_index(index_template()), source, artifact_metadata()
    )
    draft_path = write_evidence_draft(draft, directory / "draft.json")
    metadata = artifact_metadata()
    metadata["artifact_id"] = "second-observation"
    metadata_path = json_file(directory / "metadata.json", metadata)
    scenario_args = [
        part for spec in qualification_specifications("transport") for part in ("--artifact", spec)
    ]
    return {
        "runtime": [
            "runtime-manifest",
            "init",
            "--template",
            str(EXAMPLE / "runtime-manifest.yaml"),
        ],
        "init": [
            "evidence-index",
            "init",
            "--template",
            str(json_file(directory / "template.json", index_template())),
        ],
        "add": [
            "evidence-index",
            "add-artifact",
            str(draft_path),
            "--source",
            str(source),
            "--metadata",
            str(metadata_path),
        ],
        "finalize": ["evidence-index", "finalize", str(draft_path)],
        "recording": ["recording-summary", "from-mcap", str(recording(directory / "input.mcap"))],
        "statement": ["qualification", "statement", *scenario_args],
    }


@pytest.mark.parametrize(
    "command", ["runtime", "init", "add", "finalize", "recording", "statement"]
)
@pytest.mark.parametrize("alias", ["same", "relative", "hardlink"])
def test_every_writer_preserves_extension_input_alias(
    tmp_path: Path, command: str, alias: str, capsys: pytest.CaptureFixture[str]
) -> None:
    arguments = commands(tmp_path)[command]
    extension = json_file(tmp_path / "extension.json", {"type": "object"})
    original = extension.read_bytes()
    output = extension
    if alias == "relative":
        directory = tmp_path / "nested"
        directory.mkdir()
        output = directory / ".." / extension.name
    elif alias == "hardlink":
        output = tmp_path / "alias.json"
        os.link(extension, output)
    arguments.extend(
        ["--output", str(output), "--extension-schema", f"https://example.org/schema={extension}"]
    )
    assert main(["--format", "json", *arguments]) == 1
    assert '"error_id": "writer.invalid_input"' in capsys.readouterr().err
    assert extension.read_bytes() == output.read_bytes() == original


def test_default_in_place_add_protects_extension_input(tmp_path: Path) -> None:
    arguments = commands(tmp_path)["add"]
    draft_path = Path(arguments[2])
    original = draft_path.read_bytes()
    arguments.extend(["--extension-schema", f"https://example.org/schema={draft_path}"])
    assert main(arguments) == 1
    assert draft_path.read_bytes() == original
    assert load_mapping(draft_path)["index"]["artifacts"][0]["artifact_id"] == "observation-1"
