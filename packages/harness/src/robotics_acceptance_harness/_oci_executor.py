"""One local Podman attempt over private captured evaluator inputs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import time
import uuid
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from robotics_runtime_contracts.writers import write_bytes_atomically

from robotics_acceptance_harness._oci_manifest_trust import _mapping, authenticate_manifest
from robotics_acceptance_harness._oci_operator import _OCIProfile
from robotics_acceptance_harness.evaluator_json import MAX_PACKET_BYTES, MAX_PACKET_ITEMS
from robotics_acceptance_harness.evaluator_trust import (
    DEFAULT_TRUST_LIMITS,
    EvaluatorTrustError,
    _capture_tool,
    read_once,
)

_LABEL = "org.robotics-runtime.evaluator-attempt"
_MOUNT = "/run/robotics-evaluator"
_CID = re.compile(r"[0-9a-f]{64}")


def _private(path: Path, *, directory: bool) -> os.stat_result:
    observed = path.lstat()
    expected = 0o700 if directory else 0o400
    if (
        path.resolve(strict=True) != path.absolute()
        or observed.st_uid != os.getuid()
        or stat.S_IMODE(observed.st_mode) != expected
        or not (stat.S_ISDIR(observed.st_mode) if directory else stat.S_ISREG(observed.st_mode))
    ):
        raise EvaluatorTrustError("OCI attempt inputs must be private owned snapshots")
    return observed


def _inputs(profile: _OCIProfile, packet: bytes, inputs: Path, attempt: Path) -> None:
    _private(attempt, directory=True)
    if inputs != attempt / "inputs" or ":" in str(inputs):
        raise EvaluatorTrustError("OCI inputs must be the fixed private attempt directory")
    _private(inputs, directory=True)
    if {entry.name for entry in inputs.iterdir()} != {"objects", "request.json"}:
        raise EvaluatorTrustError("OCI input directory has unexpected entries")
    _private(inputs / "objects", directory=True)
    total = _private(inputs / "request.json", directory=False).st_size
    if read_once(inputs / "request.json", MAX_PACKET_BYTES) != packet:
        raise EvaluatorTrustError("OCI request snapshot differs from the prepared packet")
    for count, entry in enumerate((inputs / "objects").iterdir(), 1):
        if count > MAX_PACKET_ITEMS or _CID.fullmatch(entry.name) is None:
            raise EvaluatorTrustError("OCI input object names or count differ")
        total += _private(entry, directory=False).st_size
        if total > profile.limits["input_bytes"]:
            raise EvaluatorTrustError("OCI inputs exceed the unique disk budget")
    if total > profile.limits["input_bytes"]:
        raise EvaluatorTrustError("OCI inputs exceed the unique disk budget")


def _info(document: Mapping[str, Any], profile: _OCIProfile) -> None:
    host, store = document.get("host", {}), document.get("store", {})
    expected = profile.engine["store"]
    if (
        host.get("serviceIsRemote") is not False
        or host.get("security", {}).get("rootless") is not True
        or host.get("cgroupManager") != "systemd"
        or host.get("cgroupVersion") != "v2"
        or not {"cpu", "memory", "pids"} <= set(host.get("cgroupControllers", []))
        or any(
            store.get(key) != str(expected[field])
            for key, field in (
                ("graphRoot", "graph_root"),
                ("runRoot", "run_root"),
                ("graphDriverName", "driver"),
            )
        )
        or store.get("volumePath") != str(expected["graph_root"] / "volumes")
    ):
        raise EvaluatorTrustError("Podman facts differ from the selected rootless project context")


class _Attempt:
    def __init__(self, profile: _OCIProfile, namespace: str, directory: Path, deadline: float):
        self.profile = profile
        self.binding = profile.evaluators[namespace]
        self.directory = directory
        self.deadline = deadline
        self.cid: str | None = None
        self.config_sha256: str | None = None
        self.recovering = False
        self.identifier = uuid.uuid4().hex
        self.record: dict[str, Any] = {
            "attempt_id": self.identifier,
            "profile_sha256": profile.sha256,
            "namespace": namespace,
            "phase": "preflight",
            "commands": [],
        }
        self.tools = directory / "operator"
        self.tools.mkdir(mode=0o700)
        for name, payload, mode in (
            ("podman", profile.engine["executable_bytes"], 0o500),
            ("containers.conf", profile.engine["containers_conf"]["raw"], 0o400),
            ("storage.conf", profile.engine["storage_conf"]["raw"], 0o400),
        ):
            path = self.tools / name
            with path.open("xb") as stream:
                stream.write(payload)
            path.chmod(mode)
        self.environment = {
            **profile.engine["environment"],
            "CONTAINERS_CONF": str(self.tools / "containers.conf"),
            "CONTAINERS_STORAGE_CONF": str(self.tools / "storage.conf"),
        }
        journal = directory / "journal.json"
        with journal.open("xb"):
            pass
        journal.chmod(0o600)
        self.save()

    def save(self) -> None:
        raw = json.dumps(self.record, sort_keys=True, ensure_ascii=True).encode()
        if len(raw) > 128 * 1024:
            raise EvaluatorTrustError("OCI attempt journal exceeds its bound")
        write_bytes_atomically(raw, self.directory / "journal.json")

    def observe(self) -> None:
        try:
            self.save()
        except Exception as failure:
            if not self.recovering:
                raise
            self.record["journal_error"] = str(failure)[:4096]

    def command(
        self,
        arguments: list[str],
        deadline: float,
        *,
        response: bool = False,
        expected_exit: int = 0,
    ) -> bytes:
        limits = self.profile.limits
        event: dict[str, Any] = {"operation": arguments[:2], "state": "started"}
        self.record["commands"].append(event)
        self.observe()
        try:
            code, output, diagnostic = _capture_tool(
                [
                    str(self.tools / "podman"),
                    "--remote=false",
                    "--hooks-dir",
                    str(self.profile.engine["hooks_dir"]),
                    *arguments,
                ],
                self.directory,
                environment=self.environment,
                deadline=min(deadline, time.monotonic() + limits["command_timeout_sec"]),
                byte_limits=(
                    limits["stdout_bytes"] if response else MAX_PACKET_BYTES,
                    limits["stderr_bytes"],
                    None,
                ),
            )
        except BaseException:
            event["state"] = "unknown"
            self.observe()
            raise
        event.update(
            {
                "state": "exited",
                "exit_code": code,
                "stdout_sha256": hashlib.sha256(output).hexdigest(),
                "stdout_size": len(output),
                "stderr": diagnostic[:4096].decode("utf-8", errors="replace"),
                "stderr_truncated": len(diagnostic) > 4096,
            }
        )
        self.observe()
        if code != expected_exit:
            raise EvaluatorTrustError(f"Podman {arguments[0]} refused with exit code {code}")
        return output

    def inspect(self, deadline: float) -> dict[str, Any]:
        assert self.cid is not None
        raw = self.command(
            ["container", "inspect", "--format", "{{json .}}", "--", self.cid], deadline
        )
        document = _mapping(raw, "container-inspect")
        if (
            self.config_sha256 is None
            or document.get("Image") not in {self.config_sha256, "sha256:" + self.config_sha256}
            or document.get("Id") != self.cid
            or document.get("ImageName") != self.binding["image_ref"]
            or document.get("Config", {}).get("Labels", {}).get(_LABEL) != self.identifier
        ):
            raise EvaluatorTrustError("Podman container identity differs from this owned attempt")
        transport_digest = document.get("ImageDigest")
        if not isinstance(transport_digest, str) or len(transport_digest) > 256:
            raise EvaluatorTrustError("Podman container transport metadata is malformed")
        self.record["container_transport_digest"] = transport_digest
        self.record["container_image_ref"] = document["ImageName"]
        self.record["container_image_id"] = self.config_sha256
        return document

    def recover(self) -> None:
        self.recovering = True
        deadline = time.monotonic() + self.profile.limits["cleanup_timeout_sec"]
        self.record["phase"] = "unknown"
        self.observe()
        try:
            if self.cid is None:
                candidate = read_once(self.directory / "container.cid", 128).decode().strip()
                if _CID.fullmatch(candidate) is None:
                    return
                self.cid = candidate
            self.inspect(deadline)
            self.record["cid"] = self.cid
            self.command(["stop", "--time", "0", "--", self.cid], deadline)
            state = self.inspect(deadline).get("State", {})
            self.record["cleanup_container_state"] = {
                key: state.get(key) for key in ("Status", "Running", "ExitCode")
            }
        except Exception as failure:
            self.record["cleanup_error"] = str(failure)[:4096]
        finally:
            self.observe()


def _create_arguments(attempt: _Attempt, inputs: Path) -> list[str]:
    limits = attempt.profile.limits
    return [
        "create",
        "--name",
        "rr-evaluator-" + attempt.identifier,
        "--label",
        _LABEL + "=" + attempt.identifier,
        "--cidfile",
        str(attempt.directory / "container.cid"),
        "--pull=never",
        "--network=none",
        "--read-only",
        "--read-only-tmpfs=false",
        "--image-volume=ignore",
        "--no-healthcheck",
        "--http-proxy=false",
        "--log-driver=none",
        "--restart=no",
        "--tty=false",
        "--interactive=false",
        "--privileged=false",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pid=private",
        "--ipc=private",
        "--uts=private",
        "--cgroupns=private",
        "--userns=keep-id:uid=65532,gid=65532",
        "--user=65532:65532",
        "--systemd=false",
        "--sdnotify=ignore",
        "--memory",
        str(limits["memory_bytes"]),
        "--memory-swap",
        str(limits["memory_bytes"]),
        "--pids-limit",
        str(limits["pids"]),
        "--cpus",
        str(limits["cpus"]),
        "--timeout",
        str(limits["attempt_timeout_sec"]),
        "--tmpfs",
        f"/tmp:rw,nosuid,nodev,noexec,size={limits['tmpfs_bytes']}",
        "--volume",
        str(inputs) + ":" + _MOUNT + ":ro,nosuid,nodev,noexec",
        "--",
        attempt.binding["image_ref"],
        "--request",
        _MOUNT + "/request.json",
    ]


def _image(attempt: _Attempt, manifest: bytes, config: bytes) -> list[str]:
    expected = _mapping(manifest, "manifest")
    values = _mapping(config, "config")
    rootfs = values.get("rootfs")
    if (
        not isinstance(rootfs, Mapping)
        or rootfs.get("type") != "layers"
        or not isinstance(rootfs.get("diff_ids"), list)
        or any(not isinstance(item, str) or not item for item in rootfs["diff_ids"])
    ):
        raise EvaluatorTrustError("Signed OCI config requires ordered rootfs layer identities")
    entrypoint = values.get("config", {}).get("Entrypoint")
    if (
        not isinstance(entrypoint, list)
        or not entrypoint
        or any(not isinstance(item, str) or not item or "\x00" in item for item in entrypoint)
    ):
        raise EvaluatorTrustError("OCI image requires an explicit exec-array ENTRYPOINT")
    raw = attempt.command(
        ["image", "inspect", "--format", "{{json .}}", "--", attempt.binding["image_ref"]],
        attempt.deadline,
    )
    observed = _mapping(raw, "image-inspect")
    observed_rootfs = observed.get("RootFS")
    if (
        not isinstance(observed_rootfs, Mapping)
        or observed_rootfs.get("Type") != rootfs["type"]
        or observed_rootfs.get("Layers") != rootfs["diff_ids"]
        or observed.get("Digest") != "sha256:" + attempt.binding["manifest_sha256"]
        or observed.get("Id", "").removeprefix("sha256:") != hashlib.sha256(config).hexdigest()
        or observed.get("ManifestType") != expected["mediaType"]
        or any(
            observed.get(key, "") != attempt.binding["platform"].get(field, "")
            for key, field in (
                ("Os", "os"),
                ("Architecture", "architecture"),
                ("Variant", "variant"),
            )
        )
    ):
        raise EvaluatorTrustError("Preloaded image differs from the signed platform manifest")
    return entrypoint


def _isolation(document: Mapping[str, Any], attempt: _Attempt) -> None:
    host, config = document["HostConfig"], document["Config"]
    expected = {
        "NetworkMode": "none",
        "ReadonlyRootfs": True,
        "Privileged": False,
        "AutoRemove": False,
        "CgroupManager": "systemd",
        "Memory": attempt.profile.limits["memory_bytes"],
        "MemorySwap": attempt.profile.limits["memory_bytes"],
        "PidsLimit": attempt.profile.limits["pids"],
        "NanoCpus": attempt.profile.limits["cpus"] * 1_000_000_000,
    }
    if (
        any(
            type(host.get(key)) is not type(value) or host[key] != value
            for key, value in expected.items()
        )
        or config.get("Tty") is not False
        or config.get("OpenStdin") is not False
        or config.get("User") != "65532:65532"
        or config.get("Timeout") != attempt.profile.limits["attempt_timeout_sec"]
        or host.get("LogConfig", {}).get("Type") != "none"
        or host.get("RestartPolicy", {}).get("Name") not in ("", "no")
        or "no-new-privileges" not in host.get("SecurityOpt", [])
        or any(
            key not in document or document[key] not in (None, [])
            for key in ("EffectiveCaps", "BoundingCaps")
        )
    ):
        raise EvaluatorTrustError("Created container differs from the required isolation or limits")


def _created(
    document: Mapping[str, Any], attempt: _Attempt, config: bytes, entrypoint: list[str]
) -> None:
    host = document["HostConfig"]
    mounts = document.get("Mounts")
    if (
        document.get("Image", "").removeprefix("sha256:") != hashlib.sha256(config).hexdigest()
        or document.get("Path") != entrypoint[0]
        or document.get("Args") != entrypoint[1:] + ["--request", _MOUNT + "/request.json"]
        or document.get("State", {}).get("Status") != "created"
        or document.get("State", {}).get("Running") is not False
        or not isinstance(mounts, list)
        or len(mounts) != 1
        or any(
            mounts[0].get(key) != value
            for key, value in {
                "Type": "bind",
                "Source": str(attempt.directory / "inputs"),
                "Destination": _MOUNT,
                "RW": False,
            }.items()
        )
        or not {"nosuid", "nodev", "noexec"} <= set(mounts[0].get("Options", []))
        or set(host.get("Tmpfs", {})) != {"/tmp"}
        or not {"nosuid", "nodev", "noexec", f"size={attempt.profile.limits['tmpfs_bytes']}"}
        <= set(host["Tmpfs"]["/tmp"].split(","))
    ):
        raise EvaluatorTrustError("Created container command, image or input mounts differ")
    _isolation(document, attempt)


def _settled(document: Mapping[str, Any]) -> None:
    state = document.get("State", {})
    if (
        state.get("Status") not in {"exited", "stopped"}
        or state.get("Running") is not False
        or state.get("Paused") is not False
        or state.get("OOMKilled") is not False
        or type(state.get("ExitCode")) is not int
        or state["ExitCode"] != 0
        or state.get("Pid") != 0
    ):
        raise EvaluatorTrustError("OCI evaluator has not settled successfully")


def _retain(directory: Path, name: str, payload: bytes) -> None:
    path = directory / name
    with path.open("xb"):
        pass
    path.chmod(0o600)
    write_bytes_atomically(payload, path)
    path.chmod(0o400)


def _execute(attempt: _Attempt, config: bytes, entrypoint: list[str]) -> bytes:
    attempt.record["phase"] = "creating"
    attempt.save()
    created = attempt.command(
        _create_arguments(attempt, attempt.directory / "inputs"), attempt.deadline
    )
    candidate = read_once(attempt.directory / "container.cid", 128).decode().strip()
    if _CID.fullmatch(candidate) is None or created.strip() != candidate.encode():
        raise EvaluatorTrustError("Create acknowledgement does not bind one full container ID")
    attempt.cid = candidate
    attempt.record.update({"phase": "created", "cid": candidate})
    attempt.save()
    _created(attempt.inspect(attempt.deadline), attempt, config, entrypoint)
    attempt.record["phase"] = "running"
    attempt.save()
    response = attempt.command(
        ["start", "--attach", "--", candidate], attempt.deadline, response=True
    )
    _retain(attempt.directory, "response.bin", response)
    attempt.record["response_sha256"] = hashlib.sha256(response).hexdigest()
    attempt.record["response_size"] = len(response)
    attempt.save()
    if (
        attempt.command(["wait", "--condition=exited", "--", candidate], attempt.deadline).strip()
        != b"0"
    ):
        raise EvaluatorTrustError("OCI evaluator wait did not report success")
    _settled(attempt.inspect(attempt.deadline))
    if time.monotonic() >= attempt.deadline:
        raise EvaluatorTrustError("OCI attempt exceeded its deadline")
    cleanup_deadline = time.monotonic() + attempt.profile.limits["cleanup_timeout_sec"]
    attempt.record["phase"] = "settled"
    attempt.save()
    attempt.command(["rm", "--", candidate], cleanup_deadline)
    attempt.command(["container", "exists", "--", candidate], cleanup_deadline, expected_exit=1)
    attempt.record["phase"] = "removed"
    attempt.save()
    if time.monotonic() >= cleanup_deadline:
        raise EvaluatorTrustError("OCI cleanup exceeded its deadline")
    return response


def run_oci_evaluator(
    profile: _OCIProfile,
    namespace: str,
    prepared_request: bytes,
    inputs_dir: Path,
    attempt_dir: Path,
) -> bytes:
    """Return raw stdout only after this local attempt has settled and been removed."""
    if os.name != "posix" or os.getuid() == 0:
        raise EvaluatorTrustError("OCI execution requires the non-root POSIX operator context")
    deadline = time.monotonic() + profile.limits["attempt_timeout_sec"]
    _inputs(profile, prepared_request, inputs_dir, attempt_dir)
    request = _mapping(prepared_request, "evaluator-request")
    if request.get("namespace") != namespace or namespace not in profile.evaluators:
        raise EvaluatorTrustError("Prepared request namespace differs from the operator binding")
    attempt = _Attempt(profile, namespace, attempt_dir, deadline)
    attempt.record["request_sha256"] = hashlib.sha256(prepared_request).hexdigest()
    attempt.save()
    try:
        manifest, config, audit = authenticate_manifest(
            attempt.binding,
            profile=profile.verifier,
            deadline=deadline,
            limits=replace(DEFAULT_TRUST_LIMITS, timeout_sec=profile.limits["command_timeout_sec"]),
        )
        for name, payload in (
            ("manifest.json", manifest),
            ("config.json", config),
            ("signature-audit.bin", audit),
        ):
            _retain(attempt_dir, name, payload)
            attempt.record[name] = {
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
            }
        attempt.config_sha256 = hashlib.sha256(config).hexdigest()
        attempt.record["config_sha256"] = attempt.config_sha256
        attempt.save()
        version = attempt.command(["--version"], deadline)
        if version.strip() != ("podman version " + profile.engine["version"]).encode():
            raise EvaluatorTrustError("Podman version differs from its pinned operator profile")
        _info(
            _mapping(attempt.command(["info", "--format=json"], deadline), "podman-info"), profile
        )
        entrypoint = _image(attempt, manifest, config)
        return _execute(attempt, config, entrypoint)
    except BaseException as failure:
        attempt.record["error"] = f"{type(failure).__name__}: {failure}"[:4096]
        if attempt.record["phase"] in {"creating", "created", "running", "settled"}:
            attempt.recover()
        else:
            attempt.record["phase"] = "unknown"
            attempt.recovering = True
            attempt.observe()
        if isinstance(failure, (KeyboardInterrupt, SystemExit)):
            raise
        raise EvaluatorTrustError(
            f"OCI attempt did not complete; retained journal: {attempt_dir / 'journal.json'}; "
            f"journal error: {attempt.record.get('journal_error', 'none')}"
        ) from failure
