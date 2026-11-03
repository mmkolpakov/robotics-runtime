"""The selected candidate and published cohorts retain distinct installed controls."""

import subprocess
from hashlib import sha256
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest

from scripts.release import verify_consumers
from scripts.release.plan import ReleaseError, ReleasePlan, source_files


def test_candidate_plan_requires_the_new_minor_without_claiming_a_release() -> None:
    workspace = Path(__file__).resolve().parents[2]
    plan = verify_consumers.consumer_plan(workspace, "candidate")
    assert plan.contracts_version == "0.22.0"
    assert plan.version == "0.23.1"
    assert plan.contracts_requirement == "robotics-runtime-contracts<0.23,>=0.22"
    assert plan.contracts_commit == plan.contracts_tag == ""
    assert plan.source_files["robotics-runtime-contracts"] == source_files(workspace, "contracts")


def test_the_original_published_baseline_is_not_relabelled() -> None:
    workspace = Path(__file__).resolve().parents[2]
    plan = verify_consumers.consumer_plan(workspace, "published")
    assert plan.version == "0.22.2"
    assert plan.contracts_version == "0.21.1"
    assert plan.contracts_commit == "a6fd70f73b6c7c4f2b70b449e5dedeefb96d46fa"
    assert plan.commit == "4e8b008e36b84aafcc64edbc928c77bd02d62b4d"


def test_same_size_impostor_reference_is_refused_before_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "robotics_runtime_contracts-0.21.1-py3-none-any.whl"
    wheel.write_bytes(b"x" * 152270)
    monkeypatch.setattr(verify_consumers, "consumer_plan", lambda *_: object())
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: pytest.fail("build ran"))
    with pytest.raises(ReleaseError, match="reference wheel digest differs"):
        verify_consumers.verify_consumers(
            tmp_path,
            tmp_path,
            mode="candidate-rejects-published",
            interpreter="3.12",
            uv="uv",
            contracts_wheel=wheel,
        )


def test_candidate_pair_runs_the_same_wire_for_wheel_and_sdist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = Path(__file__).resolve().parents[2]
    archives = [tmp_path / "harness.whl", tmp_path / "harness.tar.gz"]
    selected = verify_consumers.consumer_plan(workspace, "candidate")
    monkeypatch.setattr(verify_consumers, "consumer_plan", lambda *_: selected)
    monkeypatch.setattr(verify_consumers, "extract_infra_fixtures", lambda *_: (tmp_path, {}))
    monkeypatch.setattr(verify_consumers, "_harness_archives", lambda *_: archives)

    def build(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        directory = Path(command[command.index("--out-dir") + 1])
        directory.mkdir()
        wheel = directory / "robotics_runtime_contracts-0.22.0-py3-none-any.whl"
        with ZipFile(wheel, "w") as stream:
            stream.writestr(
                "robotics_runtime_contracts-0.22.0.dist-info/METADATA",
                "Metadata-Version: 2.3\nName: robotics-runtime-contracts\nVersion: 0.22.0\n",
            )
        return subprocess.CompletedProcess(command, 0)

    calls: list[tuple[Path, dict[str, Any]]] = []

    def install(artifact: Path, _plan: ReleasePlan, **kwargs: Any) -> dict[str, Any]:
        calls.append((artifact, kwargs))
        assert kwargs["wire_consumer"] is True
        contracts = kwargs["additional_artifacts"][0]
        assert sha256(contracts.read_bytes()).hexdigest() == kwargs["contracts_wheel_sha256"]
        return {"status": "passed", "wire_consumer": {"scope": "unit call routing only"}}

    monkeypatch.setattr(subprocess, "run", build)
    monkeypatch.setattr(verify_consumers, "clean_install", install)
    result = verify_consumers.verify_consumers(
        workspace, tmp_path, mode="candidate", interpreter="3.12", uv="uv"
    )
    assert [artifact for artifact, _ in calls] == archives
    assert len(result["results"]) == 2
    assert "source-built candidate" in result["contracts_wheel"]["provenance"]


@pytest.mark.parametrize(
    ("code", "diagnostic", "accepted"),
    [
        (
            1,
            (
                "No solution found when resolving dependencies: "
                "Because robotics-acceptance-harness==0.23.1 depends on "
                "robotics-runtime-contracts>=0.22,<0.23 and "
                "robotics-runtime-contracts==0.21.1 is selected; "
                "your requirements are unsatisfiable"
            ),
            True,
        ),
        (1, "Failed to download robotics-runtime-contracts: network unavailable", False),
        (1, "No solution found: jsonschema is unavailable offline", False),
        (0, "", False),
    ],
)
def test_only_a_real_version_conflict_counts_as_expected_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int, diagnostic: str, accepted: bool
) -> None:
    workspace = Path(__file__).resolve().parents[2]
    plan = verify_consumers.consumer_plan(workspace, "candidate-rejects-published")

    def run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "install" in command:
            assert "--offline" in command and "--no-sources" in command
            return subprocess.CompletedProcess(command, code, stdout="", stderr=diagnostic)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(verify_consumers, "_published_reference", lambda path: path)
    args = (tmp_path / "harness.whl", tmp_path / "contracts.whl", tmp_path, plan)
    if accepted:
        result = verify_consumers._reject_published(*args, uv="uv", interpreter="3.12")
        assert result["status"] == "expected-dependency-conflict"
    else:
        with pytest.raises(ReleaseError, match="explicit dependency conflict"):
            verify_consumers._reject_published(*args, uv="uv", interpreter="3.12")
