"""Scoped CLI logging and bounded diagnostics for completed commands."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from typing import Any

from robotics_acceptance_harness.diagnostics import error_diagnostic, write_command_diagnostic
from robotics_acceptance_harness.errors import HarnessError, command_error_boundary

_MAX_WARNINGS = 100
_MAX_FIELD_LENGTH = 4096
_LOG_FIELDS = (
    "source_path",
    "line_number",
    "metric_name",
    "attribute_key",
    "otlp_type",
)
_ACTIVE_REPORT: ContextVar[_CommandReport | None] = ContextVar("command_report", default=None)


def _warning_payload(record: logging.LogRecord) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "diagnostic_id": str(getattr(record, "diagnostic_id", "log.warning"))[:_MAX_FIELD_LENGTH],
        "level": record.levelname.lower(),
        "message": record.getMessage()[:_MAX_FIELD_LENGTH],
    }
    for name in _LOG_FIELDS:
        value = getattr(record, name, None)
        if isinstance(value, (str, int)):
            payload[name] = value[:_MAX_FIELD_LENGTH] if isinstance(value, str) else value
    return payload


def _display_record(record: logging.LogRecord) -> logging.LogRecord:
    """Bound console text without mutating the caller's record or rendering its traceback."""
    return logging.makeLogRecord(
        record.__dict__
        | {
            "msg": record.getMessage()[:_MAX_FIELD_LENGTH],
            "args": (),
            "diagnostic_id": str(getattr(record, "diagnostic_id", "command"))[:_MAX_FIELD_LENGTH],
            "exc_info": None,
            "exc_text": None,
            "stack_info": None,
        }
    )


class _DiagnosticHandler(logging.StreamHandler[Any]):
    def __init__(self, display_level: int) -> None:
        super().__init__(sys.stderr)
        self.display_level = display_level
        self.warnings: dict[str, dict[str, Any]] = {}
        self.omitted_warnings = 0
        self.setFormatter(
            logging.Formatter(
                "%(levelname)s: [%(diagnostic_id)s] %(message)s",
                defaults={"diagnostic_id": "command"},
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        active = _ACTIVE_REPORT.get()
        if active is not None and active.handler is not self:
            return
        if record.levelno >= logging.WARNING:
            payload = _warning_payload(record)
            key = json.dumps(payload, sort_keys=True)
            if key in self.warnings:
                self.warnings[key]["occurrences"] += 1
                return
            if len(self.warnings) >= _MAX_WARNINGS:
                self.omitted_warnings += 1
                return
            self.warnings[key] = payload | {"occurrences": 1}
        if record.levelno >= self.display_level:
            super().emit(_display_record(record))


class _CommandReport:
    def __init__(self) -> None:
        self.command = ""
        self.destination: str | None = None
        self.error: HarnessError | None = None
        self.handler: _DiagnosticHandler | None = None
        self.previous_logging: tuple[int, bool, bool, list[logging.Handler]] | None = None

    def configure(self, command: str, destination: str | None, level: str) -> None:
        self.command, self.destination = command, destination
        logger = logging.getLogger("robotics_acceptance_harness")
        self.previous_logging = (
            logger.level,
            logger.propagate,
            logger.disabled,
            list(logger.handlers),
        )
        self.handler = _DiagnosticHandler(logging.getLevelNamesMapping()[level])
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.addHandler(self.handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        logger.disabled = False
        logger.info("command %s started", command)

    def finish(self, exit_code: int) -> int:
        logger = logging.getLogger("robotics_acceptance_harness")
        logger.info("command %s completed with exit code %d", self.command, exit_code)
        if self.destination is None:
            return exit_code
        payload = (
            error_diagnostic(command=self.command, error=self.error)
            if self.error is not None
            else {"command": self.command, "status": "completed", "exit_code": exit_code}
        )
        if self.handler is not None and self.handler.warnings:
            payload["warnings"] = list(self.handler.warnings.values())
        if self.handler is not None and self.handler.omitted_warnings:
            payload["omitted_warnings"] = self.handler.omitted_warnings
        try:
            with command_error_boundary():
                write_command_diagnostic(self.destination, payload)
        except HarnessError as error:
            print(f"error: cannot write diagnostic: {error}", file=sys.stderr)
            return exit_code if self.error is not None else error.exit_code
        return exit_code

    def close(self) -> None:
        if self.handler is not None and self.previous_logging is not None:
            logger = logging.getLogger("robotics_acceptance_harness")
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
            for handler in self.previous_logging[3]:
                logger.addHandler(handler)
            logger.setLevel(self.previous_logging[0])
            logger.propagate = self.previous_logging[1]
            logger.disabled = self.previous_logging[2]
            self.handler.close()


def configure_command(command: str, destination: str | None, level: str) -> None:
    report = _ACTIVE_REPORT.get()
    if report is not None:
        report.configure(command, destination, level)


def record_command_error(error: HarnessError) -> None:
    report = _ACTIVE_REPORT.get()
    if report is not None:
        report.error = error


def command_reporting[**P](command: Callable[P, int]) -> Callable[P, int]:
    @wraps(command)
    def run(*args: P.args, **kwargs: P.kwargs) -> int:
        report = _CommandReport()
        token = _ACTIVE_REPORT.set(report)
        try:
            return report.finish(command(*args, **kwargs))
        except SystemExit:
            if report.error is not None:
                report.finish(report.error.exit_code)
            raise
        finally:
            try:
                report.close()
            finally:
                _ACTIVE_REPORT.reset(token)

    return run
