from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/release.yml"


def workflow() -> dict[str, Any]:
    # BaseLoader preserves GitHub's YAML `on` key and scalar expressions literally.
    return dict(yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader))


def test_dispatch_is_always_explicit_and_cannot_enable_publishing() -> None:
    data = workflow()
    assert data["on"]["push"]["tags"] == ["contracts-v*", "harness-v*"]
    inputs = data["on"]["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"candidate"}
    assert inputs["candidate"]["required"] == "true"
    assert "default" not in inputs["candidate"]
    jobs = data["jobs"]
    assert (
        jobs["publish-pypi"]["if"]
        == "github.event_name == 'push' && vars.PYPI_PUBLISH_ENABLED == 'true'"
    )
    assert (
        jobs["github-release"]["if"]
        == "github.event_name == 'push' && needs.publish-pypi.result == 'success'"
    )
    assert jobs["publish-pypi"]["needs"] == "build"
    assert set(jobs["github-release"]["needs"]) == {"build", "publish-pypi"}
    # Neither failure, cancellation nor skipped PyPI publication satisfies success.
    for result in ("failure", "cancelled", "skipped"):
        assert f"== '{result}'" not in jobs["github-release"]["if"]


def test_actions_are_pinned_and_oidc_is_limited_to_publication_jobs() -> None:
    data = workflow()
    assert data["permissions"] == {"contents": "read"}
    jobs = data["jobs"]
    assert jobs["build"]["permissions"] == {"contents": "read"}
    assert (
        jobs["publish-pypi"]["environment"]["name"] == "${{ needs.build.outputs.pypi_environment }}"
    )
    assert (
        jobs["build"]["outputs"]["pypi_environment"] == "${{ steps.plan.outputs.pypi_environment }}"
    )
    assert jobs["publish-pypi"]["permissions"] == {"contents": "read", "id-token": "write"}
    assert jobs["github-release"]["permissions"] == {
        "contents": "write",
        "attestations": "write",
        "id-token": "write",
    }
    for job in jobs.values():
        for step in job["steps"]:
            if "uses" in step:
                assert re.fullmatch(r"[\w-]+/[\w-]+@[0-9a-f]{40}", step["uses"])


def test_validated_artifacts_are_handed_to_publication_without_rebuilding() -> None:
    jobs = workflow()["jobs"]
    steps = jobs["build"]["steps"]
    runs = [step.get("run", "") for step in steps]
    build = next(index for index, run in enumerate(runs) if "uv build " in run)
    verify = next(
        index for index, run in enumerate(runs) if "scripts.release.verify_install" in run
    )
    upload = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Upload validated distributions"
    )
    assert build < verify < upload
    assert "--no-sources" in runs[build]
    assert "if" not in steps[upload]  # default success(), never always()
    artifact = steps[upload]["with"]["name"].replace("steps.plan", "needs.build")
    for name in ("publish-pypi", "github-release"):
        steps = jobs[name]["steps"]
        assert steps[0]["with"]["name"] == artifact
        assert not any("uv build" in step.get("run", "") for step in steps)
    publish = jobs["publish-pypi"]["steps"][1]
    assert publish["with"] == {"packages-dir": "dist/", "attestations": "true"}
