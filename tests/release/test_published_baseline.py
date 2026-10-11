"""Exercise release selection against real Git tags and a fixture GitHub CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts import check_schema_compatibility as gate
from scripts.schema_compatibility import history
from scripts.schema_compatibility.structure import ReviewRequired


@pytest.fixture
def tagged_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    history.git(root, "init", "-q")
    history.git(root, "config", "user.name", "Test")
    history.git(root, "config", "user.email", "test@example.invalid")
    metadata = root / "packages/contracts/pyproject.toml"
    metadata.parent.mkdir(parents=True)
    for version in ("0.20.0", "0.21.0"):
        metadata.write_text(f'[project]\nversion="{version}"\n')
        history.git(root, "add", ".")
        history.git(root, "commit", "-q", "-m", "fixture")
        history.git(root, "tag", f"contracts-v{version}")
    return root


def record(tag: str, *, draft: bool = False, prerelease: bool = False) -> dict[str, Any]:
    return {"tagName": tag, "isDraft": draft, "isPrerelease": prerelease}


@pytest.fixture
def github(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    gh = tools / "gh"
    gh.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys\n"
        "if os.environ.get('FIXTURE_GH_ERROR'):\n"
        " print('fixture release error',file=sys.stderr); sys.exit(9)\n"
        "if sys.argv[1:3]==['release','list']:\n"
        " print(os.environ['FIXTURE_RELEASE_ROWS'])\n"
        "elif sys.argv[1:3]==['release','view']:\n"
        " print(os.environ.get('FIXTURE_RELEASE_VIEW') or json.dumps("
        "{'tagName':sys.argv[3],'isDraft':False,'isPrerelease':False}))\n"
        "else: sys.exit(10)\n"
    )
    gh.chmod(0o700)
    monkeypatch.setenv("PATH", str(tools) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("FIXTURE_RELEASE_ROWS", json.dumps([record("contracts-v0.20.0")]))


def test_candidate_self_tag_does_not_replace_the_published_baseline(
    tagged_repo: Path, github: None
) -> None:
    assert history.baseline(tagged_repo).tag == "contracts-v0.21.0"
    selected = history.published_baseline(tagged_repo, "owner/repo")
    assert selected.tag == "contracts-v0.20.0"
    assert (
        selected.commit
        == history.git(tagged_repo, "rev-parse", "refs/tags/contracts-v0.20.0^{commit}")
        .decode()
        .strip()
    )


def test_new_stable_release_is_selected_without_a_version_allowlist(
    tagged_repo: Path, github: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "FIXTURE_RELEASE_ROWS",
        json.dumps([record("contracts-v0.20.0"), record("contracts-v0.21.0")]),
    )
    assert history.published_baseline(tagged_repo, "owner/repo").tag == "contracts-v0.21.0"


def test_drafts_prereleases_and_other_packages_are_not_contracts_baselines(
    tagged_repo: Path, github: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "FIXTURE_RELEASE_ROWS",
        json.dumps(
            [
                record("contracts-v0.99.0", draft=True),
                record("contracts-v0.98.0", prerelease=True),
                record("contracts-v0.97.0-rc.1"),
                record("harness-v0.96.0"),
                record("contracts-v0.20.0"),
            ]
        ),
    )
    assert history.published_baseline(tagged_repo, "owner/repo").tag == "contracts-v0.20.0"


@pytest.mark.parametrize(
    "rows,message",
    [
        ([], "no published stable"),
        ([{"tagName": "contracts-v0.20.0"}], "metadata is incomplete"),
        ({"tagName": "contracts-v0.20.0"}, "history is invalid"),
        ([record("contracts-v0.20.0")] * 1000, "bounded scan"),
    ],
)
def test_incomplete_or_truncated_release_history_fails_closed(
    tagged_repo: Path, github: None, monkeypatch: pytest.MonkeyPatch, rows: object, message: str
) -> None:
    monkeypatch.setenv("FIXTURE_RELEASE_ROWS", json.dumps(rows))
    with pytest.raises(ReviewRequired, match=message):
        history.published_baseline(tagged_repo, "owner/repo")


def test_release_metadata_is_verified_again_before_git_extraction(
    tagged_repo: Path, github: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIXTURE_RELEASE_VIEW", json.dumps(record("contracts-v0.20.0", draft=True)))
    with pytest.raises(ReviewRequired, match="published, non-draft, stable"):
        history.published_baseline(tagged_repo, "owner/repo")


def test_missing_tag_or_mismatched_source_metadata_fails_closed(
    tagged_repo: Path, github: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIXTURE_RELEASE_ROWS", json.dumps([record("contracts-v0.22.0")]))
    with pytest.raises(ReviewRequired, match="Git baseline unavailable"):
        history.published_baseline(tagged_repo, "owner/repo")
    history.git(tagged_repo, "tag", "contracts-v0.22.0")
    with pytest.raises(ReviewRequired, match="tag/package version mismatch"):
        history.published_baseline(tagged_repo, "owner/repo")


def test_github_failure_does_not_fall_back_to_local_tags(
    tagged_repo: Path, github: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIXTURE_GH_ERROR", "1")
    with pytest.raises(ReviewRequired, match="release history unavailable"):
        history.published_baseline(tagged_repo, "owner/repo")


@pytest.mark.parametrize("operation", ["list", "view"])
def test_github_timeouts_fail_closed(
    tagged_repo: Path, github: None, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    run = subprocess.run

    def timeout(args: list[str], **kwargs: Any) -> Any:
        if args[:3] == ["gh", "release", operation]:
            raise subprocess.TimeoutExpired(args, 60)
        return run(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(ReviewRequired, match="verification failed"):
        history.published_baseline(tagged_repo, "owner/repo")


def test_explicit_empty_repository_does_not_select_offline_history(
    tagged_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(gate, "ROOT", tagged_repo)
    assert gate.main(["--published-repository", ""]) == 1
    assert "owner/repository is required" in capsys.readouterr().err
