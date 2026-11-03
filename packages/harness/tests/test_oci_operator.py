from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from robotics_acceptance_harness import _oci_operator as operator
from robotics_acceptance_harness.evaluator_json import MAX_PACKET_BYTES
from robotics_acceptance_harness.evaluator_trust import EvaluatorTrustError
from tests.test_oci_manifest_trust import fake_profile, inputs

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX operator input profile")


@pytest.fixture(autouse=True)
def no_process(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("configuration capture invoked a process")

    monkeypatch.setattr(subprocess, "Popen", forbidden)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fixture(root: Path) -> tuple[Path, dict[str, Any], list[dict[str, Any]]]:
    context = root / "context"
    context.mkdir(mode=0o700)
    paths = {name: context / name for name in ("home", "runtime", "graph", "run", "tmp", "hooks")}
    for path in paths.values():
        path.mkdir(mode=0o700)
    for name in ("libpod", "volumes"):
        (paths["graph"] / name).mkdir(mode=0o700)
    bus_path = root / "user-bus"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as bus:
        bus.bind(str(bus_path))
    engine = context / "podman"
    engine.write_bytes(b"unit engine bytes; not executed")
    engine.chmod(0o500)
    containers = context / "containers.conf"
    containers.write_text(
        '[engine]\ncgroup_manager = "systemd"\nlock_type = "file"\n'
        f"tmp_dir = {json.dumps(str(paths['tmp']))}\n"
        f"static_dir = {json.dumps(str(paths['graph'] / 'libpod'))}\n"
        f"volume_path = {json.dumps(str(paths['graph'] / 'volumes'))}\n"
    )
    storage = context / "storage.conf"
    storage.write_text(
        '[storage]\ndriver = "vfs"\n'
        f"graphroot = {json.dumps(str(paths['graph']))}\n"
        f"runroot = {json.dumps(str(paths['run']))}\n"
    )
    manifest, config, bundle, expected = inputs(root)
    verifier = {key: str(value) for key, value in asdict(fake_profile(root)).items()}
    data: dict[str, Any] = {
        "profile_version": 2,
        "verifier": {"kind": "cosign_blob_key_no_tlog", **verifier},
        "engine": {
            "backend": "podman_local",
            "executable": str(engine),
            "executable_sha256": digest(engine.read_bytes()),
            "version": "4.9.3",
            "environment": {
                "HOME": str(paths["home"]),
                "XDG_RUNTIME_DIR": str(paths["runtime"]),
                "PATH": "/usr/bin:/bin",
                "DBUS_SESSION_BUS_ADDRESS": "unix:path=" + str(bus_path),
            },
            "containers_conf": {"path": str(containers), "sha256": digest(containers.read_bytes())},
            "storage_conf": {"path": str(storage), "sha256": digest(storage.read_bytes())},
            "store": {
                "graph_root": str(paths["graph"]),
                "run_root": str(paths["run"]),
                "tmpdir": str(paths["tmp"]),
                "driver": "vfs",
            },
            "hooks_dir": str(paths["hooks"]),
        },
        "limits": {
            "attempt_timeout_sec": 60,
            "command_timeout_sec": 10,
            "cleanup_timeout_sec": 10,
            "stdout_bytes": MAX_PACKET_BYTES,
            "stderr_bytes": 65536,
            "memory_bytes": 268435456,
            "input_bytes": 1073741824,
            "pids": 32,
            "cpus": 1,
            "tmpfs_bytes": 16777216,
        },
        "evaluators": [
            {
                "namespace": "org.example",
                "image_ref": "localhost/evaluator@" + expected,
                "manifest": str(manifest),
                "config": str(config),
                "bundle": str(bundle),
                "manifest_sha256": expected[7:],
                "platform": {"os": "linux", "architecture": "amd64"},
                "invocation": "evaluator_json_v1",
            }
        ],
    }
    requirements = [
        {
            "kind": "oci",
            "namespace": "org.example",
            "execution_subject": {
                "kind": "oci_image",
                "locator": "oci://localhost/evaluator",
                "digest": expected,
            },
            "expected_assertion_ids": ["org.example.check"],
        }
    ]
    return root / "operator.json", data, requirements


def write(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data))
    path.chmod(0o600)


def replace_field(data: dict[str, Any], path: str, value: Any) -> None:
    target: Any = data
    keys = path.split(".")
    for key in keys[:-1]:
        target = target[int(key)] if isinstance(target, list) else target[key]
    target[keys[-1]] = value


def test_profile_captures_configuration_without_processes_and_keeps_it_immutable(
    tmp_path: Path,
) -> None:
    path, data, requirements = fixture(tmp_path)
    write(path, data)
    original = path.read_bytes()
    loaded = operator.load_oci_profile(path, requirements)
    assert loaded.sha256 == digest(original)
    assert loaded.verifier.version == "v3.1.4+dirty"
    assert loaded.engine["version"] == "4.9.3"
    assert set(loaded.evaluators) == {"org.example"}
    engine_bytes = loaded.engine["executable_bytes"]
    storage_bytes = loaded.engine["storage_conf"]["raw"]
    Path(data["engine"]["executable"]).unlink()
    Path(data["engine"]["executable"]).write_bytes(b"changed after capture")
    Path(data["engine"]["storage_conf"]["path"]).write_bytes(b"changed after capture")
    path.write_bytes(b"changed original profile")
    assert loaded.engine["executable_bytes"] == engine_bytes
    assert loaded.engine["storage_conf"]["raw"] == storage_bytes
    assert "data" not in loaded.engine["storage_conf"]
    with pytest.raises(TypeError):
        cast(Any, loaded.limits)["stdout_bytes"] = 0
    with pytest.raises(TypeError):
        cast(Any, loaded.engine["environment"])["PATH"] = "changed"
    with pytest.raises(TypeError):
        cast(Any, loaded.evaluators["org.example"]["platform"])["os"] = "changed"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("profile_version", 1),
        ("extra", "unknown"),
        ("verifier.kind", "github"),
        ("verifier.version", "v3.1.3"),
        ("verifier.version", "v3.1.4rc1"),
        ("engine.backend", "docker"),
        ("engine.version", "6.1.4"),
        ("engine.environment.PATH", ".:/usr/bin"),
        ("engine.environment.CONTAINER_HOST", "ssh://remote"),
        ("limits.stdout_bytes", MAX_PACKET_BYTES + 1),
        ("limits.stderr_bytes", 32 * 1024 * 1024 + 1),
        ("limits.memory_bytes", 0),
        ("limits.pids", True),
        ("limits.command_timeout_sec", 61),
        ("evaluators.0.namespace", "org.other"),
        ("evaluators.0.manifest_sha256", "a" * 64),
        ("evaluators.0.image_ref", "localhost/evaluator:latest"),
        ("evaluators.0.invocation", "shell"),
        ("evaluators.0.platform.extra", "unknown"),
    ],
)
def test_closed_profile_refuses_unsupported_fields(tmp_path: Path, field: str, value: Any) -> None:
    path, data, requirements = fixture(tmp_path)
    replace_field(data, field, value)
    write(path, data)
    with pytest.raises(EvaluatorTrustError):
        operator.load_oci_profile(path, requirements)


@pytest.mark.parametrize("fault", ["missing", "duplicate", "wheel", "receipt"])
def test_requirements_are_complete_and_no_claim_is_silently_dropped(
    tmp_path: Path, fault: str
) -> None:
    path, data, requirements = fixture(tmp_path)
    if fault == "missing":
        data["evaluators"] = []
    elif fault == "duplicate":
        data["evaluators"].append(data["evaluators"][0])
    elif fault == "wheel":
        requirements[0]["kind"] = "wheel"
    else:
        requirements[0]["execution_subject"]["provenance_receipt_sha256"] = "b" * 64
    write(path, data)
    with pytest.raises(EvaluatorTrustError):
        operator.load_oci_profile(path, requirements)


@pytest.mark.parametrize(
    "fault",
    ["missing", "hooks", "symlink", "pin", "storage", "writable", "shared-runtime", "shared-store"],
)
def test_context_is_preexisting_pinned_and_not_a_shared_fallback(
    tmp_path: Path, fault: str
) -> None:
    path, data, requirements = fixture(tmp_path)
    engine = data["engine"]
    if fault == "missing":
        engine["store"]["run_root"] = str(tmp_path / "never-created")
    elif fault == "hooks":
        (Path(engine["hooks_dir"]) / "injected.json").write_text("{}")
    elif fault == "symlink":
        original = Path(engine["store"]["run_root"])
        link = tmp_path / "linked-run"
        link.symlink_to(original, target_is_directory=True)
        engine["store"]["run_root"] = str(link)
    elif fault == "pin":
        engine["storage_conf"]["sha256"] = "a" * 64
    elif fault == "storage":
        target = Path(engine["storage_conf"]["path"])
        target.write_text(target.read_text().replace('driver = "vfs"', 'driver = "overlay"'))
        engine["storage_conf"]["sha256"] = digest(target.read_bytes())
    elif fault == "writable":
        Path(engine["store"]["tmpdir"]).chmod(0o777)
    elif fault == "shared-runtime":
        engine["environment"]["XDG_RUNTIME_DIR"] = engine["environment"]["HOME"]
    else:
        engine["store"]["graph_root"] = engine["environment"]["HOME"]
    write(path, data)
    with pytest.raises(EvaluatorTrustError):
        operator.load_oci_profile(path, requirements)
    assert not (tmp_path / "never-created").exists()


def test_actual_account_default_store_is_refused_even_with_another_selected_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pwd

    path, data, requirements = fixture(tmp_path)
    account_home = tmp_path / "actual-account-home"
    default_store = account_home / ".local/share/containers/storage"
    default_store.mkdir(parents=True, mode=0o700)
    monkeypatch.setattr(pwd, "getpwuid", lambda uid: SimpleNamespace(pw_dir=str(account_home)))
    data["engine"]["store"]["graph_root"] = str(default_store)
    target = Path(data["engine"]["storage_conf"]["path"])
    target.write_text(
        target.read_text().replace(str(tmp_path / "context/graph"), str(default_store))
    )
    data["engine"]["storage_conf"]["sha256"] = digest(target.read_bytes())
    write(path, data)
    with pytest.raises(EvaluatorTrustError, match="default shared HOME store"):
        operator.load_oci_profile(path, requirements)


@pytest.mark.parametrize(
    "repository",
    [
        "--runtime=example.com/repo",
        "shortname",
        "example.com:notaport/repo",
        "oci-archive:/tmp/image",
        "example.com/repo\x00",
    ],
)
def test_image_reference_cannot_select_options_transports_or_unqualified_names(
    tmp_path: Path, repository: str
) -> None:
    path, data, requirements = fixture(tmp_path)
    image_digest = requirements[0]["execution_subject"]["digest"]
    data["evaluators"][0]["image_ref"] = repository + "@" + image_digest
    write(path, data)
    with pytest.raises(EvaluatorTrustError):
        operator.load_oci_profile(path, requirements)


def test_operator_profile_cannot_be_taken_from_the_evidence_root(tmp_path: Path) -> None:
    _, data, requirements = fixture(tmp_path)
    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700)
    path = evidence / "operator.json"
    write(path, data)
    with pytest.raises(EvaluatorTrustError, match="outside evidence"):
        operator.load_oci_profile(path, requirements, evidence_root=evidence)


@pytest.mark.parametrize(
    "fault", ["missing", "network", "fallback", "regular", "symlink", "absent", "owner"]
)
def test_user_bus_requires_a_single_owned_socket_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    path, data, requirements = fixture(tmp_path)
    environment = data["engine"]["environment"]
    address = environment["DBUS_SESSION_BUS_ADDRESS"]
    if fault == "missing":
        del environment["DBUS_SESSION_BUS_ADDRESS"]
    elif fault == "network":
        environment["DBUS_SESSION_BUS_ADDRESS"] = "tcp:host=example.com,port=1234"
    elif fault == "fallback":
        environment["DBUS_SESSION_BUS_ADDRESS"] = address + ";unix:path=/another/bus"
    elif fault == "regular":
        environment["DBUS_SESSION_BUS_ADDRESS"] = (
            "unix:path=" + data["engine"]["storage_conf"]["path"]
        )
    elif fault == "symlink":
        alias = tmp_path / "bus-alias"
        alias.symlink_to(tmp_path / "user-bus")
        environment["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=" + str(alias)
    elif fault == "absent":
        environment["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=" + str(tmp_path / "absent-bus")
    else:
        other_uid = os.getuid() + 1
        monkeypatch.setattr(os, "getuid", lambda: other_uid)
    write(path, data)
    with pytest.raises(EvaluatorTrustError):
        operator.load_oci_profile(path, requirements)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("lock_type", "shm"),
        ("tmp_dir", "/other/tmp"),
        ("static_dir", "/other/static"),
        ("volume_path", "/other/volumes"),
        ("lock_type", None),
    ],
)
def test_engine_lock_and_state_paths_are_bound_before_any_invocation(
    tmp_path: Path, field: str, value: str | None
) -> None:
    path, data, requirements = fixture(tmp_path)
    record = data["engine"]["containers_conf"]
    target = Path(record["path"])
    lines = [line for line in target.read_text().splitlines() if not line.startswith(field + " =")]
    if value is not None:
        lines.append(field + " = " + json.dumps(value))
    target.write_text("\n".join(lines) + "\n")
    record["sha256"] = digest(target.read_bytes())
    write(path, data)
    with pytest.raises(EvaluatorTrustError, match="selected project context"):
        operator.load_oci_profile(path, requirements)


@pytest.mark.parametrize("directory", ["libpod", "volumes"])
def test_state_directories_must_be_preprovisioned(tmp_path: Path, directory: str) -> None:
    path, data, requirements = fixture(tmp_path)
    target = Path(data["engine"]["store"]["graph_root"]) / directory
    target.rmdir()
    write(path, data)
    with pytest.raises(EvaluatorTrustError):
        operator.load_oci_profile(path, requirements)
    assert not target.exists()


@pytest.mark.parametrize(
    "field",
    [
        "attempt_timeout_sec",
        "command_timeout_sec",
        "cleanup_timeout_sec",
    ],
)
def test_backend_timeouts_refuse_values_beyond_one_day(tmp_path: Path, field: str) -> None:
    path, data, requirements = fixture(tmp_path)
    data["limits"][field] = 86_401
    write(path, data)
    with pytest.raises(EvaluatorTrustError, match="exceeds one day"):
        operator.load_oci_profile(path, requirements)


@pytest.mark.parametrize("value", [0, -1, True, 2**63, "1024"])
def test_input_disk_budget_requires_a_positive_int64(tmp_path: Path, value: Any) -> None:
    path, data, requirements = fixture(tmp_path)
    data["limits"]["input_bytes"] = value
    write(path, data)
    with pytest.raises(EvaluatorTrustError, match="positive bounded integers"):
        operator.load_oci_profile(path, requirements)


def test_input_disk_budget_is_explicit_and_independent_of_child_memory(tmp_path: Path) -> None:
    path, data, requirements = fixture(tmp_path)
    data["limits"]["input_bytes"] = 2**63 - 1
    write(path, data)
    loaded = operator.load_oci_profile(path, requirements)
    assert loaded.limits["input_bytes"] == 2**63 - 1
    assert loaded.limits["memory_bytes"] == 268435456
    del data["limits"]["input_bytes"]
    write(path, data)
    with pytest.raises(EvaluatorTrustError):
        operator.load_oci_profile(path, requirements)
