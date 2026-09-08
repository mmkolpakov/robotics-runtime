"""Read released sources from Git objects, independently of editable digest fixtures."""

from __future__ import annotations

import io
import re
import subprocess
import tarfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

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


def baseline(root: Path) -> Baseline:
    if git(root, "rev-parse", "--is-shallow-repository").strip() != b"false":
        raise ReviewRequired(f"Shallow history; fetch full history (--unshallow) and tags: {FETCH}")
    tags = stable_tags(git(root, "tag", "--list", "contracts-v*").decode().splitlines())
    tag = tags[0] if tags else LEGACY_TAG
    commit = git(root, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}").decode().strip()
    prefix = "packages/contracts/" if tags else ""
    if not tags and commit != LEGACY_COMMIT:
        raise ReviewRequired(f"{LEGACY_TAG} moved: expected {LEGACY_COMMIT}, got {commit}")
    project = tomllib.loads(git(root, "show", f"{commit}:{prefix}pyproject.toml").decode())
    version = tag.removeprefix("contracts-v") if tags else "0.16.0"
    if project["project"]["version"] != version:
        raise ReviewRequired(f"Published tag/package version mismatch: {tag}")
    return Baseline(tag, commit, prefix)


def extract(root: Path, release: Baseline, destination: Path) -> Path:
    """Extract only released source and fixtures; reject links and unsafe archive paths."""
    content = git(
        root, "archive", release.commit, f"{release.prefix}src", f"{release.prefix}tests/fixtures"
    )
    with tarfile.open(fileobj=io.BytesIO(content)) as archive:
        members = archive.getmembers()
        if any(not (member.isfile() or member.isdir()) for member in members):
            raise ReviewRequired("Published source archive contains links or special files")
        archive.extractall(destination, members=members, filter="data")
    return destination / release.prefix
