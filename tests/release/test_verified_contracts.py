"""Release authentication controls use simulated transports, not a fictitious C22 release."""

from __future__ import annotations

import io
import json
import subprocess
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from scripts.release import verified_contracts as verify
from scripts.release.plan import ReleaseError, ReleasePlan

REPOSITORY = "mmkolpakov/robotics-runtime"
FILENAME = "robotics_runtime_contracts-0.22.0-py3-none-any.whl"
BLOB = b"release control payload"
DIGEST = sha256(BLOB).hexdigest()
COMMIT = "b" * 40
TREE = "c" * 40


def plan() -> ReleasePlan:
    return ReleasePlan(
        candidate="harness-v0.23.0",
        key="harness",
        package="robotics-acceptance-harness",
        version="0.23.0",
        commit="d" * 40,
        tree="e" * 40,
        source_date_epoch="1",
        dry_run=True,
        contracts_version="0.22.0",
        contracts_tag="contracts-v0.22.0",
        contracts_commit=COMMIT,
        contracts_tree=TREE,
        contracts_requirement="robotics-runtime-contracts<0.23,>=0.22",
    )


def configure(
    monkeypatch: pytest.MonkeyPatch,
    *,
    failed: str | None = None,
    tamper: bool = False,
    pypi_digest: str = DIGEST,
) -> list[list[str]]:
    calls: list[list[str]] = []
    monkeypatch.setattr(verify, "verify_contracts_tree", lambda *_: (COMMIT, TREE))
    monkeypatch.setattr(verify, "verify_published_release", lambda *_: None)

    def gh(arguments: list[str]) -> str:
        calls.append(arguments)
        operation = arguments[0] + ":" + arguments[1]
        if operation == failed:
            raise ReleaseError("stock verification refused")
        if operation == "release:download":
            (Path(arguments[arguments.index("--dir") + 1]) / FILENAME).write_bytes(BLOB)
            return ""
        if tamper and operation == "attestation:verify":
            Path(arguments[2]).write_bytes(b"changed")
        return '{"unit_report":"raw stock output; no simulated signature verdict"}'

    monkeypatch.setattr(verify, "_gh", gh)
    monkeypatch.setattr(verify, "_pypi_bytes", lambda *_: {"sha256": pypi_digest})
    return calls


def test_exact_stock_source_workflow_and_hosted_runner_policies_are_mandatory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = configure(monkeypatch)
    wheel, result = verify.authenticate_contracts(
        plan(), tmp_path, tmp_path / "contracts", REPOSITORY
    )
    assert wheel.read_bytes() == BLOB
    assert calls[-1] == [
        "attestation",
        "verify",
        str(wheel),
        "--repo",
        REPOSITORY,
        "--source-digest",
        COMMIT,
        "--signer-workflow",
        REPOSITORY + "/.github/workflows/release.yml",
        "--deny-self-hosted-runners",
        "--format",
        "json",
    ]
    assert calls[0] == [
        "release",
        "verify",
        "contracts-v0.22.0",
        "--repo",
        REPOSITORY,
        "--format",
        "json",
    ]
    assert calls[2] == [
        "release",
        "verify-asset",
        "contracts-v0.22.0",
        str(wheel),
        "--repo",
        REPOSITORY,
        "--format",
        "json",
    ]
    assert result["sha256"] == result["pypi"]["sha256"] == DIGEST
    assert result["source_verification"].startswith('{"unit_report"')


@pytest.mark.parametrize("failed", ["release:verify", "release:verify-asset", "attestation:verify"])
def test_any_stock_verifier_refusal_stops_before_pypi_or_installed_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed: str,
) -> None:
    configure(monkeypatch, failed=failed)
    monkeypatch.setattr(verify, "_pypi_bytes", lambda *_: pytest.fail("PyPI/installer reached"))
    with pytest.raises(ReleaseError, match="stock verification refused"):
        verify.authenticate_contracts(plan(), tmp_path, tmp_path / "contracts", REPOSITORY)


@pytest.mark.parametrize(
    ("tamper", "pypi", "reason"),
    [
        (True, DIGEST, "changed during authentication"),
        (False, "f" * 64, "PyPI contracts bytes differ"),
    ],
)
def test_successful_verifiers_do_not_substitute_changed_or_different_pypi_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: bool,
    pypi: str,
    reason: str,
) -> None:
    configure(monkeypatch, tamper=tamper, pypi_digest=pypi)
    with pytest.raises(ReleaseError, match=reason):
        verify.authenticate_contracts(plan(), tmp_path, tmp_path / "contracts", REPOSITORY)


def test_missing_stable_release_refuses_before_authentication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure(monkeypatch)

    def absent(*_args: Any) -> None:
        raise ReleaseError("selected release is not published")

    monkeypatch.setattr(verify, "verify_published_release", absent)
    monkeypatch.setattr(verify, "_gh", lambda *_: pytest.fail("authentication/download began"))
    with pytest.raises(ReleaseError, match="not published"):
        verify.authenticate_contracts(plan(), tmp_path, tmp_path / "contracts", REPOSITORY)


def test_failed_stock_command_cannot_become_a_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            a, 1, stdout='{"looks":"valid"}', stderr="verification failed"
        ),
    )
    with pytest.raises(ReleaseError, match="authentication/download failed"):
        verify._gh(["attestation", "verify", "selected.whl", "--repo", REPOSITORY])


class Response(io.BytesIO):
    def geturl(self) -> str:
        return "https://files.pythonhosted.org/selected.whl"


@pytest.mark.parametrize(
    "case", ["valid", "changed", "truncated", "wrong-host", "yanked", "wrong-version"]
)
def test_pypi_check_hashes_actual_response_bytes(
    monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    metadata: dict[str, Any] = {
        "info": {"version": "0.22.0"},
        "urls": [
            {
                "filename": FILENAME,
                "yanked": False,
                "size": len(BLOB),
                "digests": {"sha256": DIGEST},
                "url": "https://files.pythonhosted.org/selected.whl",
            }
        ],
    }
    payload = BLOB
    if case == "changed":
        payload = b"X" + BLOB[1:]
    if case == "truncated":
        payload = BLOB[:-1]
    if case == "wrong-host":
        metadata["urls"][0]["url"] = "https://example.org/wheel"
    if case == "yanked":
        metadata["urls"][0]["yanked"] = True
    if case == "wrong-version":
        metadata["info"]["version"] = "0.21.1"

    def opened(url: str, **_kwargs: Any) -> Response:
        return Response(json.dumps(metadata).encode() if url.endswith("/json") else payload)

    monkeypatch.setattr(verify, "urlopen", opened)
    if case == "valid":
        assert verify._pypi_bytes("0.22.0", FILENAME, len(BLOB))["sha256"] == DIGEST
    else:
        with pytest.raises(ReleaseError):
            verify._pypi_bytes("0.22.0", FILENAME, len(BLOB))
