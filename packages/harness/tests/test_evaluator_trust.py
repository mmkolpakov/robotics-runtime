from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
from dataclasses import replace
from importlib.metadata import Distribution
from pathlib import Path
from typing import Any, cast
from zipfile import ZipFile

import pytest

from robotics_acceptance_harness import evaluator_trust as trust
from robotics_acceptance_harness.evaluator_trust import (
    EvaluatorTrustError,
    GitHubVerifierProfile,
    GitHubWheelPolicy,
    TrustLimits,
    authenticate_wheel,
    verify_installed_wheel,
)

DIST_INFO = "example_evaluator-1.0.dist-info"
SOURCE = b"def evaluate(context):\n    return []\n"


def record_row(name: str, payload: bytes) -> tuple[str, str, str]:
    digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode()
    return name, f"sha256={digest}", str(len(payload))


def record_bytes(files: dict[str, bytes], record_name: str) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerows(record_row(name, payload) for name, payload in files.items())
    writer.writerow((record_name, "", ""))
    return stream.getvalue().encode()


def fixture_wheel(root: Path, extra: dict[str, bytes] | None = None) -> tuple[Path, Path]:
    files = {
        "example_evaluator/__init__.py": SOURCE,
        f"{DIST_INFO}/METADATA": b"Metadata-Version: 2.1\nName: example-evaluator\nVersion: 1.0\n",
        f"{DIST_INFO}/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{DIST_INFO}/entry_points.txt": (
            b"[robotics_acceptance.evaluators]\norg.example = example_evaluator:evaluate\n"
        ),
        **(extra or {}),
    }
    files[f"{DIST_INFO}/RECORD"] = record_bytes(files, f"{DIST_INFO}/RECORD")
    wheel = root / "example_evaluator-1.0-py3-none-any.whl"
    with ZipFile(wheel, "w") as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
    installed = root / "site-packages"
    for name, payload in files.items():
        path = installed / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return wheel, installed


@pytest.fixture
def probe_profile(tmp_path: Path) -> GitHubVerifierProfile:
    # This profile is solely a unit probe; it does not prove publisher identity.
    executable = tmp_path / "verifier"
    executable.write_bytes(b"unit-runner-probe")
    roots = tmp_path / "roots.jsonl"
    roots.write_bytes(b"unit-roots-probe")
    return GitHubVerifierProfile(
        executable,
        hashlib.sha256(executable.read_bytes()).hexdigest(),
        "2.102.0",
        roots,
        hashlib.sha256(roots.read_bytes()).hexdigest(),
    )


def admit_unit_wheel(
    monkeypatch: pytest.MonkeyPatch,
    wheel: Path,
    profile: GitHubVerifierProfile,
    limits: TrustLimits = trust.DEFAULT_TRUST_LIMITS,
) -> trust.AuthenticatedWheel:
    # Mock crypto only to test the independent installation-binding contract.
    monkeypatch.setattr(trust, "_verify_snapshot", lambda *args: b'[{"verificationResult":{}}]')
    bundle = wheel.parent / "bundle.jsonl"
    bundle.write_bytes(b"unit-bundle")
    policy = GitHubWheelPolicy(
        "example/evaluators",
        "https://github.com/example/evaluators/.github/workflows/release.yml@refs/tags/v1",
        hashlib.sha256(wheel.read_bytes()).hexdigest(),
    )
    return authenticate_wheel(wheel, bundle, policy=policy, profile=profile, limits=limits)


def test_installed_sources_are_bound_to_original_wheel_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_profile: GitHubVerifierProfile
) -> None:
    wheel, installed = fixture_wheel(tmp_path)
    authenticated = admit_unit_wheel(monkeypatch, wheel, probe_profile)
    bound = verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))
    source = installed / "example_evaluator/__init__.py"
    assert bound.sources[source] == SOURCE
    assert bound.distribution == "example-evaluator"
    source.write_bytes(b"replaced after capture")
    wheel.write_bytes(b"replaced after authentication")
    assert bound.sources[source] == SOURCE
    assert authenticated.wheel_bytes != wheel.read_bytes()
    with pytest.raises(TypeError):
        cast(Any, bound.sources)[source] = b"cannot mutate"


def test_tampered_source_and_rewritten_record_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_profile: GitHubVerifierProfile
) -> None:
    wheel, installed = fixture_wheel(tmp_path)
    authenticated = admit_unit_wheel(monkeypatch, wheel, probe_profile)
    source = installed / "example_evaluator/__init__.py"
    source.write_bytes(b"def evaluate(context):\n    raise RuntimeError('altered')\n")
    members = {
        path.relative_to(installed).as_posix(): path.read_bytes()
        for path in installed.rglob("*")
        if path.is_file() and path.name != "RECORD"
    }
    (installed / DIST_INFO / "RECORD").write_bytes(record_bytes(members, f"{DIST_INFO}/RECORD"))
    with pytest.raises(EvaluatorTrustError, match="authenticated wheel"):
        verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))


@pytest.mark.parametrize("extra", ["hidden.py", "hidden.so", "__pycache__/hidden.pyc"])
def test_namespace_files_omitted_from_record_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe_profile: GitHubVerifierProfile,
    extra: str,
) -> None:
    wheel, installed = fixture_wheel(tmp_path)
    authenticated = admit_unit_wheel(monkeypatch, wheel, probe_profile)
    path = installed / "example_evaluator" / extra
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"unadmitted")
    with pytest.raises(EvaluatorTrustError, match="extra file"):
        verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))


def test_installed_record_cannot_omit_original_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_profile: GitHubVerifierProfile
) -> None:
    wheel, installed = fixture_wheel(tmp_path)
    authenticated = admit_unit_wheel(monkeypatch, wheel, probe_profile)
    record = installed / DIST_INFO / "RECORD"
    rows = list(csv.reader(io.StringIO(record.read_text())))
    record.write_text("".join(",".join(row) + "\n" for row in rows if row[0].endswith("RECORD")))
    with pytest.raises(EvaluatorTrustError, match="omits original"):
        verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))


@pytest.mark.parametrize(
    "extra", ["extra.dist-info/WHEEL", "example_evaluator.data/scripts/script"]
)
def test_other_wheel_layouts_are_not_silently_admitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe_profile: GitHubVerifierProfile,
    extra: str,
) -> None:
    wheel, installed = fixture_wheel(tmp_path, {extra: b"unsupported"})
    authenticated = admit_unit_wheel(monkeypatch, wheel, probe_profile)
    with pytest.raises(EvaluatorTrustError):
        verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))


def test_duplicate_zip_names_are_rejected_before_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_profile: GitHubVerifierProfile
) -> None:
    wheel, installed = fixture_wheel(tmp_path)
    with ZipFile(wheel, "a") as archive, pytest.warns(UserWarning, match="Duplicate"):
        archive.writestr("example_evaluator/__init__.py", b"shadow")
    authenticated = admit_unit_wheel(monkeypatch, wheel, probe_profile)
    with pytest.raises(EvaluatorTrustError, match="duplicate member"):
        verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))


def test_zip_traversal_and_expansion_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_profile: GitHubVerifierProfile
) -> None:
    wheel, installed = fixture_wheel(tmp_path)
    with ZipFile(wheel, "a") as archive:
        archive.writestr("../escape.py", b"escape")
    authenticated = admit_unit_wheel(monkeypatch, wheel, probe_profile)
    with pytest.raises(EvaluatorTrustError, match="noncanonical"):
        verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))
    limited = admit_unit_wheel(monkeypatch, wheel, probe_profile, TrustLimits(max_expanded_bytes=1))
    with pytest.raises(EvaluatorTrustError, match="expanded byte"):
        verify_installed_wheel(limited, Distribution.at(installed / DIST_INFO))


def test_unserialized_admission_cannot_be_constructed_from_a_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_profile: GitHubVerifierProfile
) -> None:
    wheel, installed = fixture_wheel(tmp_path)
    authenticated = admit_unit_wheel(monkeypatch, wheel, probe_profile)
    fabricated = replace(authenticated, wheel_bytes=b"altered unsigned wheel")
    with pytest.raises(EvaluatorTrustError, match="in-memory"):
        verify_installed_wheel(fabricated, Distribution.at(installed / DIST_INFO))


def test_old_verifier_and_changed_operator_files_are_rejected(
    tmp_path: Path, probe_profile: GitHubVerifierProfile
) -> None:
    with pytest.raises(EvaluatorTrustError, match="2.102.0"):
        replace(probe_profile, version="2.101.0")
    wheel, _ = fixture_wheel(tmp_path)
    bundle = tmp_path / "bundle"
    bundle.write_bytes(b"not crypto")
    policy = GitHubWheelPolicy(
        "example/evaluators",
        "https://github.com/example/release@refs/tags/v1",
        hashlib.sha256(wheel.read_bytes()).hexdigest(),
    )
    profile = replace(probe_profile, executable_sha256="0" * 64)
    with pytest.raises(EvaluatorTrustError, match="operator profile"):
        authenticate_wheel(wheel, bundle, policy=policy, profile=profile)


@pytest.mark.parametrize("value", [0, -1, True])
def test_limits_refuse_nonpositive_or_boolean_sizes(value: int) -> None:
    with pytest.raises(EvaluatorTrustError, match="positive integer"):
        TrustLimits(max_wheel_bytes=value)


@pytest.mark.skipif(
    not os.environ.get("ROBOTICS_TRUST_PROFILE"), reason="requires admitted gh profile"
)
def test_official_verifier_accepts_signed_bytes_and_refuses_forged_json(tmp_path: Path) -> None:
    import json

    settings = json.loads(Path(os.environ["ROBOTICS_TRUST_PROFILE"]).read_bytes())
    profile = GitHubVerifierProfile(
        Path(settings["executable"]),
        settings["executable_sha256"],
        settings["version"],
        Path(settings["trusted_root"]),
        settings["trusted_root_sha256"],
    )
    policy = GitHubWheelPolicy(**settings["policy"])
    wheel = authenticate_wheel(
        settings["wheel"], settings["bundle"], policy=policy, profile=profile
    )
    assert wheel.sha256 == policy.wheel_sha256
    false_proof = tmp_path / "verification.json"
    false_proof.write_text('{"verified":true,"subject":{"sha256":"' + wheel.sha256 + '"}}')
    with pytest.raises(EvaluatorTrustError, match="refused"):
        authenticate_wheel(settings["wheel"], false_proof, policy=policy, profile=profile)
    other_publisher = replace(
        policy, certificate_identity="https://github.com/other/release@refs/tags/v1"
    )
    with pytest.raises(EvaluatorTrustError, match="refused"):
        authenticate_wheel(
            settings["wheel"], settings["bundle"], policy=other_publisher, profile=profile
        )


def test_pip_derived_cache_is_ignored_without_expanding_authenticated_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_profile: GitHubVerifierProfile
) -> None:
    import py_compile

    wheel, installed = fixture_wheel(tmp_path)
    authenticated = admit_unit_wheel(monkeypatch, wheel, probe_profile)
    source = installed / "example_evaluator/__init__.py"
    cache_name = py_compile.compile(str(source), doraise=True)
    assert cache_name is not None
    cache = Path(cache_name)
    record = installed / DIST_INFO / "RECORD"
    with record.open("a", newline="") as stream:
        csv.writer(stream).writerow((cache.relative_to(installed).as_posix(), "", ""))
    # The captured source loader never reads this derived cache, even if corrupted.
    cache.write_bytes(b"opaque, invalid derived cache")
    bound = verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))
    assert bound.sources[source] == SOURCE
    assert cache not in bound.paths
    assert cache not in bound.files
    assert cache not in bound.sources


def test_a_different_distribution_metadata_object_is_not_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_profile: GitHubVerifierProfile
) -> None:
    wheel, installed = fixture_wheel(tmp_path)
    authenticated = admit_unit_wheel(monkeypatch, wheel, probe_profile)
    other = installed / "other-1.0.dist-info"
    other.mkdir()
    for name in ("METADATA", "WHEEL"):
        (other / name).write_bytes((installed / DIST_INFO / name).read_bytes())
    (other / "entry_points.txt").write_bytes(
        b"[robotics_acceptance.evaluators]\norg.other = malicious:evaluate\n"
    )
    with pytest.raises(EvaluatorTrustError, match="metadata differs"):
        verify_installed_wheel(authenticated, Distribution.at(other))


def test_normal_pip_caches_have_a_separate_record_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_profile: GitHubVerifierProfile
) -> None:
    import py_compile

    modules = {f"example_evaluator/module_{i}.py": b"VALUE = 1\n" for i in range(5)}
    wheel, installed = fixture_wheel(tmp_path, modules)
    with ZipFile(wheel) as archive:
        count = len(archive.infolist())
    authenticated = admit_unit_wheel(
        monkeypatch, wheel, probe_profile, TrustLimits(max_members=count)
    )
    record = installed / DIST_INFO / "RECORD"
    with record.open("a", newline="") as stream:
        for source in (installed / "example_evaluator").glob("*.py"):
            cache_name = py_compile.compile(str(source), doraise=True)
            assert cache_name is not None
            cache = Path(cache_name)
            csv.writer(stream).writerow((cache.relative_to(installed).as_posix(), "", ""))
    bound = verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))
    assert len(bound.sources) == 6


@pytest.mark.parametrize("name", ["hook.pth", "sitecustomize.py", "usercustomize.py"])
def test_startup_hooks_are_rejected_before_installation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe_profile: GitHubVerifierProfile,
    name: str,
) -> None:
    wheel, _ = fixture_wheel(tmp_path, {name: b"raise RuntimeError('startup')\n"})
    authenticated = admit_unit_wheel(monkeypatch, wheel, probe_profile)
    with pytest.raises(EvaluatorTrustError, match="startup hooks"):
        trust.validate_evaluator_wheel(authenticated)


def test_namespace_cache_walk_has_a_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_profile: GitHubVerifierProfile
) -> None:
    wheel, installed = fixture_wheel(tmp_path)
    authenticated = admit_unit_wheel(
        monkeypatch, wheel, probe_profile, TrustLimits(max_cache_entries=1)
    )
    cache = installed / "example_evaluator/__pycache__"
    cache.mkdir()
    for tag in ("cpython-312", "cpython-313"):
        (cache / f"__init__.{tag}.pyc").write_bytes(b"never read")
    with pytest.raises(EvaluatorTrustError, match="entry budget"):
        verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))


def test_verifier_process_surface_is_closed_and_has_no_shell() -> None:
    import ast

    tree = ast.parse(Path(str(trust.__file__)).read_bytes())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
    ]
    assert len(calls) == 1 and isinstance(calls[0].func, ast.Attribute)
    assert calls[0].func.attr == "run"
    keywords = {item.arg: item.value for item in calls[0].keywords}
    assert isinstance(keywords["shell"], ast.Constant)
    assert keywords["shell"].value is False
    assert isinstance(keywords["cwd"], ast.Name)
    assert keywords["cwd"].id == "directory"
    assert isinstance(keywords["env"], ast.Call)
    runner = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_run_tool"
    )
    assert calls[0] in list(ast.walk(runner))


def test_verifier_refuses_general_process_argv(tmp_path: Path) -> None:
    for command in (
        ["unapproved", "attestation", "verify"],
        [str(tmp_path / "gh"), "auth", "login"],
        [str(tmp_path / "gh"), "workflow", "run"],
    ):
        with pytest.raises(EvaluatorTrustError, match="snapshot verifier commands"):
            trust._run_tool(command, tmp_path, TrustLimits())


def test_only_pinned_file_snapshots_reach_the_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_profile: GitHubVerifierProfile
) -> None:
    wheel, _ = fixture_wheel(tmp_path)
    bundle = tmp_path / "bundle.jsonl"
    bundle.write_bytes(b"unit-bundle")
    original = wheel.read_bytes()
    calls: list[list[str]] = []

    def runner(command: list[str], directory: Path, limits: TrustLimits) -> bytes:
        calls.append(command)
        assert Path(command[0]).read_bytes() == probe_profile.executable.read_bytes()
        assert hashlib.sha256(Path(command[0]).read_bytes()).hexdigest() == (
            probe_profile.executable_sha256
        )
        if command[1:] == ["--version"]:
            return b"gh version 2.102.0 (unit runner)\n"
        assert command[1:3] == ["attestation", "verify"]
        assert Path(command[3]).read_bytes() == original
        assert Path(command[command.index("--bundle") + 1]).read_bytes() == b"unit-bundle"
        assert Path(command[command.index("--custom-trusted-root") + 1]).read_bytes() == (
            probe_profile.trusted_root.read_bytes()
        )
        wheel.write_bytes(b"original path changed during verification")
        return b'[{"verificationResult":{}}]'

    monkeypatch.setattr(trust, "_run_tool", runner)
    policy = GitHubWheelPolicy(
        "example/evaluators",
        "https://github.com/example/release@refs/tags/v1",
        hashlib.sha256(original).hexdigest(),
    )
    admitted = authenticate_wheel(wheel, bundle, policy=policy, profile=probe_profile)
    assert len(calls) == 2
    assert admitted.wheel_bytes == original
    assert admitted.wheel_bytes != wheel.read_bytes()


def test_installation_admission_is_factory_issued_and_cannot_be_reconstructed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_profile: GitHubVerifierProfile
) -> None:
    wheel, installed = fixture_wheel(tmp_path)
    authenticated = admit_unit_wheel(monkeypatch, wheel, probe_profile)
    issued = verify_installed_wheel(authenticated, Distribution.at(installed / DIST_INFO))
    trust.require_authenticated_installation(issued)
    reconstructed = replace(issued)
    with pytest.raises(EvaluatorTrustError, match="not issued"):
        trust.require_authenticated_installation(reconstructed)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="requires the POSIX input profile")
def test_fifo_is_refused_without_waiting_for_a_writer(tmp_path: Path) -> None:
    import subprocess
    import sys

    fifo = tmp_path / "input.fifo"
    os.mkfifo(fifo)
    script = (
        "import sys; from pathlib import Path; "
        "from robotics_acceptance_harness.evaluator_trust import read_once, EvaluatorTrustError; "
        "\ntry:\n read_once(Path(sys.argv[1]), 1024)"
        "\nexcept EvaluatorTrustError:\n sys.exit(0)"
        "\nelse:\n sys.exit(1)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(fifo)],
        check=False,
        timeout=5,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr.decode()
