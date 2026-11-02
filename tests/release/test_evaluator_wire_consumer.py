"""The foreign consumer must use the published contracts artifact."""

import subprocess
from pathlib import Path

import pytest

from scripts.release import verify_consumers
from scripts.release.plan import ReleaseError, source_files


def test_candidate_plan_uses_the_published_contracts_source() -> None:
    workspace = Path(__file__).resolve().parents[2]
    plan = verify_consumers.consumer_plan(workspace, "candidate-published")
    assert plan.contracts_version == "0.21.1"
    assert plan.contracts_commit == verify_consumers.PUBLISHED_COMMITS["contracts"]
    assert plan.source_files["robotics-runtime-contracts"] == source_files(
        workspace, "contracts", ref=plan.contracts_commit
    )


def test_same_size_impostor_wheel_is_refused_before_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "robotics_runtime_contracts-0.21.1-py3-none-any.whl"
    wheel.write_bytes(b"x" * 152270)
    monkeypatch.setattr(verify_consumers, "consumer_plan", lambda *_: object())
    monkeypatch.setattr(verify_consumers, "extract_infra_fixtures", lambda *_: (tmp_path, {}))
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: pytest.fail("build ran"))
    with pytest.raises(ReleaseError, match="published contracts wheel digest differs"):
        verify_consumers.verify_consumers(
            tmp_path,
            tmp_path,
            mode="candidate-published",
            interpreter="3.12",
            uv="uv",
            contracts_wheel=wheel,
        )
