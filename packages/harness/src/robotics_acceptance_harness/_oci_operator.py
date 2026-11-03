"""Closed operator configuration for the optional local OCI evaluator."""

from __future__ import annotations

import hashlib
import os
import stat
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from packaging.version import Version
from robotics_runtime_contracts import loads_mapping

from robotics_acceptance_harness._oci_manifest_trust import _platform
from robotics_acceptance_harness.evaluator_json import MAX_PACKET_BYTES
from robotics_acceptance_harness.evaluator_trust import (
    DEFAULT_TRUST_LIMITS,
    CosignKeyVerifierProfile,
    EvaluatorTrustError,
    _pinned_snapshot,
    _sha256,
    read_once,
)
from robotics_acceptance_harness.operator_trust import _object, _path

_LIMIT_NAMES = {
    "attempt_timeout_sec",
    "command_timeout_sec",
    "cleanup_timeout_sec",
    "stdout_bytes",
    "stderr_bytes",
    "memory_bytes",
    "input_bytes",
    "pids",
    "cpus",
    "tmpfs_bytes",
}


@dataclass(frozen=True, slots=True)
class _OCIProfile:
    sha256: str
    verifier: CosignKeyVerifierProfile
    engine: Mapping[str, Any]
    limits: Mapping[str, int]
    evaluators: Mapping[str, Mapping[str, Any]]


def _absolute(value: object, root: Path) -> Path:
    return Path(os.path.abspath(_path(value, root)))


def _outside_evidence(path: Path, evidence_root: Path | None) -> None:
    if evidence_root is not None and path.is_relative_to(evidence_root.resolve()):
        raise EvaluatorTrustError("operator engine configuration must be outside evidence")


def _directory(value: object, root: Path, evidence_root: Path | None) -> Path:
    path = _absolute(value, root)
    _outside_evidence(path, evidence_root)
    if path.resolve(strict=True) != path:
        raise EvaluatorTrustError("operator context directories must not contain symlinks")
    observed = path.stat()
    if not stat.S_ISDIR(observed.st_mode) or observed.st_uid != os.getuid():
        raise EvaluatorTrustError("operator context requires preprovisioned owned directories")
    if observed.st_mode & 0o022:
        raise EvaluatorTrustError("operator context must not be group/other writable")
    return path


def _configuration(value: object, root: Path, evidence_root: Path | None) -> Mapping[str, Any]:
    fields = _object(value, {"path", "sha256"})
    path = _absolute(fields["path"], root)
    _outside_evidence(path, evidence_root)
    if not isinstance(fields["sha256"], str):
        raise EvaluatorTrustError("operator configuration digest must be a string")
    _sha256(fields["sha256"])
    raw = _pinned_snapshot(path, fields["sha256"], DEFAULT_TRUST_LIMITS.max_root_bytes)
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as failure:
        raise EvaluatorTrustError("operator configuration is not valid TOML") from failure
    return MappingProxyType({"path": path, "sha256": fields["sha256"], "raw": raw, "data": data})


def _verifier(value: object, root: Path) -> CosignKeyVerifierProfile:
    fields = _object(
        value,
        {
            "kind",
            "executable",
            "executable_sha256",
            "version",
            "public_key",
            "public_key_sha256",
            "trusted_root",
            "trusted_root_sha256",
        },
    )
    if fields["kind"] != "cosign_blob_key_no_tlog" or any(
        not isinstance(item, str) for item in fields.values()
    ):
        raise EvaluatorTrustError("OCI profile requires explicit Cosign blob key-only trust")
    profile = CosignKeyVerifierProfile(
        _absolute(fields["executable"], root),
        fields["executable_sha256"],
        fields["version"],
        _absolute(fields["public_key"], root),
        fields["public_key_sha256"],
        _absolute(fields["trusted_root"], root),
        fields["trusted_root_sha256"],
    )
    if Version(profile.version) < Version("3.1.4"):
        raise EvaluatorTrustError("OCI profile requires an admitted Cosign >=3.1.4")
    return profile


def _limits(value: object) -> Mapping[str, int]:
    fields = _object(value, _LIMIT_NAMES)
    if any(type(item) is not int or not 0 < item <= 2**63 - 1 for item in fields.values()):
        raise EvaluatorTrustError("OCI limits must be positive bounded integers")
    if fields["stdout_bytes"] > MAX_PACKET_BYTES:
        raise EvaluatorTrustError("OCI stdout limit exceeds the evaluator packet limit")
    if fields["stderr_bytes"] > DEFAULT_TRUST_LIMITS.max_report_bytes:
        raise EvaluatorTrustError("OCI stderr limit exceeds the capture limit")
    if any(
        fields[name] > 86_400
        for name in ("attempt_timeout_sec", "command_timeout_sec", "cleanup_timeout_sec")
    ):
        raise EvaluatorTrustError("OCI timeout limit exceeds one day")
    if fields["command_timeout_sec"] > fields["attempt_timeout_sec"]:
        raise EvaluatorTrustError("OCI command timeout exceeds the attempt timeout")
    return MappingProxyType(fields)


def _storage(configuration: Mapping[str, Any], store: Mapping[str, Any]) -> None:
    values = configuration["data"].get("storage")
    if not isinstance(values, dict) or any(
        values.get(key) != str(store[field])
        for key, field in (
            ("graphroot", "graph_root"),
            ("runroot", "run_root"),
            ("driver", "driver"),
        )
    ):
        raise EvaluatorTrustError("storage configuration differs from the selected project store")
    if values.get("rootless_storage_path") not in (None, "", str(store["graph_root"])):
        raise EvaluatorTrustError("rootless storage path differs from the selected project store")
    options = values.get("options", {})
    if (
        values.get("imagestore")
        or not isinstance(options, dict)
        or options.get("additionalimagestores")
    ):
        raise EvaluatorTrustError("OCI profile does not admit additional image stores")


def _user_bus(address: str, evidence_root: Path | None) -> None:
    prefix = "unix:path="
    if not address.startswith(prefix) or any(char in address for char in (";", ",", "%", "\\")):
        raise EvaluatorTrustError("engine requires one explicit local user-bus path")
    path = Path(address[len(prefix) :])
    _outside_evidence(path, evidence_root)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise EvaluatorTrustError("engine user-bus path must be absolute and contain no symlinks")
    observed = path.stat()
    if not stat.S_ISSOCK(observed.st_mode) or observed.st_uid != os.getuid():
        raise EvaluatorTrustError("engine user-bus must be an existing owned local socket")


def _engine_configuration(
    configuration: Mapping[str, Any],
    store: Mapping[str, Any],
    root: Path,
    evidence_root: Path | None,
) -> None:
    expected = {
        "lock_type": "file",
        "tmp_dir": str(store["tmpdir"]),
        "static_dir": str(store["graph_root"] / "libpod"),
        "volume_path": str(store["graph_root"] / "volumes"),
    }
    values = configuration["data"].get("engine")
    if not isinstance(values, dict) or any(
        values.get(key) != value for key, value in expected.items()
    ):
        raise EvaluatorTrustError("engine configuration differs from the selected project context")
    for name in ("static_dir", "volume_path"):
        _directory(expected[name], root, evidence_root)


def _environment(value: object, root: Path, evidence_root: Path | None) -> Mapping[str, str]:
    environment = _object(value, {"HOME", "XDG_RUNTIME_DIR", "PATH", "DBUS_SESSION_BUS_ADDRESS"})
    if any(
        not isinstance(item, str) or not item or "\x00" in item for item in environment.values()
    ):
        raise EvaluatorTrustError("engine environment must contain explicit nonempty strings")
    if any(not Path(item).is_absolute() for item in environment["PATH"].split(os.pathsep)):
        raise EvaluatorTrustError("engine PATH must contain only explicit absolute entries")
    _user_bus(environment["DBUS_SESSION_BUS_ADDRESS"], evidence_root)
    home = _directory(environment["HOME"], root, evidence_root)
    runtime = _directory(environment["XDG_RUNTIME_DIR"], root, evidence_root)
    if runtime in {home, Path(f"/run/user/{os.getuid()}"), Path("/")}:
        raise EvaluatorTrustError("engine requires a dedicated project runtime directory")
    return MappingProxyType({**environment, "HOME": str(home), "XDG_RUNTIME_DIR": str(runtime)})


def _engine(value: object, root: Path, evidence_root: Path | None) -> Mapping[str, Any]:
    from pwd import getpwuid

    fields = _object(
        value,
        {
            "backend",
            "executable",
            "executable_sha256",
            "version",
            "environment",
            "containers_conf",
            "storage_conf",
            "store",
            "hooks_dir",
        },
    )
    if fields["backend"] != "podman_local" or fields["version"] != "4.9.3":
        raise EvaluatorTrustError("OCI profile requires the supported local Podman 4.9.3 backend")
    environment = _environment(fields["environment"], root, evidence_root)
    home = Path(environment["HOME"])
    account_home = Path(getpwuid(os.getuid()).pw_dir).resolve()
    store = _object(fields["store"], {"graph_root", "run_root", "tmpdir", "driver"})
    paths = {
        name: _directory(store[name], root, evidence_root)
        for name in ("graph_root", "run_root", "tmpdir")
    }
    if paths["graph_root"] in {
        home / ".local/share/containers/storage",
        account_home / ".local/share/containers/storage",
        home,
        account_home,
        Path("/"),
    }:
        raise EvaluatorTrustError("engine must not use the default shared HOME store")
    if not isinstance(store["driver"], str) or not store["driver"]:
        raise EvaluatorTrustError("engine storage driver must be explicit")
    selected_store = MappingProxyType({**paths, "driver": store["driver"]})
    hooks = _directory(fields["hooks_dir"], root, evidence_root)
    with os.scandir(hooks) as entries:
        if next(entries, None) is not None:
            raise EvaluatorTrustError("engine hooks directory must be empty")
    containers = _configuration(fields["containers_conf"], root, evidence_root)
    storage = _configuration(fields["storage_conf"], root, evidence_root)
    _storage(storage, selected_store)
    _engine_configuration(containers, selected_store, root, evidence_root)
    executable = _absolute(fields["executable"], root)
    _outside_evidence(executable, evidence_root)
    if not isinstance(fields["executable_sha256"], str):
        raise EvaluatorTrustError("engine executable digest must be a string")
    _sha256(fields["executable_sha256"])
    binary = _pinned_snapshot(
        executable, fields["executable_sha256"], DEFAULT_TRUST_LIMITS.max_tool_bytes
    )
    return MappingProxyType(
        {
            "backend": "podman_local",
            "version": "4.9.3",
            "executable": executable,
            "executable_sha256": fields["executable_sha256"],
            "executable_bytes": binary,
            "environment": environment,
            "containers_conf": MappingProxyType(
                {key: containers[key] for key in ("path", "sha256", "raw")}
            ),
            "storage_conf": MappingProxyType(
                {key: storage[key] for key in ("path", "sha256", "raw")}
            ),
            "store": selected_store,
            "hooks_dir": hooks,
        }
    )


def _requirements(requirements: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    expected: dict[str, str] = {}
    for item in requirements:
        namespace = item.get("namespace")
        subject = item.get("execution_subject")
        if item.get("kind") != "oci" or not isinstance(namespace, str) or namespace in expected:
            raise EvaluatorTrustError("OCI requirements need distinct declared namespaces")
        if not isinstance(subject, Mapping) or subject.get("kind") != "oci_image":
            raise EvaluatorTrustError("OCI requirement needs an image execution subject")
        if "provenance_receipt_sha256" in subject:
            raise EvaluatorTrustError(
                "OCI execution profile does not yet support provenance receipts"
            )
        digest = subject.get("digest")
        if not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise EvaluatorTrustError("OCI requirement needs an exact sha256 image digest")
        _sha256(digest[7:])
        expected[namespace] = digest
    return expected


def _image_reference(value: object, digest: str) -> str:
    from urllib.parse import urlsplit

    if (
        not isinstance(value, str)
        or value.startswith("-")
        or len(value) > 2048
        or "\x00" in value
        or any(char.isspace() for char in value)
    ):
        raise EvaluatorTrustError("OCI image reference must be a fully qualified immutable name")
    repository, marker, observed = value.rpartition("@")
    if marker != "@" or observed != digest or "@" in repository or "\\" in repository:
        raise EvaluatorTrustError("OCI image reference must match the declared manifest digest")
    parsed = urlsplit("//" + repository)
    host = parsed.hostname
    port = parsed.port
    if (
        not host
        or not parsed.path.startswith("/")
        or len(parsed.path) < 2
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not ("." in host or ":" in host or host == "localhost" or port is not None)
    ):
        raise EvaluatorTrustError("OCI image reference must include an explicit registry")
    return value


def _bindings(
    value: object, expected: Mapping[str, str], root: Path
) -> Mapping[str, Mapping[str, Any]]:
    if not isinstance(value, list) or len(value) > 64:
        raise EvaluatorTrustError("OCI profile requires at most 64 evaluator bindings")
    captured: dict[str, Mapping[str, Any]] = {}
    for raw in value:
        item = _object(
            raw,
            {
                "namespace",
                "image_ref",
                "manifest",
                "config",
                "bundle",
                "manifest_sha256",
                "platform",
                "invocation",
            },
        )
        namespace = item["namespace"]
        if not isinstance(namespace, str) or namespace not in expected or namespace in captured:
            raise EvaluatorTrustError("OCI profile has a duplicate or undeclared namespace")
        if not isinstance(item["manifest_sha256"], str):
            raise EvaluatorTrustError("OCI manifest pin must be a string")
        _sha256(item["manifest_sha256"])
        if "sha256:" + item["manifest_sha256"] != expected[namespace]:
            raise EvaluatorTrustError("operator manifest pin differs from the method requirement")
        if item["invocation"] != "evaluator_json_v1":
            raise EvaluatorTrustError("OCI profile requires the fixed evaluator JSON invocation")
        captured[namespace] = MappingProxyType(
            {
                "namespace": namespace,
                "image_ref": _image_reference(item["image_ref"], expected[namespace]),
                "manifest_sha256": item["manifest_sha256"],
                "manifest": _absolute(item["manifest"], root),
                "config": _absolute(item["config"], root),
                "bundle": _absolute(item["bundle"], root),
                "platform": MappingProxyType(_platform(item["platform"])),
                "invocation": "evaluator_json_v1",
            }
        )
    if set(captured) != set(expected):
        raise EvaluatorTrustError("OCI profile is missing declared evaluator bindings")
    return MappingProxyType(captured)


def load_oci_profile(
    profile_path: str | Path,
    requirements: Sequence[Mapping[str, Any]],
    *,
    evidence_root: str | Path | None = None,
) -> _OCIProfile:
    """Capture operator configuration without invoking tools or admitting an image."""
    if os.name != "posix":
        raise EvaluatorTrustError("OCI profile capture requires the POSIX input profile")
    path = Path(os.path.abspath(Path(profile_path).expanduser()))
    evidence = None if evidence_root is None else Path(evidence_root)
    _outside_evidence(path, evidence)
    try:
        raw = read_once(path, 4 * 1024 * 1024, forbid_group_other_write=True)
        values = _object(
            loads_mapping(raw, source_name=str(path)),
            {
                "profile_version",
                "verifier",
                "engine",
                "limits",
                "evaluators",
            },
        )
        if type(values["profile_version"]) is not int or values["profile_version"] != 2:
            raise EvaluatorTrustError("unsupported OCI operator profile version")
        expected = _requirements(requirements)
        bindings = _bindings(values["evaluators"], expected, path.parent)
        return _OCIProfile(
            hashlib.sha256(raw).hexdigest(),
            _verifier(values["verifier"], path.parent),
            _engine(values["engine"], path.parent, evidence),
            _limits(values["limits"]),
            bindings,
        )
    except EvaluatorTrustError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as failure:
        raise EvaluatorTrustError(f"invalid OCI operator profile: {failure}") from failure
