from __future__ import annotations

import argparse
import json
import re
import subprocess
import tomllib
from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version

PACKAGES = {
    "contracts": "robotics-runtime-contracts",
    "harness": "robotics-acceptance-harness",
}
MODULES = {
    "contracts": "robotics_runtime_contracts",
    "harness": "robotics_acceptance_harness",
}
TAG = re.compile(
    r"(contracts|harness)-v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-rc\.([1-9]\d*))?"
)


class ReleaseError(ValueError):
    """A release precondition failed."""


@dataclass(frozen=True)
class ReleasePlan:
    candidate: str
    key: str
    package: str
    version: str
    commit: str
    tree: str
    source_date_epoch: str
    dry_run: bool
    contracts_version: str = ""
    contracts_tag: str = ""
    contracts_commit: str = ""
    contracts_tree: str = ""
    contracts_requirement: str = ""
    source_files: dict[str, dict[str, str]] = field(default_factory=dict)


def parse_candidate(candidate: str) -> tuple[str, Version]:
    match = TAG.fullmatch(candidate)
    if match is None:
        raise ReleaseError("candidate must be contracts-vX.Y.Z or harness-vX.Y.Z, optionally -rc.N")
    return match[1], Version(candidate.partition("-v")[2])


def version_tag(key: str, version: Version) -> str:
    if (
        len(version.release) != 3
        or version.dev is not None
        or version.post is not None
        or version.local
    ):
        raise ReleaseError(f"unsupported release version: {version}")
    suffix = ""
    if version.pre is not None:
        if version.pre[0] != "rc" or version.pre[1] < 1:
            raise ReleaseError("only rc.N prereleases are supported")
        suffix = f"-rc.{version.pre[1]}"
    return f"{key}-v{'.'.join(map(str, version.release))}{suffix}"


def requirements(values: list[str]) -> list[Requirement]:
    parsed = [Requirement(value) for value in values]
    if any(item.url is not None for item in parsed):
        raise ReleaseError(
            "release dependencies must use index version requirements, not URLs/paths"
        )
    return parsed


def contracts_requirement(values: list[str], harness: Version, contracts: Version) -> str:
    matches = [
        item
        for item in requirements(values)
        if canonicalize_name(item.name) == PACKAGES["contracts"]
    ]
    if len(matches) != 1 or matches[0].marker is not None or matches[0].extras:
        raise ReleaseError("harness must declare one unconditional contracts requirement")
    if contracts.is_prerelease:
        raise ReleaseError("harness requires an already released stable contracts version")
    major, minor = contracts.release[:2]
    # SPEC 37's first workspace train. Later trains follow the selected contracts minor.
    if harness.release[:2] == (0, 19) and (major, minor) != (0, 17):
        raise ReleaseError("harness 0.19 requires released contracts >=0.17,<0.18")
    expected = SpecifierSet(f">={major}.{minor},<{major}.{minor + 1}")
    if matches[0].specifier != expected or contracts not in matches[0].specifier:
        raise ReleaseError(f"harness contracts requirement must be {expected}")
    return str(matches[0])


def git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments], text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise ReleaseError(f"git {' '.join(arguments)}: {result.stderr.strip()}")
    return result.stdout.strip()


def project(repo: Path, key: str) -> dict[str, Any]:
    with (repo / "packages" / key / "pyproject.toml").open("rb") as stream:
        data = tomllib.load(stream)["project"]
    if data["name"] != PACKAGES[key]:
        raise ReleaseError(f"unexpected project name in packages/{key}")
    requirements(data.get("dependencies", []))
    return dict(data)


def verify_contracts_tree(repo: Path, tag: str) -> tuple[str, str]:
    commit = git(repo, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
    published_tree = git(repo, "rev-parse", f"{commit}:packages/contracts")
    if published_tree != git(repo, "rev-parse", "HEAD:packages/contracts"):
        raise ReleaseError(f"packages/contracts differs from released tag {tag}")
    return commit, published_tree


def verify_published_release(repository: str, tag: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ReleaseError("a GitHub owner/repository is required to verify the contracts release")
    result = subprocess.run(
        [
            "gh",
            "release",
            "view",
            tag,
            "--repo",
            repository,
            "--json",
            "tagName,isDraft,isPrerelease",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise ReleaseError(
            f"cannot verify published contracts release {tag}: {result.stderr.strip()}"
        )
    release = json.loads(result.stdout)
    if (
        release.get("tagName") != tag
        or release.get("isDraft") is not False
        or release.get("isPrerelease") is not False
    ):
        raise ReleaseError(f"{tag} must have a published, non-draft, stable GitHub release")


def verify_changelog(text: str, version: Version, contracts_tag: str) -> None:
    active = False
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            heading = re.match(r"## \[?v?([^\]\s]+)", line)
            try:
                active = heading is not None and Version(heading[1]) == version
            except ValueError:
                active = False
        elif active:
            body.append(line)
    if not re.search(rf"(?<![\w.-]){re.escape(contracts_tag)}(?![\w.-])", "\n".join(body)):
        raise ReleaseError(f"harness CHANGELOG section {version} must reference {contracts_tag}")


def source_files(repo: Path, key: str) -> dict[str, str]:
    prefix = f"packages/{key}/src/"
    paths = git(repo, "ls-files", "-z", "--", prefix).split("\0")
    return {
        path.removeprefix(prefix): sha256((repo / path).read_bytes()).hexdigest()
        for path in paths
        if path
    }


def create_plan(repo: Path, candidate: str, *, event: str, repository: str = "") -> ReleasePlan:
    key, selected = parse_candidate(candidate)
    if event not in {"push", "workflow_dispatch"}:
        raise ReleaseError("only tag pushes and explicit workflow_dispatch dry-runs are supported")
    metadata = project(repo, key)
    actual = Version(metadata["version"])
    if selected != actual or candidate != version_tag(key, actual):
        raise ReleaseError(f"candidate {candidate} does not match {metadata['name']} {actual}")
    if git(repo, "status", "--porcelain", "--untracked-files=all", "--", "packages"):
        raise ReleaseError("package trees must be clean before building a release candidate")
    commit = git(repo, "rev-parse", "HEAD")
    if event == "push":
        if commit != git(repo, "rev-parse", "--verify", f"refs/tags/{candidate}^{{commit}}"):
            raise ReleaseError("the pushed tag must identify the checked-out commit")
        git(repo, "merge-base", "--is-ancestor", commit, "refs/remotes/origin/main")
    plan = ReleasePlan(
        candidate=candidate,
        key=key,
        package=PACKAGES[key],
        version=str(actual),
        commit=commit,
        tree=git(repo, "rev-parse", f"HEAD:packages/{key}"),
        source_date_epoch=git(repo, "show", "-s", "--format=%ct", "HEAD"),
        dry_run=event == "workflow_dispatch",
        source_files={PACKAGES[key]: source_files(repo, key)},
    )
    if key == "contracts":
        return plan
    contracts = Version(project(repo, "contracts")["version"])
    dependency = contracts_requirement(metadata["dependencies"], actual, contracts)
    tag = version_tag("contracts", contracts)
    contracts_commit, contracts_tree = verify_contracts_tree(repo, tag)
    changelog = repo / "packages/harness/CHANGELOG.md"
    if not changelog.is_file():
        raise ReleaseError(f"{changelog} must record the released contracts tag")
    verify_changelog(changelog.read_text(encoding="utf-8"), actual, tag)
    verify_published_release(repository, tag)
    return replace(
        plan,
        contracts_version=str(contracts),
        contracts_tag=tag,
        contracts_commit=contracts_commit,
        contracts_tree=contracts_tree,
        contracts_requirement=dependency,
        source_files=plan.source_files | {PACKAGES["contracts"]: source_files(repo, "contracts")},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a release candidate without publishing")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--event", required=True, choices=("push", "workflow_dispatch"))
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--repository", default="")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    try:
        plan = create_plan(
            args.workspace.resolve(), args.candidate, event=args.event, repository=args.repository
        )
    except (ReleaseError, OSError) as error:
        parser.exit(1, f"release precondition failed: {error}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(asdict(plan), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.github_output:
        outputs = {
            "package": plan.package,
            "candidate": plan.candidate,
            "version": plan.version,
            "prerelease": str(Version(plan.version).is_prerelease).lower(),
            "source_date_epoch": plan.source_date_epoch,
        }
        with args.github_output.open("a", encoding="utf-8") as stream:
            for name, value in outputs.items():
                stream.write(f"{name}={value}\n")
    print(f"validated {'dry-run' if plan.dry_run else 'tag'} candidate: {plan.candidate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
