from __future__ import annotations


class ContractError(ValueError):
    """Base for expected contract failures, compatible with ValueError handlers."""

    error_id = "input.invalid"

    def __init__(
        self,
        message: str,
        *,
        error_id: str | None = None,
        json_path: str | None = None,
    ) -> None:
        if error_id is not None:
            self.error_id = error_id
        self.json_path = json_path
        super().__init__(message)


class CLIArgumentError(ContractError):
    """Raised for invalid command-line arguments, including argument combinations."""

    error_id = "cli.arguments_invalid"
