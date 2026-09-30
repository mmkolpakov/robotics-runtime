from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from packaging.version import Version

from scripts.release import plan as release


@pytest.mark.parametrize(
    "candidate",
    [
        "v0.16.0",
        "other-v1.0.0",
        "contracts-v01.0.0",
        "harness-v1.0.0\n",
        "contracts-v1.0.0+local",
        "contracts-v1.0.0-rc.0",
    ],
)
def test_invalid_candidates_are_rejected(candidate: str) -> None:
    with pytest.raises(release.ReleaseError):
        release.parse_candidate(candidate)


def test_rc_tag_matches_normalized_distribution_version() -> None:
    key, version = release.parse_candidate("contracts-v0.17.0-rc.1")
    assert key == "contracts" and version == Version("0.17.0rc1")
    assert release.version_tag(key, version) == "contracts-v0.17.0-rc.1"


@pytest.mark.parametrize(
    "requirement",
    [
        "robotics-runtime-contracts @ ../contracts",
        "robotics-runtime-contracts @ git+https://example.org/contracts.git@main",
        "robotics-runtime-contracts @ https://example.org/contracts.whl",
    ],
)
def test_release_dependencies_cannot_be_local_or_vcs(requirement: str) -> None:
    with pytest.raises(release.ReleaseError, match="index version requirements"):
        release.requirements([requirement])


@pytest.mark.parametrize(
    "requirement",
    [
        "robotics-runtime-contracts>=0.17,<0.18",
        "robotics-runtime-contracts>=0.18",
        "robotics-runtime-contracts>=0.18,<0.20",
        "robotics-runtime-contracts==0.18.0",
        "robotics-runtime-contracts>=0.18,<0.19; python_version < '3.14'",
        "robotics-runtime-contracts[extra]>=0.18,<0.19",
    ],
)
def test_first_workspace_harness_train_requires_the_exact_bounded_minor(requirement: str) -> None:
    with pytest.raises(release.ReleaseError):
        release.contracts_requirement([requirement], Version("0.19.0"), Version("0.18.0"))


def test_harness_requirement_tracks_released_patch_versions() -> None:
    assert (
        release.contracts_requirement(
            ["robotics-runtime-contracts>=0.18,<0.19"], Version("0.19.0"), Version("0.18.9")
        )
        == "robotics-runtime-contracts<0.19,>=0.18"
    )
    with pytest.raises(release.ReleaseError, match="0.19 requires"):
        release.contracts_requirement(
            ["robotics-runtime-contracts>=0.17,<0.18"], Version("0.19.0"), Version("0.17.0")
        )


@pytest.mark.parametrize("values", [[], ["robotics-runtime-contracts>=0.18,<0.19"] * 2])
def test_missing_and_duplicate_contracts_dependencies_fail(values: list[str]) -> None:
    with pytest.raises(release.ReleaseError, match="one unconditional"):
        release.contracts_requirement(values, Version("0.19.0"), Version("0.18.0"))


def test_harness_cannot_depend_on_prerelease_contracts() -> None:
    with pytest.raises(release.ReleaseError, match="stable contracts"):
        release.contracts_requirement(
            ["robotics-runtime-contracts>=0.18,<0.19"], Version("0.19.0rc1"), Version("0.18.0rc1")
        )


def test_changelog_binding_must_be_in_the_matching_release_section() -> None:
    text = "## 0.18.0\ncontracts-v0.17.0\n## 0.19.0\nNew release.\n"
    with pytest.raises(release.ReleaseError, match="section 0.19.0"):
        release.verify_changelog(text, Version("0.19.0"), "contracts-v0.17.0")
    release.verify_changelog(
        "## [0.19.0] - 2026-09-08\nBuilt against [contracts-v0.17.0](https://example.org).\n",
        Version("0.19.0"),
        "contracts-v0.17.0",
    )
    with pytest.raises(release.ReleaseError):
        release.verify_changelog(
            "## 0.19.0\ncontracts-v0.17.01\n", Version("0.19.0"), "contracts-v0.17.0"
        )


@pytest.mark.parametrize("changed_tree", [False, True])
def test_exact_version_tag_tree_is_checked_without_sorting_other_tags(
    changed_tree: bool,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, ...]] = []

    def git(repo: Path, *args: str) -> str:
        calls.append(args)
        # There could be contracts-v0.10.0 and contracts-v0.9.0 in this repo;
        # only the tag corresponding to the source version may be used.
        responses = {
            ("rev-parse", "--verify", "refs/tags/contracts-v0.9.0^{commit}"): "released-commit",
            ("rev-parse", "released-commit:packages/contracts/src"): "released-tree",
            ("rev-parse", "HEAD:packages/contracts/src"): "changed-tree"
            if changed_tree
            else "released-tree",
            ("show", "released-commit:packages/contracts/pyproject.toml"): PROJECT,
            ("show", "HEAD:packages/contracts/pyproject.toml"): PROJECT,
        }
        return responses[args]

    monkeypatch.setattr(release, "git", git)
    if changed_tree:
        with pytest.raises(release.ReleaseError, match="differs from released tag"):
            release.verify_contracts_tree(tmp_path, "contracts-v0.9.0")
    else:
        assert release.verify_contracts_tree(tmp_path, "contracts-v0.9.0") == (
            "released-commit",
            "released-tree",
        )
    assert len(calls) == (3 if changed_tree else 5)


PROJECT = '[project]\nname = "robotics-runtime-contracts"\nversion = "0.9.0"\n'


def _commit_all(repo: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "--no-verify", "-m", message], check=True
    )


@pytest.fixture
def released_contracts(tmp_path: Path) -> Path:
    package = tmp_path / "packages/contracts"
    (package / "src/robotics_runtime_contracts").mkdir(parents=True)
    (package / "src/robotics_runtime_contracts/__init__.py").write_text("VALUE = 1\n")
    (package / "pyproject.toml").write_text(
        PROJECT + '\n[build-system]\nrequires = ["hatchling==1.29.0"]\n'
    )
    (package / "CONTRIBUTING.md").write_text("# Contributing\n")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for key, value in (("user.name", "test"), ("user.email", "test@example.invalid")):
        subprocess.run(["git", "-C", str(tmp_path), "config", key, value], check=True)
    _commit_all(tmp_path, "release")
    subprocess.run(["git", "-C", str(tmp_path), "tag", "contracts-v0.9.0"], check=True)
    return tmp_path


@pytest.mark.parametrize(
    ("path", "text"),
    [
        ("CONTRIBUTING.md", "# Contributing\n\nUpdated.\n"),
        ("pyproject.toml", PROJECT + '\n[build-system]\nrequires = ["hatchling==1.32.4"]\n'),
        ("tests/test_new.py", "def test_new() -> None:\n    pass\n"),
    ],
)
def test_repository_only_contracts_changes_keep_the_release_binding(
    released_contracts: Path, path: str, text: str
) -> None:
    target = released_contracts / "packages/contracts" / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    _commit_all(released_contracts, "post-release change")

    commit, tree = release.verify_contracts_tree(released_contracts, "contracts-v0.9.0")

    assert commit == release.git(released_contracts, "rev-parse", "contracts-v0.9.0^{commit}")
    assert tree == release.git(released_contracts, "rev-parse", "HEAD:packages/contracts/src")


@pytest.mark.parametrize(
    ("path", "text", "message"),
    [
        ("src/robotics_runtime_contracts/__init__.py", "VALUE = 2\n", "src differs"),
        (
            "pyproject.toml",
            PROJECT + 'dependencies = ["PyYAML>=6"]\n',
            "project metadata differs",
        ),
    ],
)
def test_distributed_contracts_changes_block_the_harness_release(
    released_contracts: Path, path: str, text: str, message: str
) -> None:
    (released_contracts / "packages/contracts" / path).write_text(text)
    _commit_all(released_contracts, "post-release change")

    with pytest.raises(release.ReleaseError, match=message):
        release.verify_contracts_tree(released_contracts, "contracts-v0.9.0")


@pytest.mark.parametrize(
    "response",
    [
        {"tagName": "contracts-v0.17.0", "isDraft": True, "isPrerelease": False},
        {"tagName": "contracts-v0.17.0", "isDraft": False, "isPrerelease": True},
        {"tagName": "contracts-v0.16.0", "isDraft": False, "isPrerelease": False},
        {"tagName": "contracts-v0.17.0"},
    ],
)
def test_draft_prerelease_wrong_or_incomplete_release_records_fail(
    response: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(*args: Any, **kwargs: Any) -> Any:
        return subprocess.CompletedProcess(args[0], 0, json.dumps(response), "")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(release.ReleaseError, match="published, non-draft, stable"):
        release.verify_published_release("owner/repo", "contracts-v0.17.0")


@pytest.fixture
def candidate_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Synthetic metadata only: no git repository, tags, or package releases are created.
    for key, version, dependencies in (
        ("contracts", "0.18.0", []),
        ("harness", "0.19.0", ["robotics-runtime-contracts>=0.18,<0.19"]),
    ):
        package = tmp_path / "packages" / key
        package.mkdir(parents=True)
        (package / "pyproject.toml").write_text(
            f'[project]\nname="{release.PACKAGES[key]}"\nversion="{version}"\ndependencies={json.dumps(dependencies)}\n',
            encoding="utf-8",
        )
    (tmp_path / "packages/harness/CHANGELOG.md").write_text(
        "## 0.19.0\ncontracts-v0.18.0\n", encoding="utf-8"
    )

    def git(repo: Path, *args: str) -> str:
        if args[0] == "status":
            return ""
        if args[0] == "show" and args[-1].endswith(":packages/contracts/pyproject.toml"):
            return (tmp_path / "packages/contracts/pyproject.toml").read_text(encoding="utf-8")
        if args[0] == "show":
            return "1234567890"
        if args[0] == "merge-base":
            return ""
        if args[-1].endswith(":packages/contracts/src"):
            return "contracts-tree"
        if args[-1].endswith(":packages/harness"):
            return "harness-tree"
        return "commit"

    monkeypatch.setattr(release, "git", git)
    monkeypatch.setattr(
        release, "source_files", lambda repo, key: {f"{release.MODULES[key]}/__init__.py": "digest"}
    )
    monkeypatch.setattr(release, "verify_published_release", lambda repo, tag: None)
    return tmp_path


def test_successful_harness_plan_binds_tree_commit_requirement_and_sources(
    candidate_repo: Path,
) -> None:
    plan = release.create_plan(
        candidate_repo, "harness-v0.19.0", event="push", repository="owner/repo"
    )
    assert not plan.dry_run
    assert plan.contracts_tag == "contracts-v0.18.0"
    assert plan.contracts_commit == "commit" and plan.contracts_tree == "contracts-tree"
    assert plan.contracts_requirement == "robotics-runtime-contracts<0.19,>=0.18"
    assert set(plan.source_files) == set(release.PACKAGES.values())


def test_dry_run_does_not_waive_version_match(candidate_repo: Path) -> None:
    with pytest.raises(release.ReleaseError, match="does not match"):
        release.create_plan(candidate_repo, "contracts-v0.18.0-rc.1", event="workflow_dispatch")


def test_tag_push_rejects_wrong_commit_and_unmerged_commit(
    candidate_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = release.git

    def wrong_tag(repo: Path, *args: str) -> str:
        if "--verify" in args:
            return "wrong-commit"
        return original(repo, *args)

    monkeypatch.setattr(release, "git", wrong_tag)
    with pytest.raises(release.ReleaseError, match="checked-out commit"):
        release.create_plan(candidate_repo, "contracts-v0.18.0", event="push")

    def unmerged(repo: Path, *args: str) -> str:
        if args[0] == "merge-base":
            raise release.ReleaseError("not reachable from main")
        return original(repo, *args)

    monkeypatch.setattr(release, "git", unmerged)
    with pytest.raises(release.ReleaseError, match="not reachable"):
        release.create_plan(candidate_repo, "contracts-v0.18.0", event="push")


def test_dry_run_still_rejects_unreleased_contracts(
    candidate_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing_tag(repo: Path, tag: str) -> tuple[str, str]:
        raise release.ReleaseError("missing exact contracts tag")

    monkeypatch.setattr(release, "verify_contracts_tree", missing_tag)
    with pytest.raises(release.ReleaseError, match="missing exact contracts tag"):
        release.create_plan(candidate_repo, "harness-v0.19.0", event="workflow_dispatch")


def test_current_checkout_contracts_candidate_is_validated_without_mutating_versions() -> None:
    repo = Path(__file__).resolve().parents[2]
    metadata_path = repo / "packages/contracts/pyproject.toml"
    before = metadata_path.read_bytes()
    version = Version(release.project(repo, "contracts")["version"])
    plan = release.create_plan(
        repo, release.version_tag("contracts", version), event="workflow_dispatch"
    )
    assert plan.version == str(version) and plan.dry_run
    assert plan.source_files["robotics-runtime-contracts"]
    assert metadata_path.read_bytes() == before


@pytest.mark.parametrize(
    ("candidate", "package", "environment"),
    [
        ("contracts-v0.18.0", "robotics-runtime-contracts", "pypi"),
        ("harness-v0.19.0", "robotics-acceptance-harness", "pypi-harness"),
    ],
)
def test_cli_routes_verified_candidates_to_distinct_pypi_environments(
    candidate_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    candidate: str,
    package: str,
    environment: str,
) -> None:
    output = candidate_repo / "plan.json"
    github_output = candidate_repo / "github-output"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "plan",
            "--candidate",
            candidate,
            "--event",
            "workflow_dispatch",
            "--workspace",
            str(candidate_repo),
            "--repository",
            "owner/repo",
            "--output",
            str(output),
            "--github-output",
            str(github_output),
        ],
    )
    assert release.main() == 0
    values = dict(line.split("=", 1) for line in github_output.read_text().splitlines())
    assert values["package"] == package
    assert values["pypi_environment"] == environment
    assert json.loads(output.read_text())["dry_run"] is True
