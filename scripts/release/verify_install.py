from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import asdict
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from packaging.utils import canonicalize_name, parse_sdist_filename, parse_wheel_filename
from packaging.version import Version

from scripts.release.plan import ReleaseError, ReleasePlan, contracts_requirement, requirements


def distribution_metadata(path: Path) -> tuple[str, str, list[str]]:
    if path.suffix == ".whl":
        filename_name, filename_version, _, _ = parse_wheel_filename(path.name)
        with ZipFile(path) as wheel:
            members = [name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")]
            if len(members) != 1:
                raise ReleaseError("wheel must contain exactly one METADATA file")
            raw = wheel.read(members[0])
    else:
        filename_name, filename_version = parse_sdist_filename(path.name)
        with tarfile.open(path, "r:gz") as sdist:
            tar_members = [
                member
                for member in sdist
                if member.name.endswith("/PKG-INFO") and member.name.count("/") == 1
            ]
            if len(tar_members) != 1 or not tar_members[0].isfile():
                raise ReleaseError("sdist must contain exactly one root PKG-INFO file")
            stream = sdist.extractfile(tar_members[0])
            if stream is None:
                raise ReleaseError("sdist metadata is unreadable")
            raw = stream.read()
    metadata = BytesParser(policy=policy.default).parsebytes(raw)
    name, version = str(metadata["Name"]), str(metadata["Version"])
    if canonicalize_name(name) != filename_name or Version(version) != filename_version:
        raise ReleaseError("distribution filename and metadata disagree")
    return name, version, [str(item) for item in metadata.get_all("Requires-Dist", [])]


def validate_distributions(directory: Path, plan: ReleasePlan) -> list[Path]:
    artifacts = sorted(directory.glob("*.whl")) + sorted(directory.glob("*.tar.gz"))
    if len(artifacts) != 2 or sum(path.suffix == ".whl" for path in artifacts) != 1:
        raise ReleaseError("expected exactly one wheel and one sdist")
    # uv build creates this non-distribution marker in a fresh output directory.
    entries = {path for path in directory.iterdir() if path.name != ".gitignore"}
    if entries != set(artifacts) or any(
        path.is_symlink() or not path.is_file() for path in artifacts
    ):
        raise ReleaseError("distribution directory must contain only the two regular archives")
    for artifact in artifacts:
        name, version, dependencies = distribution_metadata(artifact)
        if canonicalize_name(name) != plan.package or Version(version) != Version(plan.version):
            raise ReleaseError(f"{artifact.name} does not match candidate {plan.candidate}")
        requirements(dependencies)
        if plan.key == "harness":
            requirement = contracts_requirement(
                dependencies, Version(version), Version(plan.contracts_version)
            )
            if requirement != plan.contracts_requirement:
                raise ReleaseError(
                    "built harness contracts requirement differs from its source metadata"
                )
    return artifacts


def clean_environment() -> dict[str, str]:
    # No project index, source override, editable environment or Python path can
    # influence either the installer or the installed-code smoke process.
    return {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("UV_", "PIP_", "PYTHON")) and name != "VIRTUAL_ENV"
    } | {"PYTHONNOUSERSITE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}


def clean_install(
    artifact: Path,
    plan: ReleasePlan,
    *,
    workspace: Path,
    interpreter: str,
    uv: str,
) -> dict[str, Any]:
    env = clean_environment()
    with tempfile.TemporaryDirectory(prefix="robotics-release-") as temporary:
        root = Path(temporary).resolve()
        if root.is_relative_to(workspace.resolve()):
            raise ReleaseError(
                "clean install directory must be outside the workspace; fix TMPDIR/TEMP"
            )
        dist = root / artifact.name
        shutil.copyfile(artifact, dist)
        shutil.copyfile(Path(__file__).with_name("smoke.py"), root / "smoke.py")
        (root / "plan.json").write_text(json.dumps(asdict(plan)), encoding="utf-8")
        shutil.copytree(
            workspace / "packages/contracts/consumer-examples/minimal-simulation", root / "examples"
        )
        venv = root / "venv"
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        commands = [
            [uv, "--no-config", "venv", "--python", interpreter, str(venv)],
            [
                uv,
                "--no-config",
                "pip",
                "install",
                "--python",
                str(python),
                "--no-sources",
                "--default-index",
                "https://pypi.org/simple",
                str(dist),
            ],
        ]
        if plan.contracts_version:
            commands[-1].append(f"robotics-runtime-contracts=={plan.contracts_version}")
        commands += [
            [uv, "--no-config", "pip", "check", "--python", str(python)],
            [str(python), "-I", "smoke.py", "plan.json"],
        ]
        for command in commands:
            subprocess.run(command, cwd=root, env=env, check=True)
        return {"artifact": artifact.name, "status": "passed", "outside_workspace": True}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install wheel and sdist separately outside the workspace"
    )
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--python", default="3.12")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    plan = ReleasePlan(**json.loads(args.plan.read_text(encoding="utf-8")))
    uv = shutil.which("uv")
    if uv is None:
        parser.exit(1, "uv executable is required\n")
    try:
        artifacts = validate_distributions(args.dist, plan)
        results = [
            clean_install(path, plan, workspace=args.workspace, interpreter=args.python, uv=uv)
            for path in artifacts
        ]
    except (ReleaseError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"clean release verification failed: {error}\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
