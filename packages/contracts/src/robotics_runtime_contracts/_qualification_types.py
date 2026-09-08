from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from robotics_runtime_contracts.errors import ContractError


@dataclass(frozen=True, slots=True)
class QualificationArtifact:
    """A supplied artifact descriptor; a digest is verified only by the file loader."""

    kind: str
    subject_name: str
    sha256: str
    size_bytes: int
    document: Mapping[str, Any] | None


@dataclass(frozen=True, slots=True)
class QualificationDiagnostic:
    error_id: str
    message: str
    check: str
    subject_name: str | None = None
    json_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "error_id": self.error_id,
            "message": self.message,
            "check": self.check,
            **({"subject_name": self.subject_name} if self.subject_name is not None else {}),
            **({"path": self.json_path} if self.json_path is not None else {}),
        }


class QualificationError(ContractError):
    """Expected qualification failures, optionally containing several diagnostics."""

    error_id = "qualification.invalid"

    def __init__(
        self,
        message: str,
        *,
        error_id: str | None = None,
        json_path: str | None = None,
        diagnostics: Sequence[QualificationDiagnostic] = (),
        blocked_checks: Sequence[str] = (),
    ) -> None:
        self.diagnostics = tuple(diagnostics)
        self.blocked_checks = tuple(blocked_checks)
        super().__init__(message, error_id=error_id, json_path=json_path)


@dataclass(frozen=True, slots=True)
class QualificationReport:
    """Independent check outcomes; dependent checks may be blocked by bad inputs."""

    artifacts: tuple[QualificationArtifact, ...]
    diagnostics: tuple[QualificationDiagnostic, ...]
    run_id: str | None = None
    generated_at: str | None = None
    blocked_checks: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return (
            not self.diagnostics
            and not self.blocked_checks
            and self.run_id is not None
            and self.generated_at is not None
        )

    def raise_for_errors(self) -> None:
        if self.diagnostics:
            first = self.diagnostics[0]
            raise QualificationError(
                first.message,
                error_id=first.error_id,
                json_path=first.json_path,
                diagnostics=self.diagnostics,
                blocked_checks=self.blocked_checks,
            )
        if self.blocked_checks:
            raise QualificationError(
                "qualification has blocked checks",
                blocked_checks=self.blocked_checks,
            )

    def metadata(self) -> dict[str, Any]:
        self.raise_for_errors()
        if self.run_id is None or self.generated_at is None:
            raise QualificationError("qualification has no validated run identity")
        return {
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "artifacts": [
                {"kind": item.kind, "subject_name": item.subject_name, "sha256": item.sha256}
                for item in sorted(self.artifacts, key=lambda item: item.subject_name)
            ],
        }
