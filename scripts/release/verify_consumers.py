"""Run the public consumer checks through the existing isolated release installer."""

from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any

from scripts.release.plan import PACKAGES, ReleaseError, ReleasePlan, git, project, source_files
from scripts.release.verify_install import clean_environment, clean_install, distribution_metadata

INFRA_REPOSITORY = "https://github.com/mmkolpakov/robotics-runtime-infra"
INFRA_COMMIT = "dfbf26e99d3d569f9d25bdc260510220d4dd2872"
FIXTURE_DIRECTORY = "test/qualification/fixtures"
PUBLISHED_COMMITS = {
    "contracts": "a6fd70f73b6c7c4f2b70b449e5dedeefb96d46fa",
    "harness": "4e8b008e36b84aafcc64edbc928c77bd02d62b4d",
}
PUBLISHED_VERSIONS = {"contracts": "0.21.1", "harness": "0.22.2"}


def extract_infra_fixtures(infra: Path, destination: Path) -> tuple[Path, dict[str, Any]]:
    if git(infra, "rev-parse", "HEAD") != INFRA_COMMIT:
        raise ReleaseError(f"consumer fixtures require infra commit {INFRA_COMMIT}")
    archive = subprocess.run(
        ["git", "-C", str(infra), "archive", INFRA_COMMIT, FIXTURE_DIRECTORY],
        capture_output=True,
        check=True,
    ).stdout
    # Read committed bytes, rather than checkout line endings or local modifications.
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(destination, filter="data")
    fixtures = destination / FIXTURE_DIRECTORY
    paths = sorted(path for path in fixtures.iterdir() if path.is_file())
    if not paths:
        raise ReleaseError("the pinned infra fixture set is empty")
    provenance = {
        "repository": INFRA_REPOSITORY,
        "commit": INFRA_COMMIT,
        "producer_ci": [
            f"{INFRA_REPOSITORY}/actions/runs/36992458203",
            f"{INFRA_REPOSITORY}/actions/runs/36992458109",
        ],
        "kind": "synthetic qualification regression inputs",
        "files": [
            {
                "path": f"{FIXTURE_DIRECTORY}/{path.name}",
                "sha256": sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
            }
            for path in paths
        ],
    }
    return fixtures, provenance


def consumer_plan(workspace: Path, mode: str) -> ReleasePlan:
    versions = (
        PUBLISHED_VERSIONS
        if mode == "published"
        else {key: str(project(workspace, key)["version"]) for key in PACKAGES}
    )
    refs = (
        PUBLISHED_COMMITS
        if mode == "published"
        else {"contracts": PUBLISHED_COMMITS["contracts"]}
        if mode == "candidate-published"
        else {}
    )
    if mode == "candidate-published":
        versions["contracts"] = PUBLISHED_VERSIONS["contracts"]
    commit = refs.get("harness") or git(workspace, "rev-parse", "HEAD")
    contracts_commit = refs.get("contracts", "")
    return ReleasePlan(
        candidate=f"harness-v{versions['harness']}",
        key="harness",
        package=PACKAGES["harness"],
        version=versions["harness"],
        commit=commit,
        tree=git(workspace, "rev-parse", f"{commit}:packages/harness"),
        source_date_epoch=git(workspace, "show", "-s", "--format=%ct", commit),
        dry_run=True,
        contracts_version=versions["contracts"],
        contracts_tag=f"contracts-v{versions['contracts']}" if contracts_commit else "",
        contracts_commit=contracts_commit,
        contracts_tree=(
            git(workspace, "rev-parse", f"{contracts_commit}:packages/contracts/src")
            if contracts_commit
            else ""
        ),
        source_files={
            name: source_files(workspace, key, ref=refs.get(key)) for key, name in PACKAGES.items()
        },
    )


def verify_consumers(
    workspace: Path,
    infra: Path,
    *,
    mode: str,
    interpreter: str,
    uv: str,
    contracts_wheel: Path | None = None,
) -> dict[str, Any]:
    plan = consumer_plan(workspace, mode)
    with tempfile.TemporaryDirectory(prefix="robotics-consumer-") as temporary:
        root = Path(temporary).resolve()
        if root.is_relative_to(workspace.resolve()):
            raise ReleaseError("consumer temporary directory must be outside the workspace")
        fixtures, provenance = extract_infra_fixtures(infra, root / "producer")
        if mode == "candidate-published":
            expected = "34a476046ce3326384780224b4e40cad72f41ce756f627d63a6503e01349e015"
            filename = "robotics_runtime_contracts-0.21.1-py3-none-any.whl"
            if contracts_wheel is None or contracts_wheel.name != filename:
                raise ReleaseError("the exact published contracts wheel is required")
            if (
                contracts_wheel.is_symlink()
                or not contracts_wheel.is_file()
                or contracts_wheel.stat().st_size != 152270
            ):
                raise ReleaseError(
                    "published contracts wheel must be a regular file of the expected size"
                )
            if sha256(contracts_wheel.read_bytes()).hexdigest() != expected:
                raise ReleaseError("published contracts wheel digest differs")
            subprocess.run(
                [
                    uv,
                    "--no-config",
                    "build",
                    "--package",
                    PACKAGES["harness"],
                    "--no-sources",
                    "--out-dir",
                    str(root / "dist"),
                ],
                cwd=workspace,
                env=clean_environment(),
                check=True,
            )
            artifacts = sorted((root / "dist").glob("*.whl")) + sorted(
                (root / "dist").glob("*.tar.gz")
            )
            if len(artifacts) != 2 or sum(path.suffix == ".whl" for path in artifacts) != 1:
                raise ReleaseError("candidate harness requires a wheel and sdist")
            results = [
                clean_install(
                    artifact,
                    plan,
                    workspace=workspace,
                    interpreter=interpreter,
                    uv=uv,
                    additional_artifacts=(contracts_wheel,),
                    consumer_fixtures=fixtures,
                    consumer_provenance=provenance,
                    wire_consumer=True,
                    published_contracts_sha256=expected,
                )
                for artifact in artifacts
            ]
            return {
                "mode": mode,
                "contracts_wheel": {
                    "filename": filename,
                    "sha256": expected,
                    "origin": "https://pypi.org/project/robotics-runtime-contracts/0.21.1/",
                },
                "source_commit": plan.commit,
                "candidate_artifacts": [
                    {"filename": artifact.name, "sha256": sha256(artifact.read_bytes()).hexdigest()}
                    for artifact in artifacts
                ],
                "results": results,
            }
        wheels: dict[str, Path] = {}
        if mode == "candidate":
            for name in PACKAGES.values():
                subprocess.run(
                    [
                        uv,
                        "--no-config",
                        "build",
                        "--wheel",
                        "--package",
                        name,
                        "--no-sources",
                        "--out-dir",
                        str(root / "dist"),
                    ],
                    cwd=workspace,
                    env=clean_environment(),
                    check=True,
                )
            wheels = {
                distribution_metadata(path)[0]: path for path in (root / "dist").glob("*.whl")
            }
            if set(wheels) != set(PACKAGES.values()):
                raise ReleaseError("consumer build must produce exactly the two package wheels")
        result = clean_install(
            wheels.get(PACKAGES["harness"]),
            plan,
            workspace=workspace,
            interpreter=interpreter,
            uv=uv,
            additional_artifacts=(wheels[PACKAGES["contracts"]],) if wheels else (),
            consumer_fixtures=fixtures,
            consumer_provenance=provenance,
        )
        return {
            "mode": mode,
            "versions": {
                key: value
                for key, value in (("contracts", plan.contracts_version), ("harness", plan.version))
            },
            **result,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("candidate", "published", "candidate-published"), required=True
    )
    parser.add_argument("--contracts-wheel", type=Path)
    parser.add_argument("--infra", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--python", default="3.12")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    uv = shutil.which("uv")
    if uv is None:
        parser.exit(1, "uv executable is required\n")
    try:
        report = verify_consumers(
            args.workspace.resolve(),
            args.infra.resolve(),
            mode=args.mode,
            interpreter=args.python,
            uv=uv,
            contracts_wheel=args.contracts_wheel,
        )
    except (ReleaseError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"installed consumer verification failed: {error}\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
