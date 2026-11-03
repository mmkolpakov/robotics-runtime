from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, cast

import pytest

from robotics_acceptance_harness import _oci_executor as executor
from robotics_acceptance_harness import _oci_operator as operator
from robotics_acceptance_harness.evaluator_trust import EvaluatorTrustError
from tests.test_oci_operator import fixture, write

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX local process profile")

_FAKE = r"""
import json, os, signal, sys, time
from pathlib import Path
signal.alarm(8)
home = Path(os.environ['HOME'])
settings = json.loads((home / 'settings.json').read_text())
args = sys.argv[1:]
assert args[:3] == ['--remote=false', '--hooks-dir', settings['hooks']]
args = args[3:]
with (home / 'calls.jsonl').open('a') as stream:
    stream.write(json.dumps({'args': args, 'environment': dict(os.environ)}) + '\n')
fault = settings['fault']
cid = 'a' * 64
state_path = home / 'state'
state = state_path.read_text() if state_path.exists() else settings.get('initial_state', 'created')
if args == ['--version']:
    print('podman version 4.9.3')
elif args[0] == 'info':
    print(json.dumps(settings['info']))
elif args[:2] == ['image', 'inspect']:
    print(json.dumps(settings['image']))
elif args[0] == 'create':
    assert args[args.index('--') + 1:] == [
        settings['image_ref'], '--request', '/run/robotics-evaluator/request.json']
    label = args[args.index('--label') + 1].split('=', 1)[1]
    settings['container']['Config']['Labels'] = {'org.robotics-runtime.evaluator-attempt': label}
    (home / 'settings.json').write_text(json.dumps(settings))
    Path(args[args.index('--cidfile') + 1]).write_text(cid)
    if fault == 'create-ack-loss':
        time.sleep(6)
    print(cid)
elif args[:2] == ['container', 'exists']:
    sys.exit(0 if fault == 'rm-no-absence' else 1)
elif args[:2] == ['container', 'inspect']:
    document = settings['container']
    document['State'] = {
        'Status': state, 'Running': state == 'running', 'Paused': False,
        'OOMKilled': False, 'Pid': 0, 'ExitCode': 0}
    if fault == 'foreign-cid':
        document['Id'] = 'b' * 64
    if fault == 'wrong-container-config':
        document['Image'] = 'f' * 64
    if fault == 'failed-exit' and state == 'exited':
        document['State']['ExitCode'] = 7
    print(json.dumps(document))
elif args[0] == 'start':
    state_path.write_text('running')
    if fault == 'overflow':
        os.write(1, b'x' * 257); time.sleep(6)
    if fault == 'stderr-overflow':
        os.write(2, b'x' * 65537); time.sleep(6)
    if fault == 'silent':
        time.sleep(6)
    if fault == 'fd-holder':
        pid = os.fork()
        if pid == 0:
            signal.alarm(4)
            time.sleep(2)
            (home / 'holder-finished').write_text('done')
        os._exit(0)
    os.write(2, b'unit diagnostic')
    os.write(1, bytes.fromhex(settings['response']))
    state_path.write_text('exited')
elif args[0] == 'wait':
    print(0)
elif args[0] == 'stop':
    state_path.write_text('exited')
elif args[0] == 'rm':
    if fault == 'near-deadline':
        time.sleep(0.3)
    state_path.write_text('removed'); print(cid)
else:
    raise AssertionError(args)
"""


def _prepare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str = "") -> tuple[Any, ...]:
    import sys

    if os.getuid() == 0:
        pytest.skip("real fake-CLI lifecycle uses the non-root owner profile")
    path, data, requirements = fixture(tmp_path)
    binding = data["evaluators"][0]
    layers = ["sha256:" + "1" * 64, "sha256:" + "2" * 64]
    config = {
        "os": "linux",
        "architecture": "amd64",
        "config": {"Entrypoint": ["/evaluator"]},
        "rootfs": {"type": "layers", "diff_ids": layers},
    }
    config_raw = json.dumps(config).encode()
    Path(binding["config"]).write_bytes(config_raw)
    manifest = json.loads(Path(binding["manifest"]).read_bytes())
    manifest["layers"] = [
        {"mediaType": "application/vnd.oci.image.layer.v1.tar", "digest": layer, "size": 1024}
        for layer in layers
    ]
    config_sha = hashlib.sha256(config_raw).hexdigest()
    manifest["config"].update(digest="sha256:" + config_sha, size=len(config_raw))
    manifest_raw = json.dumps(manifest).encode()
    Path(binding["manifest"]).write_bytes(manifest_raw)
    manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
    binding["manifest_sha256"] = manifest_sha
    binding["image_ref"] = "localhost/unit@sha256:" + manifest_sha
    requirements[0]["execution_subject"]["digest"] = "sha256:" + manifest_sha
    engine = Path(data["engine"]["executable"])
    engine.unlink()
    engine.write_text(f"#!{sys.executable}\n" + _FAKE)
    engine.chmod(0o500)
    data["engine"]["executable_sha256"] = hashlib.sha256(engine.read_bytes()).hexdigest()
    data["limits"].update(
        command_timeout_sec=1, attempt_timeout_sec=8, cleanup_timeout_sec=3, stdout_bytes=256
    )
    write(path, data)
    profile = operator.load_oci_profile(path, requirements)
    monkeypatch.setattr(
        executor,
        "authenticate_manifest",
        lambda *a, **k: (manifest_raw, config_raw, b"fixture audit"),
    )
    attempt = tmp_path / "attempt"
    attempt.mkdir(mode=0o700)
    inputs = attempt / "inputs"
    inputs.mkdir(mode=0o700)
    (inputs / "objects").mkdir(mode=0o700)
    packet = b'{"namespace":"org.example"}'
    (inputs / "request.json").write_bytes(packet)
    (inputs / "request.json").chmod(0o400)
    home = Path(data["engine"]["environment"]["HOME"])
    settings = {
        "hooks": data["engine"]["hooks_dir"],
        "fault": fault,
        "image_ref": binding["image_ref"],
        "response": b' \n{"value":9007199254740993}\n'.hex(),
        "info": {
            "host": {
                "serviceIsRemote": False,
                "security": {"rootless": True},
                "cgroupManager": "systemd",
                "cgroupVersion": "v2",
                "cgroupControllers": ["cpu", "memory", "pids"],
            },
            "store": {
                "graphRoot": data["engine"]["store"]["graph_root"],
                "runRoot": data["engine"]["store"]["run_root"],
                "graphDriverName": "vfs",
                "volumePath": str(Path(data["engine"]["store"]["graph_root"]) / "volumes"),
            },
        },
        "image": {
            "Digest": "sha256:" + manifest_sha,
            "Id": config_sha,
            "ManifestType": manifest["mediaType"],
            "RootFS": {"Type": "layers", "Layers": layers},
            "Os": "linux",
            "Architecture": "amd64",
        },
    }

    settings["container"] = {
        "Id": "a" * 64,
        "Image": config_sha,
        "ImageName": binding["image_ref"],
        "ImageDigest": "sha256:" + manifest_sha,
        "Path": "/evaluator",
        "Args": ["--request", "/run/robotics-evaluator/request.json"],
        "Config": {
            "Labels": {},
            "Tty": False,
            "OpenStdin": False,
            "User": "65532:65532",
            "Timeout": 8,
        },
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "Privileged": False,
            "AutoRemove": False,
            "CgroupManager": "systemd",
            "Memory": 268435456,
            "MemorySwap": 268435456,
            "PidsLimit": 32,
            "NanoCpus": 1000000000,
            "LogConfig": {"Type": "none"},
            "RestartPolicy": {"Name": "no"},
            "SecurityOpt": ["no-new-privileges"],
            "Tmpfs": {"/tmp": "rw,nosuid,nodev,noexec,size=16777216"},
        },
        "EffectiveCaps": None,
        "BoundingCaps": None,
        "Mounts": [
            {
                "Type": "bind",
                "Source": str(inputs),
                "Destination": "/run/robotics-evaluator",
                "RW": False,
                "Options": ["nosuid", "nodev", "noexec"],
            }
        ],
    }
    (home / "settings.json").write_text(json.dumps(settings))
    return profile, packet, inputs, attempt, home


def _calls(home: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (home / "calls.jsonl").read_text().splitlines()]


def test_root_refuses_before_any_tool_or_input_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(os, "getuid", lambda: 0)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("root refusal reached a tool")

    monkeypatch.setattr(executor, "_capture_tool", forbidden)
    monkeypatch.setattr(executor, "authenticate_manifest", forbidden)
    with pytest.raises(EvaluatorTrustError, match="non-root"):
        executor.run_oci_evaluator(cast(Any, None), "unit", b"", tmp_path, tmp_path)


@pytest.mark.parametrize("payload", [b' \n{"value":9007199254740993}\n', b"\x00\xff\n"])
def test_normal_attempt_preserves_raw_output_and_removes_only_its_cid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: bytes
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch)
    settings = home / "settings.json"
    values = json.loads(settings.read_bytes())
    values["response"] = payload.hex()
    settings.write_text(json.dumps(values))
    monkeypatch.setenv("CONTAINER_HOST", "must-not-inherit")
    result = executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    assert result == payload
    assert (attempt / "response.bin").read_bytes() == result
    record = json.loads((attempt / "journal.json").read_bytes())
    for name in ("manifest.json", "config.json", "signature-audit.bin"):
        raw = (attempt / name).read_bytes()
        assert record[name] == {"sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}
        assert (attempt / name).stat().st_mode & 0o777 == 0o400
    assert (attempt / "manifest.json").read_bytes() == profile.evaluators["org.example"][
        "manifest"
    ].read_bytes()
    assert (attempt / "signature-audit.bin").read_bytes() == b"fixture audit"
    calls = _calls(home)
    assert [call["args"][0] for call in calls] == [
        "--version",
        "info",
        "image",
        "create",
        "container",
        "start",
        "wait",
        "container",
        "rm",
        "container",
    ]
    assert all("CONTAINER_HOST" not in call["environment"] for call in calls)
    assert calls[-2]["args"] == ["rm", "--", "a" * 64]
    assert calls[-1]["args"] == ["container", "exists", "--", "a" * 64]
    assert (inputs / "request.json").read_bytes() == packet
    assert json.loads((attempt / "journal.json").read_bytes())["phase"] == "removed"


@pytest.mark.parametrize(
    "fault",
    ["create-ack-loss", "overflow", "stderr-overflow", "silent", "foreign-cid", "failed-exit"],
)
def test_uncertain_attempt_retains_inputs_and_never_replays_or_removes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch, fault)
    with pytest.raises(EvaluatorTrustError, match="retained journal"):
        executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    operations = [call["args"][0] for call in _calls(home)]
    assert operations.count("create") == 1
    assert operations.count("start") <= 1
    assert "rm" not in operations
    if fault in {"create-ack-loss", "foreign-cid"}:
        assert "start" not in operations
    if fault == "foreign-cid":
        assert "stop" not in operations
    assert (inputs / "request.json").read_bytes() == packet
    assert json.loads((attempt / "journal.json").read_bytes())["phase"] == "unknown"


@pytest.mark.parametrize(
    "fault", ["manifest", "config", "remote", "cgroups", "writable-mount", "memory"]
)
def test_live_fact_mismatch_refuses_before_untrusted_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch)
    path = home / "settings.json"
    values = json.loads(path.read_bytes())
    if fault == "manifest":
        values["image"]["Digest"] = "sha256:" + "f" * 64
    elif fault == "config":
        values["image"]["Id"] = "f" * 64
    elif fault == "remote":
        values["info"]["host"]["serviceIsRemote"] = True
    elif fault == "cgroups":
        values["info"]["host"]["cgroupControllers"] = ["cpu", "pids"]
    elif fault == "writable-mount":
        values["container"]["Mounts"][0]["RW"] = True
    else:
        values["container"]["HostConfig"]["Memory"] = 0
    path.write_text(json.dumps(values))
    with pytest.raises(EvaluatorTrustError, match="retained journal"):
        executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    assert "start" not in [call["args"][0] for call in _calls(home)]


@pytest.mark.parametrize("fault", ["changed-request", "writable-file", "symlink", "extra"])
def test_only_private_prepared_inputs_are_mounted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch)
    target = inputs / "request.json"
    if fault == "changed-request":
        target.chmod(0o600)
        target.write_bytes(b"changed")
        target.chmod(0o400)
    elif fault == "writable-file":
        target.chmod(0o600)
    elif fault == "symlink":
        target.unlink()
        target.symlink_to(home / "settings.json")
    else:
        (inputs / "operator-key").write_bytes(b"must not be exposed")
    with pytest.raises(EvaluatorTrustError):
        executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    assert not (home / "calls.jsonl").exists()


def test_inherited_writer_is_unknown_and_retains_inputs_without_waiting_for_eof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch, "fd-holder")
    try:
        with pytest.raises(EvaluatorTrustError, match="retained journal"):
            executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
        assert json.loads((attempt / "journal.json").read_bytes())["phase"] == "unknown"
        assert "rm" not in [call["args"][0] for call in _calls(home)]
        assert (inputs / "request.json").read_bytes() == packet
    finally:
        deadline = time.monotonic() + 4
        while not (home / "holder-finished").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert (home / "holder-finished").exists(), "finite CLI fixture did not finish"


def test_total_input_budget_refuses_before_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch)
    profile = replace(profile, limits={**profile.limits, "input_bytes": len(packet) - 1})
    with pytest.raises(EvaluatorTrustError, match="unique disk budget"):
        executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    assert not (home / "calls.jsonl").exists()


def test_wrong_config_cannot_be_stopped_or_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile, packet, inputs, attempt, home = _prepare(
        tmp_path, monkeypatch, "wrong-container-config"
    )
    with pytest.raises(EvaluatorTrustError, match="retained journal"):
        executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    operations = [call["args"][0] for call in _calls(home)]
    assert not {"start", "stop", "rm"} & set(operations)


def test_rm_acknowledgement_without_absence_cannot_return_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch, "rm-no-absence")
    with pytest.raises(EvaluatorTrustError, match="retained journal"):
        executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    assert any(call["args"][:2] == ["container", "exists"] for call in _calls(home))
    assert (attempt / "response.bin").exists()
    assert json.loads((attempt / "journal.json").read_bytes())["phase"] == "unknown"


def test_settled_response_has_a_separate_cleanup_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile, packet, inputs, attempt, _ = _prepare(tmp_path, monkeypatch, "near-deadline")
    original = executor._Attempt.inspect
    deadlines: list[float] = []

    def inspect(owner: Any, deadline: float) -> dict[str, Any]:
        result = original(owner, deadline)
        if result["State"]["Status"] == "exited" and not owner.recovering:
            owner.deadline = time.monotonic() + 0.15
            deadlines.append(owner.deadline)
        return result

    monkeypatch.setattr(executor._Attempt, "inspect", inspect)
    response = executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    assert deadlines and time.monotonic() > deadlines[0]
    assert (attempt / "response.bin").read_bytes() == response
    assert json.loads((attempt / "journal.json").read_bytes())["phase"] == "removed"


def test_journal_failure_cannot_prevent_owned_stop_after_overflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch, "overflow")
    original = executor._Attempt.save
    failed = False

    def save(owner: Any) -> None:
        nonlocal failed
        failed = failed or any(
            row["operation"][0] == "start" and row["state"] == "unknown"
            for row in owner.record["commands"]
        )
        if failed:
            raise OSError("unit journal unavailable")
        original(owner)

    monkeypatch.setattr(executor._Attempt, "save", save)
    with pytest.raises(EvaluatorTrustError, match="journal unavailable"):
        executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    operations = [call["args"][0] for call in _calls(home)]
    assert "stop" in operations and "rm" not in operations
    assert (inputs / "request.json").read_bytes() == packet


@pytest.mark.parametrize(
    "name", ["manifest.json", "config.json", "signature-audit.bin", "response.bin"]
)
def test_captured_bytes_are_retained_before_the_next_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch)
    from robotics_runtime_contracts.writers import write_bytes_atomically

    original = write_bytes_atomically

    def write_response(content: bytes, output: Any) -> Path:
        if Path(output).name == name:
            raise OSError("unit required payload storage unavailable")
        return original(content, output)

    monkeypatch.setattr(executor, "write_bytes_atomically", write_response)
    with pytest.raises(EvaluatorTrustError, match="retained journal"):
        executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    if name == "response.bin":
        operations = [call["args"][0] for call in _calls(home)]
        assert "stop" in operations and "rm" not in operations
    else:
        assert not (home / "calls.jsonl").exists()


@pytest.mark.parametrize("state", ["configured", "initialized"])
def test_create_state_uses_the_exact_public_podman_spelling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch)
    path = home / "settings.json"
    settings = json.loads(path.read_bytes())
    settings["initial_state"] = state
    path.write_text(json.dumps(settings))
    with pytest.raises(EvaluatorTrustError, match="retained journal"):
        executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    assert "start" not in [call["args"][0] for call in _calls(home)]


@pytest.mark.parametrize("value", [None, []])
def test_explicit_zero_capability_representations_are_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: Any
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch)
    path = home / "settings.json"
    settings = json.loads(path.read_bytes())
    for key in ("EffectiveCaps", "BoundingCaps"):
        settings["container"][key] = value
    path.write_text(json.dumps(settings))
    assert executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)


@pytest.mark.parametrize("key", ["EffectiveCaps", "BoundingCaps"])
@pytest.mark.parametrize("value", ["missing", ["CAP_SYS_ADMIN"], {}, False])
def test_missing_nonempty_or_wrong_type_capabilities_refuse_before_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str, value: Any
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch)
    path = home / "settings.json"
    settings = json.loads(path.read_bytes())
    if value == "missing":
        del settings["container"][key]
    else:
        settings["container"][key] = value
    path.write_text(json.dumps(settings))
    with pytest.raises(EvaluatorTrustError, match="retained journal"):
        executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    assert "start" not in [call["args"][0] for call in _calls(home)]


def test_creation_time_transport_digest_is_not_runtime_content_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch)
    path = home / "settings.json"
    settings = json.loads(path.read_bytes())
    other = "sha256:" + "f" * 64
    settings["container"]["ImageDigest"] = other
    settings["image"]["RepoDigests"] = []
    path.write_text(json.dumps(settings))
    assert executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    journal = json.loads((attempt / "journal.json").read_bytes())
    assert journal["container_transport_digest"] == other
    assert (
        journal["manifest.json"]["sha256"] == profile.evaluators["org.example"]["manifest_sha256"]
    )


@pytest.mark.parametrize("fault", ["missing", "null", "type", "layer", "order", "layers-type"])
def test_image_rootfs_must_match_the_signed_config_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch)
    path = home / "settings.json"
    settings = json.loads(path.read_bytes())
    image = settings["image"]
    if fault == "missing":
        del image["RootFS"]
    elif fault == "null":
        image["RootFS"] = None
    elif fault == "type":
        image["RootFS"]["Type"] = "unknown"
    elif fault == "layer":
        image["RootFS"]["Layers"][0] = "sha256:" + "3" * 64
    elif fault == "order":
        image["RootFS"]["Layers"].reverse()
    else:
        image["RootFS"]["Layers"] = "not-an-array"
    path.write_text(json.dumps(settings))
    with pytest.raises(EvaluatorTrustError, match="retained journal"):
        executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    assert "create" not in [call["args"][0] for call in _calls(home)]


def test_container_must_keep_the_selected_immutable_image_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch)
    path = home / "settings.json"
    settings = json.loads(path.read_bytes())
    settings["container"]["ImageName"] = "localhost/other@" + settings["image"]["Digest"]
    path.write_text(json.dumps(settings))
    with pytest.raises(EvaluatorTrustError, match="retained journal"):
        executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    assert not {"start", "stop", "rm"} & {call["args"][0] for call in _calls(home)}


def test_signature_refusal_cannot_be_replaced_by_matching_engine_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile, packet, inputs, attempt, home = _prepare(tmp_path, monkeypatch)

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise EvaluatorTrustError("unit signature refused")

    monkeypatch.setattr(executor, "authenticate_manifest", refuse)
    with pytest.raises(EvaluatorTrustError, match="retained journal"):
        executor.run_oci_evaluator(profile, "org.example", packet, inputs, attempt)
    assert not (home / "calls.jsonl").exists()
