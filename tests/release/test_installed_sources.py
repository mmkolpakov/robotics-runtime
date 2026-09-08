from __future__ import annotations

import json
import sys
from hashlib import sha256
from importlib.metadata import PathDistribution
from pathlib import Path
from typing import Any

import pytest

from scripts.release import smoke


@pytest.fixture
def installed_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, Any], Path, Path]:
    module = tmp_path / "robotics_runtime_contracts"
    module.mkdir()
    source = module / "__init__.py"
    source.write_bytes(b"published source\n")
    metadata = tmp_path / "robotics_runtime_contracts-0.17.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Name: robotics-runtime-contracts\nVersion: 0.17.0\n", encoding="utf-8"
    )
    (metadata / "RECORD").write_text("robotics_runtime_contracts/__init__.py,,\n", encoding="utf-8")
    (metadata / "direct_url.json").write_text(
        json.dumps({"url": "file:///candidate.whl", "archive_info": {}}), encoding="utf-8"
    )
    installed = PathDistribution(metadata)
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    monkeypatch.setattr(smoke, "distribution", lambda name: installed)
    monkeypatch.setattr(smoke, "distributions", lambda: [installed])
    plan = {
        "package": "robotics-runtime-contracts",
        "version": "0.17.0",
        "contracts_version": "0.17.0",
        "source_files": {
            "robotics-runtime-contracts": {
                "robotics_runtime_contracts/__init__.py": sha256(source.read_bytes()).hexdigest()
            }
        },
    }
    return plan, source, metadata


def test_matching_installed_bytes_and_inventory_pass(
    installed_sources: tuple[dict[str, Any], Path, Path],
) -> None:
    smoke.verify_installed_sources(installed_sources[0])


def test_same_version_but_different_published_bytes_fail(
    installed_sources: tuple[dict[str, Any], Path, Path],
) -> None:
    plan, source, _ = installed_sources
    source.write_bytes(b"unreleased source\n")
    with pytest.raises(RuntimeError, match="differs from the checked release source"):
        smoke.verify_installed_sources(plan)


@pytest.mark.parametrize(
    "record",
    ["", "robotics_runtime_contracts/__init__.py,,\nrobotics_runtime_contracts/extra.py,,\n"],
)
def test_missing_or_extra_installed_source_fails(
    installed_sources: tuple[dict[str, Any], Path, Path], record: str
) -> None:
    plan, _, metadata = installed_sources
    (metadata / "RECORD").write_text(record, encoding="utf-8")
    if "extra.py" in record:
        (metadata.parent / "robotics_runtime_contracts/extra.py").write_bytes(b"extra source\n")
    with pytest.raises(RuntimeError, match="inventory differs"):
        smoke.verify_installed_sources(plan)


@pytest.mark.parametrize(
    "origin",
    [
        {"dir_info": {"editable": True}},
        {"vcs_info": {"vcs": "git"}},
        {"archive_info": {}, "dir_info": {}},
    ],
)
def test_editable_or_vcs_install_is_rejected(
    installed_sources: tuple[dict[str, Any], Path, Path], origin: dict[str, Any]
) -> None:
    plan, _, metadata = installed_sources
    (metadata / "direct_url.json").write_text(json.dumps(origin), encoding="utf-8")
    with pytest.raises(RuntimeError, match="non-index or editable"):
        smoke.verify_installed_sources(plan)


def test_contracts_dependency_must_come_from_pypi_even_when_bytes_match(
    installed_sources: tuple[dict[str, Any], Path, Path],
) -> None:
    plan, _, _ = installed_sources
    plan["package"] = "robotics-acceptance-harness"
    with pytest.raises(RuntimeError, match="non-index or editable dependency"):
        smoke.verify_installed_sources(plan)


def test_imported_source_outside_the_clean_venv_fails(
    installed_sources: tuple[dict[str, Any], Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, source, _ = installed_sources
    monkeypatch.setattr(sys, "prefix", str(source.parent / "different-venv"))
    with pytest.raises(RuntimeError, match="differs from the checked release source"):
        smoke.verify_installed_sources(plan)
