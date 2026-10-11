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
    AuthenticatedWheel,
    CosignKeyVerifierProfile,
    CosignKeyWheelPolicy,
    EvaluatorTrustError,
    GitHubVerifierProfile,
    GitHubWheelPolicy,
    authenticate_wheel,
    authenticate_wheel_with_cosign_key,
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


def _verifier(value: object, root: Path) -> GitHubVerifierProfile | CosignKeyVerifierProfile:
    if not isinstance(value, dict):
        raise EvaluatorTrustError("operator verifier must be an object")
    kind = value.get("kind")
    common = {
        "kind",
        "executable",
        "executable_sha256",
        "version",
        "trusted_root",
        "trusted_root_sha256",
    }
    if kind == "github":
        values = _object(value, common)
    elif kind == "cosign_key_no_tlog":
        values = _object(value, common | {"public_key", "public_key_sha256"})
    else:
        raise EvaluatorTrustError("operator must explicitly select github or cosign_key_no_tlog")
    if any(not isinstance(item, str) for item in values.values()):
        raise EvaluatorTrustError("operator verifier fields must be strings")
    arguments = {
        "executable": _path(values["executable"], root),
        "executable_sha256": values["executable_sha256"],
        "version": values["version"],
        "trusted_root": _path(values["trusted_root"], root),
        "trusted_root_sha256": values["trusted_root_sha256"],
    }
    try:
        if kind == "github":
            return GitHubVerifierProfile(**arguments)
        return CosignKeyVerifierProfile(
            **arguments,
            public_key=_path(values["public_key"], root),
            public_key_sha256=values["public_key_sha256"],
        )
    except EvaluatorTrustError:
        raise
    except (TypeError, ValueError) as error:
        raise EvaluatorTrustError("operator verifier has invalid field values") from error


def _profile(
    path: Path, evidence_root: Path | None
) -> tuple[GitHubVerifierProfile | CosignKeyVerifierProfile, list[Any]]:
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
    profile = _verifier(data["verifier"], path.parent)
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


def _authenticate_binding(
    binding: dict[str, Any],
    profile: GitHubVerifierProfile | CosignKeyVerifierProfile,
    root: Path,
    expected_digest: str,
) -> AuthenticatedWheel:
    if isinstance(profile, GitHubVerifierProfile):
        publisher = _publisher(binding["publisher"])
        if publisher.wheel_sha256 != expected_digest:
            raise EvaluatorTrustError("operator policy wheel subject differs from scenario binding")
        return authenticate_wheel(
            _path(binding["wheel"], root),
            _path(binding["bundle"], root),
            policy=publisher,
            profile=profile,
        )
    values = _object(
        binding["publisher"], {"wheel_sha256", "predicate_type", "public_key_sha256", "trust_mode"}
    )
    if any(not isinstance(item, str) for item in values.values()):
        raise EvaluatorTrustError("key-only publisher fields must be strings")
    publisher_key = CosignKeyWheelPolicy(**values)
    if publisher_key.wheel_sha256 != expected_digest:
        raise EvaluatorTrustError("operator policy wheel subject differs from scenario binding")
    return authenticate_wheel_with_cosign_key(
        _path(binding["wheel"], root),
        _path(binding["bundle"], root),
        policy=publisher_key,
        profile=profile,
    )


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
        requirement = expected[namespace]
        wheel = _authenticate_binding(
            binding, profile, path.parent, str(requirement["artifact_sha256"])
        )
        validate_evaluator_wheel(wheel)
        captured[namespace] = verify_installed_wheel(
            wheel, distribution(str(requirement["distribution"]))
        )
    if set(captured) != set(expected):
        raise EvaluatorTrustError("operator profile is missing declared evaluator authentications")
    return MappingProxyType(captured)
