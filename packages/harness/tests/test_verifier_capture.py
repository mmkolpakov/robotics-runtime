from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

import pytest

from robotics_acceptance_harness import evaluator_trust as trust

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX verifier input profile")


def verifier(tmp_path: Path, body: str, name: str = "gh") -> list[str]:
    executable = tmp_path / name
    executable.write_text(
        f"#!{sys.executable}\nimport os, signal, sys, time\nsignal.alarm(8)\n{body}\n"
    )
    executable.chmod(0o500)
    return (
        [str(executable), "--version"]
        if name == "gh"
        else [str(executable), "verify-blob-attestation"]
    )


@pytest.fixture
def children(monkeypatch: pytest.MonkeyPatch) -> list[subprocess.Popen[bytes]]:
    observed: list[subprocess.Popen[bytes]] = []
    original = subprocess.Popen

    def start(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        process = original(*args, **kwargs)
        observed.append(process)
        return process

    monkeypatch.setattr(subprocess, "Popen", start)
    return observed


@pytest.mark.parametrize("descriptor", [1, 2])
def test_excess_byte_refuses_before_silent_child_deadline(
    tmp_path: Path, children: list[subprocess.Popen[bytes]], descriptor: int
) -> None:
    command = verifier(tmp_path, f"os.write({descriptor}, b'x' * 257)\ntime.sleep(6)")
    started = time.monotonic()
    with pytest.raises(trust.EvaluatorTrustError, match="byte limit"):
        trust._run_tool(command, tmp_path, trust.TrustLimits(max_report_bytes=256, timeout_sec=4))
    assert time.monotonic() - started < 3
    assert children[0].returncode is not None
    assert not (tmp_path / "verifier-output").exists()


def test_binary_exact_cap_concurrent_streams_and_stdout_only(tmp_path: Path) -> None:
    command = verifier(
        tmp_path,
        "import threading\n"
        "payload = bytes(range(256)) * 512\n"
        "worker = threading.Thread(target=lambda: os.write(2, payload))\n"
        "worker.start()\nos.write(1, payload)\nworker.join()",
    )
    result = trust._run_tool(
        command, tmp_path, trust.TrustLimits(max_report_bytes=131072, timeout_sec=4)
    )
    assert result == bytes(range(256)) * 512


def test_cosign_keeps_stream_order_not_arrival_order(tmp_path: Path) -> None:
    command = verifier(tmp_path, "os.write(2, b'err')\nos.write(1, b'out')", "cosign")
    assert (
        trust._run_tool(
            command, tmp_path, trust.TrustLimits(max_report_bytes=6), tool_name="cosign"
        )
        == b"outerr"
    )


def test_nonzero_preserves_diagnostic_and_never_returns_report(tmp_path: Path) -> None:
    command = verifier(
        tmp_path, "os.write(1, b'partial')\nos.write(2, b'refused\\xff')\nsys.exit(3)"
    )
    with pytest.raises(trust.EvaluatorTrustError, match="GitHub attestation verification refused"):
        trust._run_tool(command, tmp_path, trust.TrustLimits())


def test_eof_does_not_bypass_process_deadline_and_kill_reaps_ignoring_term(
    tmp_path: Path, children: list[subprocess.Popen[bytes]]
) -> None:
    command = verifier(
        tmp_path,
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\nos.close(1)\nos.close(2)\ntime.sleep(6)",
    )
    started = time.monotonic()
    with pytest.raises(trust.EvaluatorTrustError, match="exceeded its deadline"):
        trust._run_tool(command, tmp_path, trust.TrustLimits(timeout_sec=1))
    assert time.monotonic() - started < 4
    assert children[0].returncode == -signal.SIGKILL


def test_exited_child_with_inherited_writer_does_not_hold_parent(
    tmp_path: Path, children: list[subprocess.Popen[bytes]]
) -> None:
    done = tmp_path / "holder-finished"
    command = verifier(
        tmp_path,
        "pid = os.fork()\n"
        "if pid == 0:\n"
        "    time.sleep(2)\n"
        f"    open({str(done)!r}, 'w').close()\n"
        "    os._exit(0)\n"
        "os._exit(0)",
    )
    started = time.monotonic()
    try:
        with pytest.raises(trust.EvaluatorTrustError, match="exceeded its deadline"):
            trust._run_tool(command, tmp_path, trust.TrustLimits(timeout_sec=1))
        assert time.monotonic() - started < 1.8
        assert children[0].returncode == 0
        assert not done.exists()
    finally:
        deadline = time.monotonic() + 4
        while not done.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert done.exists(), "finite inherited-FD fixture did not settle"


@pytest.mark.parametrize("failure", [KeyboardInterrupt, OSError])
def test_capture_failure_closes_streams_and_reaps_direct_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    children: list[subprocess.Popen[bytes]],
    failure: type[BaseException],
) -> None:
    command = verifier(tmp_path, "os.write(1, b'x')\ntime.sleep(6)")
    original = os.read

    def read(descriptor: int, count: int) -> bytes:
        if children:
            raise failure()
        return original(descriptor, count)

    monkeypatch.setattr(os, "read", read)
    with pytest.raises(failure):
        trust._run_tool(command, tmp_path, trust.TrustLimits(timeout_sec=4))
    assert children[0].returncode is not None
    assert children[0].stdout is not None and children[0].stdout.closed
    assert children[0].stderr is not None and children[0].stderr.closed


def test_combined_overflow_refuses_while_child_is_still_running(tmp_path: Path) -> None:
    command = verifier(
        tmp_path, "os.write(2, b'err')\nos.write(1, b'out')\ntime.sleep(6)", "cosign"
    )
    started = time.monotonic()
    with pytest.raises(trust.EvaluatorTrustError, match="combined verifier audit"):
        trust._run_tool(
            command,
            tmp_path,
            trust.TrustLimits(max_report_bytes=5, timeout_sec=4),
            tool_name="cosign",
        )
    assert time.monotonic() - started < 3


@pytest.mark.parametrize("payload", [b"", b'\r\n{"n":9007199254740993}\n', b"\xff\xc3\xa9"])
def test_exact_bytes_and_empty_output(tmp_path: Path, payload: bytes) -> None:
    command = verifier(tmp_path, f"os.write(1, {payload!r})")
    assert (
        trust._run_tool(command, tmp_path, trust.TrustLimits(max_report_bytes=max(1, len(payload))))
        == payload
    )


def test_cosign_version_has_independent_caps(tmp_path: Path) -> None:
    command = verifier(tmp_path, "os.write(1, b'out')\nos.write(2, b'err')", "cosign")
    command[1:] = ["version", "--json"]
    assert (
        trust._run_tool(
            command, tmp_path, trust.TrustLimits(max_report_bytes=3), tool_name="cosign"
        )
        == b"out"
    )


def test_failed_launch_never_produces_an_admission(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        trust._run_tool([str(tmp_path / "gh"), "--version"], tmp_path, trust.TrustLimits())


def test_cleanup_without_reap_is_explicit_failure() -> None:
    from unittest.mock import Mock

    process = Mock(pid=123, args=["owned-fixture"])
    process.poll.return_value = None
    process.wait.side_effect = subprocess.TimeoutExpired(process.args, 1)
    with pytest.raises(trust.EvaluatorTrustError, match="cleanup did not settle"):
        trust._stop_tool(process)
    process.terminate.assert_called_once_with()
    process.kill.assert_called_once_with()
    assert process.wait.call_count == 2


def test_allowed_argv_is_literal_and_environment_is_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    monkeypatch.setenv("GH_TOKEN", "must-not-inherit")
    command = verifier(
        tmp_path,
        "import json\nprint(json.dumps({'argv': sys.argv[1:], 'env': dict(os.environ)}))",
    )
    command[1:] = ["attestation", "verify", "$(not-a-shell); *"]
    observed = json.loads(trust._run_tool(command, tmp_path, trust.TrustLimits()))
    assert observed["argv"] == command[1:]
    assert "GH_TOKEN" not in observed["env"]
    assert "PATH" not in observed["env"]
    assert observed["env"]["HOME"] == str(tmp_path / "home")


def test_private_capture_uses_only_explicit_selected_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    monkeypatch.setenv("UNSELECTED_ENGINE_SETTING", "must-not-inherit")
    command = verifier(tmp_path, "import json\nprint(json.dumps(dict(os.environ)))")
    code, output, error = trust._capture_tool(
        command,
        tmp_path,
        environment={"PATH": "/operator/helpers", "ENGINE_SELECTION": "project-store"},
        deadline=time.monotonic() + 4,
        byte_limits=(4096, 32, None),
    )
    observed = json.loads(output)
    assert code == 0 and error == b""
    assert observed["PATH"] == "/operator/helpers"
    assert observed["ENGINE_SELECTION"] == "project-store"
    assert "UNSELECTED_ENGINE_SETTING" not in observed


@pytest.mark.parametrize(
    ("stdout", "stderr"), [(b"abc", b"12345"), (b"abcd", b""), (b"", b"123456")]
)
def test_private_capture_has_independent_stream_caps(
    tmp_path: Path, stdout: bytes, stderr: bytes
) -> None:
    command = verifier(tmp_path, f"os.write(1, {stdout!r})\nos.write(2, {stderr!r})")
    arguments: dict[str, Any] = {
        "environment": {},
        "deadline": time.monotonic() + 4,
        "byte_limits": (3, 5, None),
    }
    if len(stdout) <= 3 and len(stderr) <= 5:
        assert trust._capture_tool(command, tmp_path, **arguments) == (0, stdout, stderr)
    else:
        with pytest.raises(trust.EvaluatorTrustError, match="byte limit"):
            trust._capture_tool(command, tmp_path, **arguments)


def test_expired_deadline_and_absent_environment_refuse_before_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        pytest.fail("refused capture spawned a child")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    with pytest.raises(subprocess.TimeoutExpired):
        trust._capture_tool(
            ["never-run"],
            tmp_path,
            environment={},
            deadline=time.monotonic() - 1,
            byte_limits=(1, 1, None),
        )
    with pytest.raises(trust.EvaluatorTrustError, match="explicit environment"):
        trust._capture_tool(
            ["never-run"],
            tmp_path,
            environment=cast(Any, None),
            deadline=time.monotonic() + 1,
            byte_limits=(1, 1, None),
        )


def test_two_commands_share_one_absolute_deadline(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    first_command = verifier(first, "time.sleep(1)\nos.write(1, b'first')")
    second_command = verifier(second, "time.sleep(2.5)\nos.write(1, b'late')")
    deadline = time.monotonic() + 3
    assert trust._capture_tool(
        first_command, first, environment={}, deadline=deadline, byte_limits=(32, 32, None)
    ) == (0, b"first", b"")
    with pytest.raises(subprocess.TimeoutExpired):
        trust._capture_tool(
            second_command, second, environment={}, deadline=deadline, byte_limits=(32, 32, None)
        )


def test_process_settlement_after_deadline_cannot_return_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    command = verifier(tmp_path, "os.write(1, b'otherwise-valid')")
    deadline = time.monotonic() + 4
    original = subprocess.Popen

    def start(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        process = original(*args, **kwargs)
        original_wait = process.wait

        def wait(timeout: float | None = None) -> int:
            result = original_wait(timeout=timeout)
            monkeypatch.setattr(time, "monotonic", lambda: deadline + 1)
            return result

        monkeypatch.setattr(process, "wait", wait)
        return process

    monkeypatch.setattr(subprocess, "Popen", start)
    with pytest.raises(subprocess.TimeoutExpired):
        trust._capture_tool(
            command, tmp_path, environment={}, deadline=deadline, byte_limits=(32, 32, None)
        )


def test_verifier_expired_parent_deadline_refuses_before_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("expired verifier deadline spawned a process")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    with pytest.raises(trust.EvaluatorTrustError, match="exceeded its deadline"):
        trust._run_tool(
            [str(tmp_path / "gh"), "--version"],
            tmp_path,
            trust.TrustLimits(),
            deadline=time.monotonic() - 1,
        )


def test_verifier_command_timeout_still_limits_a_later_parent_deadline(tmp_path: Path) -> None:
    command = verifier(tmp_path, "time.sleep(6)")
    started = time.monotonic()
    with pytest.raises(trust.EvaluatorTrustError, match="exceeded its deadline"):
        trust._run_tool(command, tmp_path, trust.TrustLimits(timeout_sec=1), deadline=started + 5)
    assert time.monotonic() - started < 3
