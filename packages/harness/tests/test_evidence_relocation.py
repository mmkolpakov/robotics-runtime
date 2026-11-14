from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from robotics_acceptance_harness import _evidence_files
from robotics_acceptance_harness.evidence import EvidenceValidationError, load_evidence_index
from tests.support import local_evidence_artifact, local_recording_artifact, write_evidence_index

RUN_ID = "run-01234567-89ab-4def-8123-456789abcdef"


def archive(
    tmp_path: Path, name: str = "payload.bin", *, recording: bool = False
) -> tuple[Path, Path, Path, Path]:
    original = tmp_path / "original"
    original.mkdir()
    payload = original / "nested" / name
    payload.parent.mkdir()
    payload.write_bytes(b"original measured bytes")
    artifact = (
        local_recording_artifact(payload, topics={"/clock": "rosgraph_msgs/msg/Clock"})
        if recording
        else local_evidence_artifact(payload)
    )
    index = write_evidence_index(original / "index.json", run_id=RUN_ID, artifacts=[artifact])
    copied = tmp_path / "copied"
    shutil.copytree(original, copied)
    return original, copied, index, payload


@pytest.mark.parametrize("name", ["payload.bin", "space name.bin", "percent%2F.bin", "данные.bin"])
def test_relocated_evidence_preserves_identity_without_original_files(
    tmp_path: Path, name: str
) -> None:
    original, copied, index, payload = archive(tmp_path, name)
    raw = index.read_bytes()
    shutil.rmtree(original)
    verified = load_evidence_index(copied / index.name, evidence_origin_root=original)
    actual = copied / payload.relative_to(original)
    assert tuple(verified.local_files) == (actual,)
    assert verified.read_local(actual) == b"original measured bytes"
    assert verified.links[0]["uri"] == payload.as_uri()
    assert (copied / index.name).read_bytes() == raw


@pytest.mark.parametrize("failure", ["missing", "tampered", "leaf-link", "directory-link", "fifo"])
def test_relocated_failures_never_fall_back_to_valid_original(tmp_path: Path, failure: str) -> None:
    original, copied, index, payload = archive(tmp_path)
    actual = copied / payload.relative_to(original)
    if failure == "missing":
        actual.unlink()
    elif failure == "tampered":
        actual.write_bytes(b"x" * actual.stat().st_size)
    elif failure == "leaf-link":
        actual.unlink()
        actual.symlink_to(payload)
    elif failure == "directory-link":
        shutil.rmtree(actual.parent)
        actual.parent.symlink_to(payload.parent, target_is_directory=True)
    else:
        actual.unlink()
        os.mkfifo(actual)
    with pytest.raises(EvidenceValidationError):
        load_evidence_index(copied / index.name, evidence_origin_root=original)


def test_relocated_reopen_rejects_same_content_symlink(tmp_path: Path) -> None:
    original, copied, index, payload = archive(tmp_path)
    actual = copied / payload.relative_to(original)
    verified = load_evidence_index(copied / index.name, evidence_origin_root=original)
    actual.unlink()
    actual.symlink_to(payload)
    with pytest.raises(EvidenceValidationError):
        verified.read_local(actual)


def test_relocated_directory_swap_during_open_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original, copied, index, payload = archive(tmp_path)
    descriptor = _evidence_files._descriptor

    def swap(root: Path, relative: Path) -> int:
        (copied / "nested").rename(copied / "kept")
        (copied / "nested").symlink_to(payload.parent, target_is_directory=True)
        return descriptor(root, relative)

    monkeypatch.setattr(_evidence_files, "_descriptor", swap)
    with pytest.raises(EvidenceValidationError):
        load_evidence_index(copied / index.name, evidence_origin_root=original)


def test_relocated_summary_uses_copied_bytes(tmp_path: Path) -> None:
    original, copied, index, _ = archive(tmp_path, "recording.mcap", recording=True)
    shutil.rmtree(original)
    verified = load_evidence_index(copied / index.name, evidence_origin_root=original)
    assert verified.recording_summaries[0].path.parent == copied / "nested"


@pytest.mark.parametrize("mutation", ["outside", "mismatch", "duplicate", "traversal", "remote"])
def test_relocated_reference_failures(tmp_path: Path, mutation: str) -> None:
    original, copied, index, payload = archive(tmp_path)
    document = json.loads(index.read_bytes())
    artifact = document["artifacts"][0]
    origin = tmp_path / "orig" if mutation == "outside" else original
    if mutation == "mismatch":
        artifact["uri"] = (original / "different").as_uri()
    elif mutation == "duplicate":
        other = dict(artifact, artifact_id="another")
        document["artifacts"].append(other)
    elif mutation == "traversal":
        artifact["local_path"] = str(original / "nested" / ".." / payload.name)
        artifact["uri"] = "file://" + artifact["local_path"]
    elif mutation == "remote":
        artifact["uri"] = "file://remote-host" + str(payload)
    (copied / index.name).write_text(json.dumps(document))
    with pytest.raises(EvidenceValidationError):
        load_evidence_index(copied / index.name, evidence_origin_root=origin)


@pytest.mark.parametrize("origin", ["relative", "/original/../other", "/original//other"])
def test_invalid_origin_root(tmp_path: Path, origin: str) -> None:
    _, copied, index, _ = archive(tmp_path)
    with pytest.raises(EvidenceValidationError):
        load_evidence_index(copied / index.name, evidence_origin_root=origin)


def test_equal_bytes_at_distinct_locations_are_supported(tmp_path: Path) -> None:
    original, copied, index, payload = archive(tmp_path)
    document = json.loads(index.read_bytes())
    artifact = dict(document["artifacts"][0], artifact_id="another")
    second = original / "second.bin"
    second.write_bytes(payload.read_bytes())
    artifact.update(uri=second.as_uri(), local_path=str(second))
    document["artifacts"].append(artifact)
    (copied / "second.bin").write_bytes(second.read_bytes())
    (copied / index.name).write_text(json.dumps(document))
    verified = load_evidence_index(copied / index.name, evidence_origin_root=original)
    assert len(verified.local_files) == 2


def test_reordered_relocated_artifacts_keep_each_original_identity(tmp_path: Path) -> None:
    original, copied, index, payload = archive(tmp_path)
    second = original / "second.bin"
    second.write_bytes(b"another measurement")
    document = json.loads(index.read_bytes())
    document["artifacts"].insert(
        0, local_evidence_artifact(second, overrides={"artifact_id": "second"})
    )
    (copied / "second.bin").write_bytes(second.read_bytes())
    (copied / index.name).write_text(json.dumps(document))
    verified = load_evidence_index(copied / index.name, evidence_origin_root=original)
    for path, link in verified.local_files.items():
        assert path == copied / Path(link["uri"].removeprefix("file://")).relative_to(original)
        assert verified.read_local(path) == (original / path.relative_to(copied)).read_bytes()


@pytest.mark.parametrize("change", ["tamper", "grow", "remove"])
def test_relocated_reopen_verifies_again(tmp_path: Path, change: str) -> None:
    original, copied, index, payload = archive(tmp_path)
    actual = copied / payload.relative_to(original)
    verified = load_evidence_index(copied / index.name, evidence_origin_root=original)
    if change == "tamper":
        actual.write_bytes(b"x" * actual.stat().st_size)
    elif change == "grow":
        actual.write_bytes(actual.read_bytes() + b"x")
    else:
        actual.unlink()
    with pytest.raises(EvidenceValidationError):
        verified.read_local(actual)


@pytest.mark.parametrize("suffix", ["%ZZ", "%", "%00", "/./payload.bin", "//payload.bin"])
def test_relocated_malformed_uri_is_rejected(tmp_path: Path, suffix: str) -> None:
    original, copied, index, _ = archive(tmp_path)
    document = json.loads(index.read_bytes())
    document["artifacts"][0]["uri"] += suffix
    (copied / index.name).write_text(json.dumps(document))
    with pytest.raises(EvidenceValidationError):
        load_evidence_index(copied / index.name, evidence_origin_root=original)
