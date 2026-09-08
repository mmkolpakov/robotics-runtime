"""Copied and run with the installed interpreter, -I, outside the workspace."""

from __future__ import annotations

import json
import subprocess
import sys
import sysconfig
from hashlib import sha256
from importlib import import_module
from importlib.metadata import distribution, distributions
from pathlib import Path
from typing import Any


def verify_installed_sources(plan: dict[str, Any]) -> None:
    prefix = Path(sys.prefix).resolve()
    for name, sources in plan["source_files"].items():
        installed = distribution(name)
        expected = plan["version"] if name == plan["package"] else plan["contracts_version"]
        if installed.version != expected:
            raise RuntimeError(f"installed {name} version differs from the release plan")
        modules = {Path(relative).parts[0] for relative in sources}
        inventory = {
            file.as_posix()
            for file in installed.files or ()
            if file.parts[0] in modules and "__pycache__" not in file.parts
        }
        if inventory != set(sources):
            raise RuntimeError(f"installed {name} file inventory differs from the release source")
        for relative, digest in sources.items():
            path = Path(str(installed.locate_file(relative))).resolve()
            if not path.is_relative_to(prefix) or sha256(path.read_bytes()).hexdigest() != digest:
                raise RuntimeError(
                    f"installed {name}/{relative} differs from the checked release source"
                )
    for installed in distributions():
        origin = installed.read_text("direct_url.json")
        if origin is not None:
            direct = json.loads(origin)
            # Only the artifact under test may have a local archive origin.
            if (
                installed.metadata["Name"] != plan["package"]
                or "archive_info" not in direct
                or "dir_info" in direct
                or "vcs_info" in direct
            ):
                raise RuntimeError(
                    f"non-index or editable dependency: {installed.metadata['Name']}"
                )


def main() -> None:
    plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    verify_installed_sources(plan)
    contracts = import_module("robotics_runtime_contracts")
    assert contracts.__file__ is not None
    assert (
        Path(contracts.__file__).resolve()
        == Path(
            str(
                distribution("robotics-runtime-contracts").locate_file(
                    "robotics_runtime_contracts/__init__.py"
                )
            )
        ).resolve()
    )

    for name in contracts.schema_resource_names():
        assert contracts.schema_path(name).is_file()
        assert contracts.load_schema(name)["$id"]
    examples = Path("examples")
    documents = sorted(examples.glob("*.yaml"))
    assert documents
    for path in documents:
        contracts.validate_document(contracts.load_mapping(path))
    writers = import_module("robotics_runtime_contracts.writers")
    qualification = import_module("robotics_runtime_contracts.qualification")
    runtime = writers.create_runtime_manifest(
        contracts.load_mapping(examples / "runtime-manifest.yaml")
    )
    output = writers.write_document(runtime, Path("generated-runtime.json"))
    assert contracts.load_mapping(output) == runtime
    assert contracts.file_sha256(output) == sha256(output.read_bytes()).hexdigest()
    report = qualification.inspect_qualification_artifacts(
        [f"scenario:scenario.json={examples / 'scenario.yaml'}"]
    )
    assert not report.valid and report.diagnostics and report.blocked_checks
    for role in ("execution_trust_policy", "robot_description"):
        assert contracts.load_schema(contracts.schema_for_role(role))["$id"]
    scripts = Path(sysconfig.get_path("scripts"))
    suffix = ".exe" if sys.platform == "win32" else ""
    subprocess.run(
        [str(scripts / f"robotics-contracts{suffix}"), "validate", "--quiet", *map(str, documents)],
        check=True,
    )
    if plan["key"] == "harness":
        harness = import_module("robotics_acceptance_harness")
        assert harness.__file__ is not None
        assert (
            Path(harness.__file__).resolve()
            == Path(
                str(
                    distribution("robotics-acceptance-harness").locate_file(
                        "robotics_acceptance_harness/__init__.py"
                    )
                )
            ).resolve()
        )
        assert harness.__version__ == plan["version"]
        assert harness.EvaluationContext and harness.ProductEvaluator
        subprocess.run(
            [
                str(scripts / f"robotics-acceptance{suffix}"),
                "explain",
                "--scenario",
                str(examples / "scenario.yaml"),
                "--runtime",
                str(examples / "runtime-manifest.yaml"),
            ],
            check=True,
        )
    print(json.dumps({"package": plan["package"], "version": plan["version"], "smoke": "passed"}))


if __name__ == "__main__":
    main()
