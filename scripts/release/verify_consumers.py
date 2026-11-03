"""Run the public consumer checks through the existing isolated release installer."""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement
from packaging.version import Version

from scripts.release.plan import (
    PACKAGES,
    ReleaseError,
    ReleasePlan,
    contracts_requirement,
    git,
    project,
    source_files,
)
from scripts.release.verify_install import (
    clean_environment,
    clean_install,
    distribution_metadata,
    validate_distributions,
)

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
    published = mode == "published"
    versions = (
        dict(PUBLISHED_VERSIONS)
        if published
        else {key: str(project(workspace, key)["version"]) for key in PACKAGES}
    )
    refs = PUBLISHED_COMMITS if published else {}
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
        contracts_requirement=(
            ""
            if published
            else contracts_requirement(
                project(workspace, "harness")["dependencies"],
                Version(versions["harness"]),
                Version(versions["contracts"]),
            )
        ),
        source_files={
            name: source_files(workspace, key, ref=refs.get(key)) for key, name in PACKAGES.items()
        },
    )


def _harness_archives(workspace: Path, directory: Path, uv: str, plan: ReleasePlan) -> list[Path]:
    subprocess.run(
        [
            uv,
            "--no-config",
            "build",
            "--package",
            PACKAGES["harness"],
            "--no-sources",
            "--out-dir",
            str(directory),
        ],
        cwd=workspace,
        env=clean_environment(),
        check=True,
    )
    return validate_distributions(directory, plan)


def _published_reference(wheel: Path | None) -> Path:
    filename = "robotics_runtime_contracts-0.21.1-py3-none-any.whl"
    if wheel is None or wheel.name != filename:
        raise ReleaseError("the exact published contracts reference wheel is required")
    if wheel.is_symlink() or not wheel.is_file() or wheel.stat().st_size != 152270:
        raise ReleaseError(
            "published contracts reference must be a regular file of the expected size"
        )
    if (
        sha256(wheel.read_bytes()).hexdigest()
        != "34a476046ce3326384780224b4e40cad72f41ce756f627d63a6503e01349e015"
    ):
        raise ReleaseError("published contracts reference wheel digest differs")
    return wheel


def _reject_published(
    artifact: Path,
    contracts: Path,
    root: Path,
    plan: ReleasePlan,
    *,
    uv: str,
    interpreter: str,
) -> dict[str, Any]:
    _published_reference(contracts)
    venv = root / ("reject-wheel" if artifact.suffix == ".whl" else "reject-sdist")
    env = clean_environment() | {"NO_COLOR": "1"}
    subprocess.run(
        [uv, "--no-config", "venv", "--python", interpreter, str(venv)],
        cwd=root,
        env=env,
        check=True,
    )
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    arguments = [
        uv,
        "--no-config",
        "pip",
        "install",
        "--python",
        str(python),
        "--offline",
        "--no-sources",
        str(artifact),
        str(contracts),
    ]
    result = subprocess.run(
        arguments, cwd=root, env=env, capture_output=True, text=True, timeout=120
    )
    _published_reference(contracts)
    diagnostic = " ".join(result.stderr.lower().split())
    minimum = Version(plan.contracts_version)
    requirement = (
        f"robotics-runtime-contracts>={minimum.major}.{minimum.minor},"
        f"<{minimum.major}.{minimum.minor + 1}"
    )
    reasons = (
        "no solution found",
        f"robotics-acceptance-harness=={plan.version}",
        "depends on " + requirement,
        "requirements are unsatisfiable",
    )
    if result.returncode == 0 or not all(text in diagnostic for text in reasons):
        raise ReleaseError(
            "unsupported contracts were not rejected as an explicit dependency conflict: "
            + result.stderr
        )
    return {
        "artifact": artifact.name,
        "status": "expected-dependency-conflict",
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


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
    reference = (
        _published_reference(contracts_wheel) if mode == "candidate-rejects-published" else None
    )
    with tempfile.TemporaryDirectory(prefix="robotics-consumer-") as temporary:
        root = Path(temporary).resolve()
        if root.is_relative_to(workspace.resolve()):
            raise ReleaseError("consumer temporary directory must be outside the workspace")
        fixtures, provenance = extract_infra_fixtures(infra, root / "producer")
        if mode == "published":
            result = clean_install(
                None,
                plan,
                workspace=workspace,
                interpreter=interpreter,
                uv=uv,
                consumer_fixtures=fixtures,
                consumer_provenance=provenance,
            )
            return {"mode": mode, "versions": dict(PUBLISHED_VERSIONS), **result}
        archives = _harness_archives(workspace, root / "harness", uv, plan)
        if mode == "candidate-rejects-published":
            if (
                Version(PUBLISHED_VERSIONS["contracts"])
                in Requirement(plan.contracts_requirement).specifier
            ):
                raise ReleaseError("the candidate still supports the published contracts reference")
            assert reference is not None
            return {
                "mode": mode,
                "candidate": plan.candidate,
                "contracts_reference": {
                    "version": PUBLISHED_VERSIONS["contracts"],
                    "sha256": sha256(reference.read_bytes()).hexdigest(),
                },
                "results": [
                    _reject_published(
                        artifact, reference, root, plan, uv=uv, interpreter=interpreter
                    )
                    for artifact in archives
                ],
            }
        if mode != "candidate":
            raise ReleaseError("unknown consumer cohort mode")
        directory = root / "contracts"
        subprocess.run(
            [
                uv,
                "--no-config",
                "build",
                "--wheel",
                "--package",
                PACKAGES["contracts"],
                "--no-sources",
                "--out-dir",
                str(directory),
            ],
            cwd=workspace,
            env=clean_environment(),
            check=True,
        )
        wheels = sorted(directory.glob("*.whl"))
        if len(wheels) != 1 or distribution_metadata(wheels[0])[:2] != (
            PACKAGES["contracts"],
            plan.contracts_version,
        ):
            raise ReleaseError("candidate build must produce the selected contracts wheel")
        wheel = wheels[0]
        digest = sha256(wheel.read_bytes()).hexdigest()
        results = [
            clean_install(
                artifact,
                plan,
                workspace=workspace,
                interpreter=interpreter,
                uv=uv,
                additional_artifacts=(wheel,),
                consumer_fixtures=fixtures,
                consumer_provenance=provenance,
                wire_consumer=True,
                contracts_wheel_sha256=digest,
            )
            for artifact in archives
        ]
        return {
            "mode": mode,
            "versions": {"contracts": plan.contracts_version, "harness": plan.version},
            "contracts_wheel": {
                "filename": wheel.name,
                "sha256": digest,
                "provenance": "source-built candidate; not a published artifact",
            },
            "results": results,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("candidate", "published", "candidate-rejects-published"), required=True
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
    except (ReleaseError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f"installed consumer verification failed: {error}\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
