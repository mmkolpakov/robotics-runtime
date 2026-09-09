from __future__ import annotations

import hashlib
import io
import json
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

import pytest

from robotics_acceptance_harness.documents import load_bundle
from robotics_acceptance_harness.evidence import load_evidence_index
from robotics_acceptance_harness.sdk import (
    EvaluationContext,
    EvidenceAccessError,
    EvidenceValidationError,
)
from tests.support import evidence_index, local_evidence_artifact

RUN_ID = "run-01234567-89ab-4def-8123-456789abcdef"
FIXTURES = Path(__file__).parent / "fixtures/simulation"


def evaluator_context(directory: Path, content: bytes) -> tuple[EvaluationContext, Path, str]:
    payload = directory / "observation.bin"
    payload.write_bytes(content)
    index = directory / "evidence-index.json"
    document = evidence_index(
        RUN_ID, [local_evidence_artifact(payload, media_type="application/octet-stream")]
    )
    index.write_text(json.dumps(document), encoding="utf-8")
    bundle = load_bundle(FIXTURES / "scenario.yaml", runtime_path=FIXTURES / "runtime.yaml")
    evidence = load_evidence_index(index, expected_run_id=RUN_ID)
    context = EvaluationContext(RUN_ID, "primary", bundle, evidence, (), 0, 1)
    return context, payload, hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize("size", [32, 2 * 1024 * 1024 + 17])
def test_sdk_yields_seekable_read_only_verified_bytes(tmp_path: Path, size: int) -> None:
    content = (b"recorded evidence" * (size // 17 + 1))[:size]
    context, payload, digest = evaluator_context(tmp_path, content)
    with context.evidence(digest) as stream:
        assert stream.read(8) == content[:8]
        stream.seek(-8, io.SEEK_END)
        assert stream.read() == content[-8:]
        stream.seek(0)
        assert hashlib.sha256(stream.read()).hexdigest() == digest
        assert not stream.writable()
        with pytest.raises(io.UnsupportedOperation):
            stream.write(b"unrecorded")
    assert stream.closed
    assert payload.read_bytes() == content
    # The existing metadata API and positional context constructor remain valid.
    assert context.evidence.links[0]["sha256"] == digest
    assert digest in context.evidence_sha256


def test_sdk_snapshot_survives_original_file_changes(tmp_path: Path) -> None:
    context, payload, digest = evaluator_context(tmp_path, b"original evidence")
    with context.evidence(digest) as stream:
        payload.write_bytes(b"modified evidence")
        assert stream.read() == b"original evidence"
        stream.seek(0)
        assert stream.read() == b"original evidence"
    with pytest.raises(EvidenceValidationError), context.evidence(digest):
        pytest.fail("modified file was yielded")


@pytest.mark.parametrize("mutation", ["same-size", "shorter", "longer", "missing"])
def test_sdk_checks_current_bytes_before_yielding(tmp_path: Path, mutation: str) -> None:
    context, payload, digest = evaluator_context(tmp_path, b"original")
    if mutation == "missing":
        payload.unlink()
    else:
        payload.write_bytes(
            {"same-size": b"tampered", "shorter": b"x", "longer": b"x" * 30}[mutation]
        )
    with pytest.raises(EvidenceValidationError), context.evidence(digest):
        pytest.fail("unverified payload was yielded")


def test_sdk_does_not_resolve_unknown_digests_as_paths(tmp_path: Path) -> None:
    context, payload, _digest = evaluator_context(tmp_path, b"original")
    with pytest.raises(EvidenceAccessError, match="absent"), context.evidence(str(payload)):
        pytest.fail("path was treated as a digest")


def test_sdk_requires_local_bytes_even_when_digest_is_verified(tmp_path: Path) -> None:
    context, _payload, digest = evaluator_context(tmp_path, b"original")
    retained_only = replace(context.evidence, local_files=MappingProxyType({}))
    context = replace(context, evidence=retained_only)
    with (
        pytest.raises(EvidenceAccessError, match="local bytes are unavailable"),
        context.evidence(digest),
    ):
        pytest.fail("retained metadata was treated as local bytes")


def test_sdk_closes_the_snapshot_when_evaluator_raises(tmp_path: Path) -> None:
    context, _payload, digest = evaluator_context(tmp_path, b"original")
    with (
        pytest.raises(RuntimeError, match="evaluator failure"),
        context.evidence(digest) as stream,
    ):
        assert stream.read(1) == b"o"
        raise RuntimeError("evaluator failure")
    assert stream.closed
