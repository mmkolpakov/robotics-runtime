from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from robotics_acceptance_harness import _evidence_files as files
from robotics_acceptance_harness.application import VerificationError, _wait_for_evidence
from robotics_acceptance_harness.evidence import EvidenceValidationError, load_evidence_index
from robotics_acceptance_harness.otel import MetricInputError, load_otlp_json_metrics
from tests.support import (
    FakeTime,
    local_evidence_artifact,
    local_recording_artifact,
    write_evidence_index,
)

RUN_ID = "run-01234567-89ab-4def-8123-456789abcdef"


def _directory_link(link: Path, target: Path) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        link.symlink_to(target, target_is_directory=True)


def test_opened_regular_file_is_read_inside_its_root(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "payload.bin"
    path.parent.mkdir()
    path.write_bytes(b"retained payload")
    with files.open_evidence(path, tmp_path) as stream:
        assert stream.read() == b"retained payload"
        assert os.fstat(stream.fileno()).st_size == 16
    assert stream.closed


@pytest.mark.parametrize("alias", [False, True])
def test_valid_hash_does_not_authorize_evidence_outside_the_index_directory(
    tmp_path: Path,
    alias: bool,
) -> None:
    root, outside = tmp_path / "evidence", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    external = outside / "payload.bin"
    external.write_bytes(b"the digest and size really match")
    if alias:
        _directory_link(root / "redirect", outside)
        external = root / "redirect" / external.name
    index = write_evidence_index(
        root / "index.json",
        run_id=RUN_ID,
        artifacts=[local_evidence_artifact(external)],
    )
    with pytest.raises(EvidenceValidationError):
        load_evidence_index(index)


def test_directory_swap_after_path_checks_cannot_redirect_the_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outside = tmp_path / "evidence", tmp_path / "outside"
    nested = root / "nested"
    nested.mkdir(parents=True)
    outside.mkdir()
    path = nested / "payload.bin"
    for destination in (path, outside / path.name):
        destination.write_bytes(b"identical bytes outside are still unauthorized")
    index = write_evidence_index(
        root / "index.json",
        run_id=RUN_ID,
        artifacts=[local_evidence_artifact(path)],
    )
    original = files._descriptor

    def swap_before_open(source: Path, directory: Path, relative: Path) -> int:
        nested.rename(root / "original")
        _directory_link(nested, outside)
        return original(source, directory, relative)

    monkeypatch.setattr(files, "_descriptor", swap_before_open)
    with pytest.raises(EvidenceValidationError):
        load_evidence_index(index)


def test_otlp_reopen_enforces_the_evidence_directory(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    root.mkdir()
    source = tmp_path / "outside.jsonl"
    source.write_text("{}\n", encoding="utf-8")
    with pytest.raises(MetricInputError, match="outside the evidence directory"):
        load_otlp_json_metrics(source, evidence_root=root)


def test_nonregular_evidence_is_rejected_without_waiting_for_a_writer(tmp_path: Path) -> None:
    if sys.platform == "win32":
        pytest.skip("POSIX named-pipe boundary; Windows handle paths are tested separately")
    source = tmp_path / "pipe"
    os.mkfifo(source)
    with (
        pytest.raises(files.EvidenceReadError, match="regular file"),
        files.open_evidence(source, tmp_path),
    ):
        pytest.fail("a FIFO was admitted as evidence")


def test_invalid_index_retries_to_the_deadline_and_preserves_the_last_error(tmp_path: Path) -> None:
    source = tmp_path / "index.json"
    source.write_bytes(b'{"artifacts":')
    clock = FakeTime()
    with pytest.raises(VerificationError, match="not ready before deadline") as caught:
        _wait_for_evidence(
            source,
            run_id=RUN_ID,
            receipt_paths=(),
            verification_paths=(),
            receipt_dependency_paths=(),
            timeout_sec=0.12,
            poll_interval_sec=0.05,
            now_ns=clock.now_ns,
            sleep_fn=clock.sleep,
        )
    assert clock.value_ns == 120_000_000
    assert isinstance(caught.value.__cause__, EvidenceValidationError)
    assert "cannot parse" in str(caught.value.__cause__)


def test_recording_summary_cannot_escape_the_evidence_directory(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    root.mkdir()
    recording = root / "recording.mcap"
    artifact = local_recording_artifact(recording, topics={"/clock": "rosgraph_msgs/msg/Clock"})
    outside = tmp_path / "outside-summary.json"
    outside.write_bytes(recording.with_suffix(".recording-summary.json").read_bytes())
    artifact["recording_summary"]["uri"] = outside.as_uri()
    index = write_evidence_index(root / "index.json", run_id=RUN_ID, artifacts=[artifact])
    with pytest.raises(EvidenceValidationError, match="recording_summary.*outside"):
        load_evidence_index(index)


def test_summary_size_digest_and_parse_share_one_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recording = tmp_path / "recording.mcap"
    artifact = local_recording_artifact(recording, topics={"/clock": "rosgraph_msgs/msg/Clock"})
    summary = recording.with_suffix(".recording-summary.json")
    index = write_evidence_index(tmp_path / "index.json", run_id=RUN_ID, artifacts=[artifact])
    original = os.open
    summary_opens: list[int] = []

    def tracked_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        descriptor = original(path, flags, *args, **kwargs)
        if Path(path).name == summary.name:
            summary_opens.append(descriptor)
        return descriptor

    monkeypatch.setattr(os, "open", tracked_open)
    verified = load_evidence_index(index)
    assert len(summary_opens) == 1
    assert verified.recording_summaries[0].sha256 == artifact["recording_summary"]["sha256"]
