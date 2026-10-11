"""Guard fixture provenance without an installation or a network request."""

from __future__ import annotations

import subprocess
from hashlib import sha256
from pathlib import Path

import pytest

from scripts.release import verify_consumers
from scripts.release.plan import ReleaseError, git, source_files


@pytest.fixture
def producer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = tmp_path / "producer"
    fixture = repo / verify_consumers.FIXTURE_DIRECTORY / "single-artifacts.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_bytes(b'{"artifacts":[]}\n')
    source = repo / "packages/contracts/src/robotics_runtime_contracts/__init__.py"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"released source\n")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.org",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "Fixture source",
        ],
        check=True,
    )
    monkeypatch.setattr(verify_consumers, "INFRA_COMMIT", git(repo, "rev-parse", "HEAD"))
    return repo


def test_fixture_snapshot_and_digests_use_committed_bytes(producer: Path, tmp_path: Path) -> None:
    source = producer / verify_consumers.FIXTURE_DIRECTORY / "single-artifacts.json"
    source.write_bytes(b"locally changed\r\n")
    fixtures, provenance = verify_consumers.extract_infra_fixtures(producer, tmp_path / "snapshot")
    raw = (fixtures / source.name).read_bytes()
    assert raw == b'{"artifacts":[]}\n'
    assert provenance["files"][0]["sha256"] == sha256(raw).hexdigest()
    assert provenance["commit"] == git(producer, "rev-parse", "HEAD")


def test_fixture_checkout_must_match_the_selected_commit(
    producer: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(verify_consumers, "INFRA_COMMIT", "0" * 40)
    with pytest.raises(ReleaseError, match="require infra commit"):
        verify_consumers.extract_infra_fixtures(producer, tmp_path / "snapshot")


def test_release_source_comparison_uses_original_bytes(producer: Path) -> None:
    source = producer / "packages/contracts/src/robotics_runtime_contracts/__init__.py"
    source.write_bytes(b"candidate source\r\n")
    name = "robotics_runtime_contracts/__init__.py"
    assert (
        source_files(producer, "contracts", ref="HEAD")[name]
        == sha256(b"released source\n").hexdigest()
    )
    assert source_files(producer, "contracts")[name] == sha256(source.read_bytes()).hexdigest()


def test_published_consumer_keeps_each_package_source_origin(
    producer: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contracts_commit = git(producer, "rev-parse", "HEAD")
    contract = producer / "packages/contracts/src/robotics_runtime_contracts/__init__.py"
    harness = producer / "packages/harness/src/robotics_acceptance_harness/__init__.py"
    harness.parent.mkdir(parents=True)
    harness.write_bytes(b"published harness patch\n")
    contract.write_bytes(b"other workspace contracts source\n")
    subprocess.run(["git", "-C", str(producer), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(producer),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.org",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "Independent package source",
        ],
        check=True,
    )
    harness_commit = git(producer, "rev-parse", "HEAD")
    monkeypatch.setattr(
        verify_consumers,
        "PUBLISHED_COMMITS",
        {"contracts": contracts_commit, "harness": harness_commit},
    )
    plan = verify_consumers.consumer_plan(producer, "published")
    assert plan.commit == harness_commit
    assert plan.contracts_commit == contracts_commit
    assert (
        plan.source_files["robotics-runtime-contracts"]["robotics_runtime_contracts/__init__.py"]
        == sha256(b"released source\n").hexdigest()
    )
    assert (
        plan.source_files["robotics-acceptance-harness"]["robotics_acceptance_harness/__init__.py"]
        == sha256(b"published harness patch\n").hexdigest()
    )
