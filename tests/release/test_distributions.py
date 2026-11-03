from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest

from scripts.release import verify_install as verify
from scripts.release.plan import ReleaseError, ReleasePlan


@pytest.fixture
def plan() -> ReleasePlan:
    return ReleasePlan(
        candidate="contracts-v0.17.0",
        key="contracts",
        package="robotics-runtime-contracts",
        version="0.17.0",
        commit="commit",
        tree="tree",
        source_date_epoch="1234567890",
        dry_run=True,
    )


def archives(
    directory: Path,
    *,
    name: str = "robotics-runtime-contracts",
    version: str = "0.17.0",
    dependencies: tuple[str, ...] = (),
) -> list[Path]:
    directory.mkdir(exist_ok=True)
    stem = f"{name.replace('-', '_')}-{version}"
    metadata = f"Metadata-Version: 2.3\nName: {name}\nVersion: {version}\n"
    metadata += "".join(f"Requires-Dist: {item}\n" for item in dependencies)
    raw = metadata.encode()
    wheel = directory / f"{stem}-py3-none-any.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr(f"{stem}.dist-info/METADATA", raw)
    sdist = directory / f"{stem}.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        info = tarfile.TarInfo(f"{stem}/PKG-INFO")
        info.size = len(raw)
        archive.addfile(info, io.BytesIO(raw))
    return [wheel, sdist]


def test_both_distribution_metadata_are_checked_and_uv_marker_is_allowed(
    tmp_path: Path, plan: ReleasePlan
) -> None:
    expected = archives(tmp_path)
    (tmp_path / ".gitignore").write_text("*", encoding="utf-8")
    assert verify.validate_distributions(tmp_path, plan) == expected


@pytest.mark.parametrize("index", [0, 1])
def test_each_archive_must_have_the_candidate_identity(
    tmp_path: Path, plan: ReleasePlan, index: int
) -> None:
    artifacts = archives(tmp_path)
    wrong = archives(tmp_path / "wrong", version="0.18.0")
    artifacts[index].unlink()
    wrong[index].replace(tmp_path / wrong[index].name)
    # Remove the fixture staging directory from the directory under validation.
    wrong[1 - index].unlink()
    (tmp_path / "wrong").rmdir()
    with pytest.raises(ReleaseError, match="does not match candidate"):
        verify.validate_distributions(tmp_path, plan)


@pytest.mark.parametrize("extra", ["stale.whl", "surprise.txt"])
def test_extra_distributions_and_files_cannot_be_uploaded(
    tmp_path: Path, plan: ReleasePlan, extra: str
) -> None:
    archives(tmp_path)
    (tmp_path / extra).write_text("unexpected", encoding="utf-8")
    with pytest.raises(ReleaseError):
        verify.validate_distributions(tmp_path, plan)


def test_missing_sdist_fails(tmp_path: Path, plan: ReleasePlan) -> None:
    archives(tmp_path)[1].unlink()
    with pytest.raises(ReleaseError, match="one wheel and one sdist"):
        verify.validate_distributions(tmp_path, plan)


def test_filename_cannot_disguise_different_metadata(tmp_path: Path) -> None:
    wheel = archives(tmp_path)[0]
    renamed = wheel.with_name(wheel.name.replace("0.17.0", "0.18.0"))
    wheel.rename(renamed)
    with pytest.raises(ReleaseError, match="filename and metadata disagree"):
        verify.distribution_metadata(renamed)


def test_duplicate_wheel_metadata_fails(tmp_path: Path) -> None:
    wheel = archives(tmp_path)[0]
    with ZipFile(wheel, "a") as archive:
        archive.writestr("other.dist-info/METADATA", "Name: other\nVersion: 1.0\n")
    with pytest.raises(ReleaseError, match="exactly one METADATA"):
        verify.distribution_metadata(wheel)


def test_sdist_metadata_must_be_a_regular_file(tmp_path: Path) -> None:
    sdist = archives(tmp_path)[1]
    with tarfile.open(sdist, "w:gz") as archive:
        info = tarfile.TarInfo("package/PKG-INFO")
        info.type = tarfile.SYMTYPE
        info.linkname = "../../outside"
        archive.addfile(info)
    with pytest.raises(ReleaseError, match="root PKG-INFO"):
        verify.distribution_metadata(sdist)


def test_built_metadata_cannot_add_a_git_dependency(tmp_path: Path, plan: ReleasePlan) -> None:
    archives(tmp_path, dependencies=("other @ git+https://example.org/source.git",))
    with pytest.raises(ReleaseError, match="index version requirements"):
        verify.validate_distributions(tmp_path, plan)


def test_harness_archive_requirement_must_match_the_released_minor(
    tmp_path: Path, plan: ReleasePlan
) -> None:
    archives(
        tmp_path,
        name="robotics-acceptance-harness",
        version="0.19.0",
        dependencies=("robotics-runtime-contracts>=0.17,<0.18",),
    )
    harness = replace(
        plan,
        candidate="harness-v0.19.0",
        key="harness",
        package="robotics-acceptance-harness",
        version="0.19.0",
        contracts_version="0.18.0",
        contracts_requirement="robotics-runtime-contracts<0.19,>=0.18",
    )
    with pytest.raises(ReleaseError, match="requirement must be"):
        verify.validate_distributions(tmp_path, harness)


def test_clean_environment_removes_python_and_index_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "PYTHONPATH",
        "PYTHONHOME",
        "UV_INDEX",
        "UV_PROJECT_ENVIRONMENT",
        "PIP_CONFIG_FILE",
        "PIP_INDEX_URL",
        "VIRTUAL_ENV",
    ):
        monkeypatch.setenv(name, "untrusted")
    env = verify.clean_environment()
    assert not any(key.startswith(("UV_", "PIP_")) for key in env)
    assert {key for key in env if key.startswith("PYTHON")} == {"PYTHONNOUSERSITE"}
    assert "VIRTUAL_ENV" not in env


@pytest.mark.parametrize("install_fails", [False, True])
def test_clean_install_uses_only_exact_archive_and_pypi_in_a_separate_environment(
    tmp_path: Path, plan: ReleasePlan, monkeypatch: pytest.MonkeyPatch, install_fails: bool
) -> None:
    workspace = tmp_path / "workspace"
    examples = workspace / "packages/contracts/consumer-examples/minimal-simulation"
    examples.mkdir(parents=True)
    (examples / "scenario.yaml").write_text("{}", encoding="utf-8")
    artifact = archives(tmp_path)[0]
    captured: list[tuple[list[str], Path, dict[str, str]]] = []

    def run(command: list[str], *, cwd: Path, env: dict[str, str], check: bool) -> Any:
        assert check
        captured.append((command, cwd, env))
        if install_fails and "install" in command:
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", run)
    harness = replace(plan, contracts_version="0.17.0")
    if install_fails:
        with pytest.raises(subprocess.CalledProcessError):
            verify.clean_install(
                artifact, harness, workspace=workspace, interpreter="3.12", uv="uv"
            )
    else:
        result = verify.clean_install(
            artifact, harness, workspace=workspace, interpreter="3.12", uv="uv"
        )
        assert result["status"] == "passed"
        assert captured[-1][0][1:] == ["-I", "smoke.py", "plan.json"]
    install = captured[1][0]
    assert install[:4] == ["uv", "--no-config", "pip", "install"]
    assert "--no-sources" in install
    assert install[install.index("--default-index") + 1] == "https://pypi.org/simple"
    assert install[-1] == "robotics-runtime-contracts==0.17.0"
    assert Path(install[-2]).name == artifact.name
    for _, cwd, env in captured:
        assert not cwd.is_relative_to(workspace)
        assert "PYTHONPATH" not in env and "VIRTUAL_ENV" not in env


def test_temp_directory_inside_workspace_is_rejected(
    tmp_path: Path, plan: ReleasePlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    with pytest.raises(ReleaseError, match="outside the workspace"):
        verify.clean_install(
            tmp_path / "unused.whl", plan, workspace=tmp_path, interpreter="3.12", uv="uv"
        )


@pytest.mark.parametrize("tamper", ["source", "copy"])
def test_wire_contracts_digest_is_checked_before_any_installed_code(
    tmp_path: Path, plan: ReleasePlan, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    import shutil
    from hashlib import sha256

    wheel = tmp_path / "contracts.whl"
    wheel.write_bytes(b"original contracts")
    expected = sha256(wheel.read_bytes()).hexdigest()
    copy = shutil.copyfile

    def copying(source: Path, destination: Path, **kwargs: Any) -> Path:
        result = copy(source, destination, **kwargs)
        if source == wheel:
            Path(destination).write_bytes(b"changed copy")
        return Path(result)

    if tamper == "source":
        wheel.write_bytes(b"changed source")
    else:
        monkeypatch.setattr(shutil, "copyfile", copying)
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: pytest.fail("installer or target code ran")
    )
    with pytest.raises(ReleaseError, match="contracts wheel digest differs"):
        verify.clean_install(
            None,
            plan,
            workspace=tmp_path,
            interpreter="3.12",
            uv="uv",
            additional_artifacts=(wheel,),
            wire_consumer=True,
            contracts_wheel_sha256=expected,
        )


@pytest.mark.parametrize("available", [True, False])
def test_harness_release_cannot_bypass_authenticated_contracts_or_either_archive(
    tmp_path: Path,
    plan: ReleasePlan,
    monkeypatch: pytest.MonkeyPatch,
    available: bool,
) -> None:
    from scripts.release import verified_contracts

    selected = replace(
        plan,
        candidate="harness-v0.23.0",
        key="harness",
        package="robotics-acceptance-harness",
        version="0.23.0",
        contracts_version="0.22.0",
    )
    document = tmp_path / "plan.json"
    document.write_text(json.dumps(asdict(selected)))
    artifacts = [tmp_path / "harness.whl", tmp_path / "harness.tar.gz"]
    contracts = tmp_path / "contracts.whl"
    calls: list[tuple[Path, dict[str, Any]]] = []

    def authenticated(*_args: Any) -> tuple[Path, dict[str, str]]:
        if not available:
            raise ReleaseError("selected contracts release is not authenticated")
        return contracts, {"sha256": "a" * 64, "scope": "unit routing, not a real release"}

    def installed(artifact: Path, _plan: ReleasePlan, **kwargs: Any) -> dict[str, str]:
        calls.append((artifact, kwargs))
        assert kwargs["additional_artifacts"] == (contracts,)
        assert kwargs["wire_consumer"] is True
        assert kwargs["contracts_wheel_sha256"] == "a" * 64
        return {"status": "passed"}

    monkeypatch.setattr(verify, "validate_distributions", lambda *_: artifacts)
    monkeypatch.setattr(
        verify, "distribution_metadata", lambda *_: ("robotics-runtime-contracts", "0.22.0", [])
    )
    monkeypatch.setattr(verified_contracts, "authenticate_contracts", authenticated)
    monkeypatch.setattr(verify, "clean_install", installed)
    monkeypatch.setattr("shutil.which", lambda *_: "uv")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "verify_install",
            "--plan",
            str(document),
            "--dist",
            str(tmp_path),
            "--workspace",
            str(tmp_path),
            "--repository",
            "mmkolpakov/robotics-runtime",
            "--report",
            str(tmp_path / "result.json"),
        ],
    )
    if available:
        assert verify.main() == 0
        assert [artifact for artifact, _ in calls] == artifacts
    else:
        with pytest.raises(SystemExit) as error:
            verify.main()
        assert error.value.code == 1
        assert not calls and not (tmp_path / "result.json").exists()


def test_additional_archive_cannot_admit_an_unrelated_dependency(
    tmp_path: Path,
    plan: ReleasePlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from hashlib import sha256

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    foreign = archives(tmp_path / "foreign", name="unrelated-dependency", version="0.17.0")[0]
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("installer ran"))
    with pytest.raises(ReleaseError, match="selected package or contracts prerequisite"):
        verify.clean_install(
            None,
            replace(plan, contracts_version="0.17.0"),
            workspace=workspace,
            interpreter="3.12",
            uv="uv",
            additional_artifacts=(foreign,),
            wire_consumer=True,
            contracts_wheel_sha256=sha256(foreign.read_bytes()).hexdigest(),
        )
