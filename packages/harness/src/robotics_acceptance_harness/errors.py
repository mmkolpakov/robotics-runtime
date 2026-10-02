"""Common command failure contract and dependency exception translation."""

from collections.abc import Iterator
from contextlib import contextmanager

from robotics_runtime_contracts import ContractError


class HarnessError(Exception):
    """A modeled failure, distinct from a completed acceptance verdict."""

    error_id = "harness.error"
    exit_code = 2

    @property
    def diagnostic_exception(self) -> Exception:
        return self

    @property
    def diagnostic_issues(self) -> tuple[tuple[str, str], ...]:
        return ()


class HarnessInputError(HarnessError, ValueError):
    """Invalid command arguments or values supplied to the harness."""

    error_id = "input.invalid"


class _CommandError(HarnessError):
    """Retain a dependency failure's original type, message and causal chain."""

    def __init__(self, original: Exception) -> None:
        self.original = original
        if isinstance(original, ContractError):
            self.error_id = original.error_id
        elif isinstance(original, OSError):
            self.error_id = "input.io_error"
        elif isinstance(original, ValueError):
            self.error_id = "input.invalid"
        else:
            self.error_id = "internal.error"
        super().__init__(str(original))

    @property
    def diagnostic_exception(self) -> Exception:
        return self.original

    @property
    def diagnostic_issues(self) -> tuple[tuple[str, str], ...]:
        if isinstance(self.original, ContractError) and self.original.json_path:
            return ((self.original.json_path, str(self.original)),)
        return ()


@contextmanager
def command_error_boundary() -> Iterator[None]:
    """Normalize dependency failures while preserving process-control exceptions."""
    try:
        yield
    except HarnessError:
        raise
    except Exception as error:
        raise _CommandError(error) from error


__all__ = ["HarnessError", "HarnessInputError", "command_error_boundary"]
