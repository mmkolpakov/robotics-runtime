"""Authenticate evaluator wheels with operator-pinned official verifiers.

Trust profiles belong to the integrator's reviewed composition, outside evidence.
An artifact-verification JSON or a saved verifier report is not an admission.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat

# Pinned official verifiers only; argv/path regressions test this boundary.
import subprocess  # nosemgrep: attach-only-no-process-control
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib.metadata import Distribution
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from packaging.utils import InvalidWheelFilename, parse_wheel_filename
from packaging.version import Version

from robotics_acceptance_harness.errors import HarnessError


class EvaluatorTrustError(HarnessError, ValueError):
    """An artifact, publisher, verifier profile or installation was not admitted."""

    error_id = "evaluator_trust.invalid"


def _sha256(value: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise EvaluatorTrustError("expected a lowercase SHA-256 digest")


@dataclass(frozen=True, slots=True)
class TrustLimits:
    max_wheel_bytes: int = 128 * 1024 * 1024
    max_bundle_bytes: int = 16 * 1024 * 1024
    max_tool_bytes: int = 256 * 1024 * 1024
    max_root_bytes: int = 4 * 1024 * 1024
    max_report_bytes: int = 32 * 1024 * 1024
    max_member_bytes: int = 32 * 1024 * 1024
    max_expanded_bytes: int = 256 * 1024 * 1024
    max_members: int = 10_000
    max_cache_entries: int = 30_000
    timeout_sec: int = 60

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise EvaluatorTrustError(f"{name} must be a positive integer")


DEFAULT_TRUST_LIMITS = TrustLimits()


@dataclass(frozen=True, slots=True)
class GitHubVerifierProfile:
    """Operator-admitted executable and trust roots; never load these from evidence."""

    executable: Path
    executable_sha256: str
    version: str
    trusted_root: Path
    trusted_root_sha256: str

    def __post_init__(self) -> None:
        _sha256(self.executable_sha256)
        _sha256(self.trusted_root_sha256)
        if Version(self.version) < Version("2.102.0"):
            raise EvaluatorTrustError("GitHub verifier profile requires gh >=2.102.0")


@dataclass(frozen=True, slots=True)
class GitHubWheelPolicy:
    """Publisher and subject expectations supplied by the trusted integrator."""

    repository: str
    certificate_identity: str
    wheel_sha256: str
    oidc_issuer: str = "https://token.actions.githubusercontent.com"
    predicate_type: str = "https://slsa.dev/provenance/v1"
    source_ref: str | None = None
    source_digest: str | None = None
    signer_digest: str | None = None
    deny_self_hosted_runners: bool = True

    def __post_init__(self) -> None:
        _sha256(self.wheel_sha256)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repository):
            raise EvaluatorTrustError("expected a GitHub owner/repository")
        for value in (self.certificate_identity, self.oidc_issuer, self.predicate_type):
            if not value.startswith("https://") or any(char.isspace() for char in value):
                raise EvaluatorTrustError("identity, issuer and predicate must be exact HTTPS URIs")
        for digest in (self.source_digest, self.signer_digest):
            if digest is not None and not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", digest):
                raise EvaluatorTrustError("source/signer digest must be a full commit digest")
        if self.source_ref is not None and not self.source_ref.startswith("refs/"):
            raise EvaluatorTrustError("source ref must be an exact refs/ value")
        if not isinstance(self.deny_self_hosted_runners, bool):
            raise EvaluatorTrustError("deny_self_hosted_runners must be a boolean")


@dataclass(frozen=True, slots=True)
class CosignKeyVerifierProfile:
    """Operator-admitted Cosign, external public key and explicit offline root."""

    executable: Path
    executable_sha256: str
    version: str
    public_key: Path
    public_key_sha256: str
    trusted_root: Path
    trusted_root_sha256: str

    def __post_init__(self) -> None:
        for digest in (self.executable_sha256, self.public_key_sha256, self.trusted_root_sha256):
            _sha256(digest)
        parsed = Version(self.version)
        if parsed < Version("3.1.3") or parsed.is_prerelease:
            raise EvaluatorTrustError("Cosign key profile requires stable Cosign >=3.1.3")


@dataclass(frozen=True, slots=True)
class CosignKeyWheelPolicy:
    """Signature-by-key-holder policy; no OIDC, log, timestamp or build-origin claim."""

    wheel_sha256: str
    predicate_type: str
    public_key_sha256: str
    trust_mode: Literal["key_only_no_tlog"]

    def __post_init__(self) -> None:
        _sha256(self.wheel_sha256)
        _sha256(self.public_key_sha256)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]*:[^\s]+", self.predicate_type):
            raise EvaluatorTrustError("expected an exact attestation predicate URI")
        if self.trust_mode != "key_only_no_tlog":
            raise EvaluatorTrustError("Cosign key-only/no-tlog policy must be an explicit choice")


_WHEEL_ADMISSION = object()
_INSTALLATION_ADMISSION = object()


@dataclass(frozen=True, slots=True)
class AuthenticatedWheel:
    """In-memory admission returned by authenticate_wheel; not a serialized receipt."""

    filename: str
    wheel_bytes: bytes
    sha256: str
    bundle_sha256: str
    policy: GitHubWheelPolicy | CosignKeyWheelPolicy
    verifier_sha256: str
    trusted_root_sha256: str
    verification_report: bytes
    limits: TrustLimits
    _admission: object | None = field(default=None, init=False, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedInstallation:
    wheel_sha256: str
    distribution: str
    version: str
    paths: frozenset[Path]
    files: Mapping[Path, bytes]
    sources: Mapping[Path, bytes]
    entry_points: tuple[tuple[str, str, str], ...]
    _admission: object | None = field(default=None, init=False, repr=False, compare=False)


def read_once(path: Path, limit: int) -> bytes:
    """Capture bounded regular-file bytes once; never parse a later reread."""

    absolute = Path(os.path.abspath(path.expanduser()))
    if absolute.resolve(strict=True) != absolute:
        raise EvaluatorTrustError(f"input path contains a symlink: {path}")
    required = ("O_NOFOLLOW", "O_NONBLOCK")
    if not all(hasattr(os, name) for name in required):
        raise EvaluatorTrustError("input profile requires POSIX no-follow/nonblocking file opens")
    descriptor = os.open(absolute, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise EvaluatorTrustError(f"input is not a bounded regular file: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            payload = stream.read(limit + 1)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if (
        len(payload) > limit
        or len(payload) != before.st_size
        or any(getattr(before, field) != getattr(after, field) for field in identity)
    ):
        raise EvaluatorTrustError(f"input changed or exceeded its byte limit: {path}")
    return payload


def _pinned_snapshot(path: Path, digest: str, limit: int) -> bytes:
    payload = read_once(path, limit)
    if hashlib.sha256(payload).hexdigest() != digest:
        raise EvaluatorTrustError(f"operator profile file differs from its pinned digest: {path}")
    return payload


def _run_tool(
    command: list[str],
    directory: Path,
    limits: TrustLimits,
    *,
    tool_name: Literal["gh", "cosign"] = "gh",
) -> bytes:
    if tool_name not in {"gh", "cosign"}:
        raise EvaluatorTrustError("unsupported snapshot verifier")
    label = "GitHub" if tool_name == "gh" else "Cosign"
    filename = tool_name + (".exe" if os.name == "nt" else "")
    expected = str(directory / filename)
    admitted = (
        command[1:] == ["--version"] or command[1:3] == ["attestation", "verify"]
        if tool_name == "gh"
        else command[1:] == ["version", "--json"] or command[1:2] == ["verify-blob-attestation"]
    )
    if not command or command[0] != expected or not admitted:
        raise EvaluatorTrustError("only the pinned snapshot verifier commands are admitted")
    output = directory / "verifier-output"
    error = directory / "verifier-error"
    with output.open("wb") as stdout, error.open("wb") as stderr:
        try:
            process = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                timeout=limits.timeout_sec,
                check=False,
                shell=False,
                cwd=directory,
                env=_verifier_environment(directory),
            )
        except subprocess.TimeoutExpired as failure:
            raise EvaluatorTrustError(
                f"{label} attestation verifier exceeded its deadline"
            ) from failure
    report = read_once(output, limits.max_report_bytes)
    diagnostic = read_once(error, limits.max_report_bytes)
    if process.returncode != 0:
        message = diagnostic.decode(errors="replace").strip()
        raise EvaluatorTrustError(f"{label} attestation verification refused: {message}")
    if tool_name == "cosign" and command[1] != "version":
        if len(report) + len(diagnostic) > limits.max_report_bytes:
            raise EvaluatorTrustError("combined verifier audit exceeds its byte limit")
        return report + diagnostic
    return report


def _verifier_environment(directory: Path) -> dict[str, str]:
    environment = {
        "HOME": str(directory / "home"),
        "XDG_CONFIG_HOME": str(directory / "config"),
        "XDG_CACHE_HOME": str(directory / "cache"),
        "GH_CONFIG_DIR": str(directory / "gh-config"),
        "GH_HOST": "github.com",
        "GH_PROMPT_DISABLED": "1",
        "GH_NO_UPDATE_NOTIFIER": "1",
        "GH_NO_EXTENSION_UPDATE_NOTIFIER": "1",
        "NO_COLOR": "1",
        "LC_ALL": "C.UTF-8",
    }
    for name in ("SYSTEMROOT", "WINDIR"):
        if name in os.environ:
            environment[name] = os.environ[name]
    return environment


def _verify_snapshot(
    artifact: tuple[str, bytes],
    bundle: bytes,
    policy: GitHubWheelPolicy,
    profile: GitHubVerifierProfile,
    limits: TrustLimits,
) -> bytes:
    filename, artifact_bytes = artifact
    tool = _pinned_snapshot(profile.executable, profile.executable_sha256, limits.max_tool_bytes)
    roots = _pinned_snapshot(
        profile.trusted_root, profile.trusted_root_sha256, limits.max_root_bytes
    )
    with TemporaryDirectory(prefix="evaluator-verification-") as temporary:
        directory = Path(temporary)
        executable = directory / ("gh.exe" if os.name == "nt" else "gh")
        executable.write_bytes(tool)
        executable.chmod(0o500)
        artifact_path = directory / filename
        artifact_path.write_bytes(artifact_bytes)
        bundle_path = directory / "bundle.jsonl"
        bundle_path.write_bytes(bundle)
        root_path = directory / "trusted-root.jsonl"
        root_path.write_bytes(roots)
        for path in (artifact_path, bundle_path, root_path):
            path.chmod(0o400)
        observed = _run_tool([str(executable), "--version"], directory, limits).decode()
        match = re.match(r"gh version ([0-9]+[.][0-9]+[.][0-9]+)(?: |$)", observed)
        if match is None or Version(match[1]) != Version(profile.version):
            raise EvaluatorTrustError("GitHub verifier version differs from its operator profile")
        command = [
            str(executable),
            "attestation",
            "verify",
            str(artifact_path),
            "--bundle",
            str(bundle_path),
            "--custom-trusted-root",
            str(root_path),
            "--repo",
            policy.repository,
            "--cert-identity",
            policy.certificate_identity,
            "--cert-oidc-issuer",
            policy.oidc_issuer,
            "--predicate-type",
            policy.predicate_type,
            "--digest-alg",
            "sha256",
            "--format",
            "json",
        ]
        for option, value in (
            ("--source-ref", policy.source_ref),
            ("--source-digest", policy.source_digest),
            ("--signer-digest", policy.signer_digest),
        ):
            if value is not None:
                command.extend((option, value))
        if policy.deny_self_hosted_runners:
            command.append("--deny-self-hosted-runners")
        return _run_tool(command, directory, limits)


def authenticate_wheel(
    wheel_path: str | Path,
    bundle_path: str | Path,
    *,
    policy: GitHubWheelPolicy,
    profile: GitHubVerifierProfile,
    limits: TrustLimits = DEFAULT_TRUST_LIMITS,
) -> AuthenticatedWheel:
    """Verify raw wheel bytes using the admitted official tool and external policy.

    No input verification JSON is trusted. The returned original bytes are the
    only wheel payload the installation binder should subsequently consume.
    """

    filename, artifact, bundle = _wheel_inputs(wheel_path, bundle_path, policy.wheel_sha256, limits)
    report = _verify_snapshot((filename, artifact), bundle, policy, profile, limits)
    verified = json.loads(report)
    if not isinstance(verified, list) or not verified:
        raise EvaluatorTrustError("official verifier returned no verified attestations")
    return _wheel_admission((filename, artifact, bundle), policy, profile, report, limits)


def _wheel_inputs(
    wheel_path: str | Path, bundle_path: str | Path, expected_digest: str, limits: TrustLimits
) -> tuple[str, bytes, bytes]:
    wheel_path = Path(wheel_path)
    try:
        parse_wheel_filename(wheel_path.name)
    except InvalidWheelFilename as failure:
        raise EvaluatorTrustError("expected a PyPA wheel filename") from failure
    artifact = read_once(wheel_path, limits.max_wheel_bytes)
    if hashlib.sha256(artifact).hexdigest() != expected_digest:
        raise EvaluatorTrustError("wheel differs from the externally expected subject digest")
    return wheel_path.name, artifact, read_once(Path(bundle_path), limits.max_bundle_bytes)


def _wheel_admission(
    inputs: tuple[str, bytes, bytes],
    policy: GitHubWheelPolicy | CosignKeyWheelPolicy,
    profile: GitHubVerifierProfile | CosignKeyVerifierProfile,
    report: bytes,
    limits: TrustLimits,
) -> AuthenticatedWheel:
    filename, artifact, bundle = inputs
    authenticated = AuthenticatedWheel(
        filename=filename,
        wheel_bytes=artifact,
        sha256=hashlib.sha256(artifact).hexdigest(),
        bundle_sha256=hashlib.sha256(bundle).hexdigest(),
        policy=policy,
        verifier_sha256=profile.executable_sha256,
        trusted_root_sha256=profile.trusted_root_sha256,
        verification_report=report,
        limits=limits,
    )
    object.__setattr__(authenticated, "_admission", _WHEEL_ADMISSION)
    return authenticated


def authenticate_wheel_with_cosign_key(
    wheel_path: str | Path,
    bundle_path: str | Path,
    *,
    policy: CosignKeyWheelPolicy,
    profile: CosignKeyVerifierProfile,
    limits: TrustLimits = DEFAULT_TRUST_LIMITS,
) -> AuthenticatedWheel:
    """Authenticate private wheel bytes against the operator's explicit key policy."""
    if policy.public_key_sha256 != profile.public_key_sha256:
        raise EvaluatorTrustError("publisher key differs from the external verifier profile")
    inputs = _wheel_inputs(wheel_path, bundle_path, policy.wheel_sha256, limits)
    from robotics_acceptance_harness._cosign_key_verifier import verify_snapshot

    report = verify_snapshot(inputs[:2], inputs[2], policy, profile, limits)
    return _wheel_admission(inputs, policy, profile, report, limits)


def verify_installed_wheel(
    wheel: AuthenticatedWheel, distribution: Distribution
) -> AuthenticatedInstallation:
    """Bind captured installed bytes to an in-memory authenticated wheel admission.

    Installer metadata is not an authentication root. Only self-contained purelib
    wheels without script/data/native transformations are admitted by this profile.
    Existing verified-source import guards remain necessary before execution.
    """

    if not isinstance(wheel, AuthenticatedWheel) or wheel._admission is not _WHEEL_ADMISSION:
        raise EvaluatorTrustError(
            "installation requires an authenticated in-memory wheel admission"
        )
    from robotics_acceptance_harness._wheel_binding import bind_installation

    installed = bind_installation(wheel, distribution)
    object.__setattr__(installed, "_admission", _INSTALLATION_ADMISSION)
    return installed


def validate_evaluator_wheel(wheel: AuthenticatedWheel) -> None:
    """Check the supported evaluator profile before installing authenticated bytes.

    Reject startup hooks and unsupported layouts; this cannot undo Python startup
    code that was already executed in an unreviewed environment.
    """

    if not isinstance(wheel, AuthenticatedWheel) or wheel._admission is not _WHEEL_ADMISSION:
        raise EvaluatorTrustError("profile validation requires an authenticated wheel admission")
    from robotics_acceptance_harness._wheel_binding import validate_profile

    validate_profile(wheel)


def require_authenticated_installation(installed: AuthenticatedInstallation) -> None:
    """Require this process to have issued the captured-source admission."""

    if (
        not isinstance(installed, AuthenticatedInstallation)
        or installed._admission is not _INSTALLATION_ADMISSION
    ):
        raise EvaluatorTrustError("installation was not issued by authenticated byte binding")
