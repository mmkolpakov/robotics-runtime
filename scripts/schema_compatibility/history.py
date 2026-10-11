"""Read released sources from Git objects, independently of editable digest fixtures."""

from __future__ import annotations

import io
import json
import re
import subprocess
import tarfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

from scripts.release.plan import ReleaseError, verify_published_release
from scripts.schema_compatibility.structure import ReviewRequired

LEGACY_TAG = "contracts-legacy/v0.16.0"
LEGACY_COMMIT = "0c2c0f4d37ef97fc6818ac61c66cdcef0bec3940"
LEGACY_URL = "https://github.com/mmkolpakov/robotics-runtime-contracts.git"
FETCH = f"git fetch origin --tags; git fetch {LEGACY_URL} refs/tags/v0.16.0:refs/tags/{LEGACY_TAG}"


@dataclass(frozen=True)
class Baseline:
    tag: str
    commit: str
    prefix: str


def git(root: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments], capture_output=True, check=False, timeout=60
    )
    if result.returncode:
        raise ReviewRequired(f"Git baseline unavailable: {result.stderr.decode().strip()}; {FETCH}")
    return result.stdout


def stable_tags(tags: list[str]) -> list[str]:
    versions = []
    for tag in tags:
        match = re.fullmatch(r"contracts-v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", tag)
        if match:
            versions.append((tuple(int(part) for part in match.groups()), tag))
    return [tag for _, tag in sorted(versions, reverse=True)]


def _tag_baseline(root: Path, tag: str) -> Baseline:
    commit = git(root, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}").decode().strip()
    legacy = tag == LEGACY_TAG
    prefix = "" if legacy else "packages/contracts/"
    if legacy and commit != LEGACY_COMMIT:
        raise ReviewRequired(f"{LEGACY_TAG} moved: expected {LEGACY_COMMIT}, got {commit}")
    project = tomllib.loads(git(root, "show", f"{commit}:{prefix}pyproject.toml").decode())
    version = "0.16.0" if legacy else tag.removeprefix("contracts-v")
    if project["project"]["version"] != version:
        raise ReviewRequired(f"Published tag/package version mismatch: {tag}")
    return Baseline(tag, commit, prefix)


def baseline(root: Path) -> Baseline:
    if git(root, "rev-parse", "--is-shallow-repository").strip() != b"false":
        raise ReviewRequired(f"Shallow history; fetch full history (--unshallow) and tags: {FETCH}")
    tags = stable_tags(git(root, "tag", "--list", "contracts-v*").decode().splitlines())
    return _tag_baseline(root, tags[0] if tags else LEGACY_TAG)


def published_baseline(root: Path, repository: str) -> Baseline:
    """Select a verified stable GitHub release, independently of local candidate tags."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ReviewRequired("a GitHub owner/repository is required for the published baseline")
    if git(root, "rev-parse", "--is-shallow-repository").strip() != b"false":
        raise ReviewRequired(f"Shallow history; fetch full history (--unshallow) and tags: {FETCH}")
    try:
        result = subprocess.run(
            [
                "gh",
                "release",
                "list",
                "--repo",
                repository,
                "--limit",
                "1000",
                "--json",
                "tagName,isDraft,isPrerelease",
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        if result.returncode:
            raise ReviewRequired(f"published release history unavailable: {result.stderr.strip()}")
        rows = json.loads(result.stdout)
        tags = _published_tags(rows)
        if not tags:
            raise ReviewRequired("no published stable contracts release is available")
        verify_published_release(repository, tags[0])
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, ReleaseError) as error:
        raise ReviewRequired(f"published release verification failed: {error}") from error
    return _tag_baseline(root, tags[0])


def _published_tags(rows: object) -> list[str]:
    if not isinstance(rows, list) or len(rows) >= 1000:
        raise ReviewRequired("published release history is invalid or exceeds the bounded scan")
    for row in rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("tagName"), str)
            or type(row.get("isDraft")) is not bool
            or type(row.get("isPrerelease")) is not bool
        ):
            raise ReviewRequired("published release metadata is incomplete")
    return stable_tags(
        [row["tagName"] for row in rows if not row["isDraft"] and not row["isPrerelease"]]
    )


def extract(root: Path, release: Baseline, destination: Path) -> Path:
    """Extract released source, fixtures and consumer examples; reject links and unsafe paths."""
    paths = [
        f"{release.prefix}src",
        f"{release.prefix}tests/fixtures",
        f"{release.prefix}consumer-examples",
    ]
    if release.prefix:
        paths.extend(["packages/harness/tests/fixtures", "packages/harness/tests/live/fixtures"])
    content = git(root, "archive", release.commit, *paths)
    with tarfile.open(fileobj=io.BytesIO(content)) as archive:
        members = archive.getmembers()
        if any(not (member.isfile() or member.isdir()) for member in members):
            raise ReviewRequired("Published source archive contains links or special files")
        archive.extractall(destination, members=members, filter="data")
    return destination / release.prefix
