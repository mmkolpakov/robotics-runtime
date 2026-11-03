"""Authenticate the exact released contracts wheel before harness release checks."""

from __future__ import annotations

import json
import subprocess
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import urlopen

from packaging.version import Version

from scripts.release.plan import (
    ReleaseError,
    ReleasePlan,
    verify_contracts_tree,
    verify_published_release,
    version_tag,
)


def _gh(arguments: list[str]) -> str:
    result = subprocess.run(["gh", *arguments], capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ReleaseError(
            "GitHub release authentication/download failed: " + result.stderr.strip()
        )
    return result.stdout


def _pypi_bytes(version: str, filename: str, size: int) -> dict[str, Any]:
    metadata_url = f"https://pypi.org/pypi/robotics-runtime-contracts/{version}/json"
    with urlopen(metadata_url, timeout=60) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ReleaseError("PyPI release metadata exceeds its byte bound")
    metadata = json.loads(raw)
    if metadata["info"]["version"] != version:
        raise ReleaseError("PyPI release version differs from the selected contracts")
    matches = [item for item in metadata["urls"] if item.get("filename") == filename]
    if len(matches) != 1 or matches[0].get("yanked") is not False:
        raise ReleaseError("the selected PyPI contracts wheel is absent, ambiguous or yanked")
    item = matches[0]
    if type(item.get("size")) is not int or item["size"] != size:
        raise ReleaseError("PyPI contracts wheel size differs from the authenticated asset")
    url = item["url"]
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "files.pythonhosted.org"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.fragment
    ):
        raise ReleaseError("PyPI contracts wheel must use its official HTTPS file host")
    digest, total = sha256(), 0
    with urlopen(url, timeout=60) as response:
        if urlsplit(response.geturl()).hostname != "files.pythonhosted.org":
            raise ReleaseError("PyPI contracts wheel redirected away from its file host")
        while chunk := response.read(min(65536, size + 1 - total)):
            total += len(chunk)
            if total > size:
                raise ReleaseError("PyPI contracts wheel exceeds its declared byte size")
            digest.update(chunk)
    actual = digest.hexdigest()
    if total != size or actual != item["digests"]["sha256"]:
        raise ReleaseError("PyPI contracts wheel bytes differ from its metadata")
    return {
        "metadata_url": metadata_url,
        "url": url,
        "sha256": actual,
        "size_bytes": total,
        "metadata_sha256": sha256(raw).hexdigest(),
    }


def authenticate_contracts(
    plan: ReleasePlan,
    workspace: Path,
    directory: Path,
    repository: str,
) -> tuple[Path, dict[str, Any]]:
    authority = "mmkolpakov/robotics-runtime"
    if plan.key != "harness" or repository != authority:
        raise ReleaseError("harness release needs the explicit contracts release authority")
    version = Version(plan.contracts_version)
    if version.is_prerelease or plan.contracts_tag != version_tag("contracts", version):
        raise ReleaseError("harness release requires the exact stable contracts tag")
    commit, tree = verify_contracts_tree(workspace, plan.contracts_tag)
    if (commit, tree) != (plan.contracts_commit, plan.contracts_tree):
        raise ReleaseError("selected contracts Git identity differs from the release plan")
    verify_published_release(repository, plan.contracts_tag)
    filename = f"robotics_runtime_contracts-{version}-py3-none-any.whl"
    verified_release = _gh(
        ["release", "verify", plan.contracts_tag, "--repo", repository, "--format", "json"]
    )
    directory.mkdir(mode=0o700)
    _gh(
        [
            "release",
            "download",
            plan.contracts_tag,
            "--repo",
            repository,
            "--pattern",
            filename,
            "--dir",
            str(directory),
        ]
    )
    wheel = directory / filename
    if wheel.is_symlink() or not wheel.is_file():
        raise ReleaseError("downloaded contracts wheel is not a regular file")
    captured = sha256(wheel.read_bytes()).hexdigest()
    verified_asset = _gh(
        [
            "release",
            "verify-asset",
            plan.contracts_tag,
            str(wheel),
            "--repo",
            repository,
            "--format",
            "json",
        ]
    )
    verified_source = _gh(
        [
            "attestation",
            "verify",
            str(wheel),
            "--repo",
            authority,
            "--source-digest",
            plan.contracts_commit,
            "--signer-workflow",
            authority + "/.github/workflows/release.yml",
            "--deny-self-hosted-runners",
            "--format",
            "json",
        ]
    )
    if sha256(wheel.read_bytes()).hexdigest() != captured:
        raise ReleaseError("contracts asset changed during authentication")
    pypi = _pypi_bytes(str(version), filename, wheel.stat().st_size)
    if pypi["sha256"] != captured:
        raise ReleaseError("PyPI contracts bytes differ from the authenticated GitHub release")
    return wheel, {
        "scope": "Stock GitHub release and source/workflow attestations; identical PyPI wheel",
        "repository": repository,
        "tag": plan.contracts_tag,
        "contracts_commit": commit,
        "contracts_tree": tree,
        "filename": filename,
        "sha256": captured,
        "size_bytes": wheel.stat().st_size,
        "release_verification": verified_release,
        "asset_verification": verified_asset,
        "source_verification": verified_source,
        "pypi": pypi,
    }
