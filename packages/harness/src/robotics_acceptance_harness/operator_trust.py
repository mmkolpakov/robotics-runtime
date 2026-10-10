"""Load one reviewed operator profile for evaluator wheel/source admission."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import fields
from importlib.metadata import distribution
from pathlib import Path
from types import MappingProxyType
from typing import Any

from robotics_runtime_contracts import loads_mapping

from robotics_acceptance_harness.evaluator_trust import (
    AuthenticatedInstallation,
    EvaluatorTrustError,
    GitHubVerifierProfile,
    GitHubWheelPolicy,
    authenticate_wheel,
    read_once,
    validate_evaluator_wheel,
    verify_installed_wheel,
)


def _object(value: object, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise EvaluatorTrustError(f"operator profile requires exactly these fields: {sorted(keys)}")
    return value


def _path(value: object, root: Path) -> Path:
    if not isinstance(value, str) or not value:
        raise EvaluatorTrustError("operator profile requires a nonempty file path")
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def _profile(path: Path, evidence_root: Path | None) -> tuple[GitHubVerifierProfile, list[Any]]:
    path = Path(os.path.abspath(path.expanduser()))
    if evidence_root is not None and path.is_relative_to(evidence_root.resolve()):
        raise EvaluatorTrustError("operator trust profile must be outside the evidence root")
    raw = read_once(path, 4 * 1024 * 1024)
    if path.stat().st_mode & 0o022:
        raise EvaluatorTrustError("operator trust profile must not be group/other writable")
    data = _object(
        loads_mapping(raw, source_name=str(path)), {"profile_version", "verifier", "evaluators"}
    )
    if type(data["profile_version"]) is not int or data["profile_version"] != 1:
        raise EvaluatorTrustError("unsupported evaluator operator profile version")
    values = _object(
        data["verifier"],
        {"executable", "executable_sha256", "version", "trusted_root", "trusted_root_sha256"},
    )
    for key in ("executable_sha256", "version", "trusted_root_sha256"):
        if not isinstance(values[key], str):
            raise EvaluatorTrustError(f"operator verifier {key} must be a string")
    profile = GitHubVerifierProfile(
        executable=_path(values["executable"], path.parent),
        executable_sha256=values["executable_sha256"],
        version=values["version"],
        trusted_root=_path(values["trusted_root"], path.parent),
        trusted_root_sha256=values["trusted_root_sha256"],
    )
    items = data["evaluators"]
    if not isinstance(items, list) or len(items) > 64:
        raise EvaluatorTrustError("operator profile requires at most 64 evaluator bindings")
    return profile, items


def _publisher(value: object) -> GitHubWheelPolicy:
    if not isinstance(value, dict):
        raise EvaluatorTrustError("publisher policy must be an object")
    allowed = {field.name for field in fields(GitHubWheelPolicy)}
    required = {"repository", "certificate_identity", "wheel_sha256"}
    if not required <= set(value) or not set(value) <= allowed:
        raise EvaluatorTrustError("publisher policy has absent or unknown fields")
    nullable = {"source_ref", "source_digest", "signer_digest"}
    for name, item in value.items():
        if name == "deny_self_hosted_runners":
            if type(item) is not bool:
                raise EvaluatorTrustError("publisher runner policy must be boolean")
        elif not isinstance(item, str) and not (name in nullable and item is None):
            raise EvaluatorTrustError(f"publisher {name} must be a string")
    try:
        return GitHubWheelPolicy(**value)
    except EvaluatorTrustError:
        raise
    except (TypeError, ValueError) as error:
        raise EvaluatorTrustError("publisher policy has invalid field values") from error


def load_evaluator_authentications(
    profile_path: str | Path | None,
    requirements: Sequence[Mapping[str, Any]],
    *,
    evidence_root: str | Path | None = None,
) -> Mapping[str, AuthenticatedInstallation]:
    """Authenticate declared evaluators using operator-owned pins, not evidence JSON."""

    if profile_path is None:
        return MappingProxyType({})
    path = Path(os.path.abspath(Path(profile_path).expanduser()))
    root = None if evidence_root is None else Path(evidence_root)
    profile, items = _profile(path, root)
    expected = {str(item["namespace"]): item for item in requirements}
    captured: dict[str, AuthenticatedInstallation] = {}
    for item in items:
        binding = _object(item, {"namespace", "wheel", "bundle", "publisher"})
        namespace = binding["namespace"]
        if not isinstance(namespace, str) or namespace not in expected or namespace in captured:
            raise EvaluatorTrustError(
                "operator profile has duplicate or undeclared evaluator namespace"
            )
        policy = _publisher(binding["publisher"])
        requirement = expected[namespace]
        if policy.wheel_sha256 != requirement["artifact_sha256"]:
            raise EvaluatorTrustError("operator policy wheel subject differs from scenario binding")
        wheel = authenticate_wheel(
            _path(binding["wheel"], path.parent),
            _path(binding["bundle"], path.parent),
            policy=policy,
            profile=profile,
        )
        validate_evaluator_wheel(wheel)
        captured[namespace] = verify_installed_wheel(
            wheel, distribution(str(requirement["distribution"]))
        )
    if set(captured) != set(expected):
        raise EvaluatorTrustError("operator profile is missing declared evaluator authentications")
    return MappingProxyType(captured)
