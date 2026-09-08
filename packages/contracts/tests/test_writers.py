from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from robotics_runtime_contracts import (
    ContractError,
    dumps_canonical,
    file_sha256,
    load_mapping,
    validate_document,
)
from robotics_runtime_contracts.cli import main
from robotics_runtime_contracts.writers import (
    WriterError,
    add_evidence_artifact,
    create_evidence_index,
    create_runtime_manifest,
    finalize_evidence_index,
    write_document,
    write_evidence_draft,
)

EXAMPLE = Path(__file__).parents[1] / "consumer-examples/minimal-simulation"


def index_template() -> dict[str, Any]:
    template = load_mapping(EXAMPLE / "evidence-index.yaml")
    del template["artifacts"], template["finalized"]
    return template


def artifact_metadata() -> dict[str, Any]:
    return {
        "artifact_id": "observation-1",
        "kind": "observation",
        "media_type": "application/json",
        "retention_class": "pull-request-7d",
        "storage_state": "local",
        "segment_index": 0,
    }


def json_file(path: Path, document: object) -> Path:
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_runtime_template_is_validated_without_inventing_observations(tmp_path: Path) -> None:
    template = load_mapping(EXAMPLE / "runtime-manifest.yaml")
    before = deepcopy(template)
    result = create_runtime_manifest(template)
    assert result == before
    result["ros"]["distribution"] = "changed"
    assert template == before
    del template["clock"]
    output = tmp_path / "runtime.json"
    output.write_bytes(b"previous output")
    invalid = json_file(tmp_path / "invalid.json", template)
    assert (
        main(["runtime-manifest", "init", "--template", str(invalid), "--output", str(output)]) == 1
    )
    assert output.read_bytes() == b"previous output"


def test_atomic_writer_preserves_existing_output_on_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = create_runtime_manifest(load_mapping(EXAMPLE / "runtime-manifest.yaml"))
    destination = tmp_path / "runtime.json"
    destination.write_bytes(b"existing")

    def fail_replace(_source: object, _destination: object) -> None:
        raise OSError("replacement failed")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="replacement failed"):
        write_document(document, destination)
    assert destination.read_bytes() == b"existing"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["runtime.json"]


def test_draft_is_distinct_from_a_public_finalized_index() -> None:
    draft = create_evidence_index(index_template())
    assert draft["index"]["artifacts"] == []
    assert draft["index"]["finalized"] is False
    with pytest.raises(ContractError):
        validate_document(draft)
    with pytest.raises(ContractError):
        finalize_evidence_index(draft)


def test_artifact_hash_is_of_original_bytes_and_finalize_rechecks_them(tmp_path: Path) -> None:
    source = tmp_path / "observation.json"
    source.write_bytes(b'{ "value": 1 }\r\n')
    draft = create_evidence_index(index_template())
    added = add_evidence_artifact(draft, source, artifact_metadata())
    assert draft["index"]["artifacts"] == []
    result = finalize_evidence_index(added)
    artifact = result["artifacts"][0]
    assert artifact["sha256"] == file_sha256(source)
    assert artifact["size_bytes"] == len(source.read_bytes())
    assert artifact["uri"] == source.as_uri()
    assert result["policy_observation"] == index_template()["policy_observation"]
    validate_document(result)
    source.write_bytes(b'{"value":1}')  # Same JSON value, different artifact bytes.
    with pytest.raises(WriterError, match="sha256"):
        finalize_evidence_index(added)


@pytest.mark.parametrize(
    "field,value", [("sha256", "0" * 64), ("size_bytes", 999), ("size_bytes", True)]
)
def test_artifact_rejects_claimed_facts_that_disagree_with_source(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    source = json_file(tmp_path / "observation.json", {"value": 1})
    metadata = artifact_metadata()
    metadata[field] = value
    with pytest.raises(WriterError, match=field):
        add_evidence_artifact(create_evidence_index(index_template()), source, metadata)


def test_duplicate_artifact_and_forged_uri_do_not_finalize(tmp_path: Path) -> None:
    source = json_file(tmp_path / "observation.json", {"value": 1})
    draft = add_evidence_artifact(
        create_evidence_index(index_template()), source, artifact_metadata()
    )
    before = deepcopy(draft)
    with pytest.raises(ContractError, match="unique"):
        add_evidence_artifact(draft, source, artifact_metadata())
    assert draft == before
    draft["index"]["artifacts"][0]["uri"] = (tmp_path / "different.json").as_uri()
    with pytest.raises(WriterError, match="uri"):
        finalize_evidence_index(draft)


def test_draft_output_cannot_overwrite_its_artifact(tmp_path: Path) -> None:
    source = json_file(tmp_path / "observation.json", {"value": 1})
    original = source.read_bytes()
    draft = add_evidence_artifact(
        create_evidence_index(index_template()), source, artifact_metadata()
    )
    with pytest.raises(WriterError, match="must not replace"):
        write_evidence_draft(draft, source)
    assert source.read_bytes() == original


def test_retained_metadata_is_explicit_and_not_inferred(tmp_path: Path) -> None:
    source = json_file(tmp_path / "observation.json", {"value": 1})
    metadata = artifact_metadata()
    metadata["storage_state"] = "retained"
    metadata["uri"] = "s3://example/evidence/object"
    draft = create_evidence_index(index_template())
    with pytest.raises(ContractError):
        add_evidence_artifact(draft, source, metadata)
    metadata.update(immutable_revision="object-version-1", receipt_sha256="b" * 64)
    result = finalize_evidence_index(add_evidence_artifact(draft, source, metadata))
    assert result["artifacts"][0]["sha256"] == file_sha256(source)


def test_consumer_runtime_and_evidence_are_generated_by_cli(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime.json"
    assert (
        main(
            [
                "runtime-manifest",
                "init",
                "--template",
                str(EXAMPLE / "runtime-manifest.yaml"),
                "--output",
                str(runtime),
            ]
        )
        == 0
    )
    assert runtime.read_bytes() == dumps_canonical(load_mapping(EXAMPLE / "runtime-manifest.yaml"))
    template = json_file(tmp_path / "index-template.json", index_template())
    metadata = json_file(tmp_path / "artifact.json", artifact_metadata())
    source = tmp_path / "observed data.json"
    source.write_bytes((EXAMPLE / "evidence/time-authority.json").read_bytes())
    draft = tmp_path / "draft.json"
    output = tmp_path / "index.json"
    assert (
        main(["evidence-index", "init", "--template", str(template), "--output", str(draft)]) == 0
    )
    assert (
        main(
            [
                "evidence-index",
                "add-artifact",
                str(draft),
                "--source",
                str(source),
                "--metadata",
                str(metadata),
            ]
        )
        == 0
    )
    assert main(["evidence-index", "finalize", str(draft), "--output", str(output)]) == 0
    validate_document(load_mapping(runtime))
    validate_document(load_mapping(output))
    assert load_mapping(output)["artifacts"][0]["sha256"] == file_sha256(source)
    previous = output.read_bytes()
    source.write_bytes(b"changed")
    assert main(["evidence-index", "finalize", str(draft), "--output", str(output)]) == 1
    assert output.read_bytes() == previous


def test_missing_cli_inputs_and_alias_output_are_rejected(tmp_path: Path) -> None:
    assert main(["runtime-manifest", "init"]) == 2
    template = json_file(tmp_path / "runtime.json", load_mapping(EXAMPLE / "runtime-manifest.yaml"))
    original = template.read_bytes()
    assert (
        main(["runtime-manifest", "init", "--template", str(template), "--output", str(template)])
        == 1
    )
    assert template.read_bytes() == original
