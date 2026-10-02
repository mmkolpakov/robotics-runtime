# Function complexity budgets

CI runs Ruff `C901` (complexity 10) and `PLR0913` (five arguments) across both
packages. Existing violations have measured
values recorded by file, qualified function name and rule in
`complexity-budgets.json`; line changes do not change a function's identity.

New violations, increases and stale budgets fail CI. Existing violations remain visible debt,
to be removed as their functions are refactored. This gate supplements the
unconditional Ruff checks; it does not claim the existing functions meet the
default limits.

After reducing a function's complexity, CI requires lowering or removing its budget
in the same commit. `uv run python scripts/ci/check_complexity.py --write-baseline` generates
the candidate file. Review the diff: an unrelated increase is a regression, not
a reason to refresh all budgets. CI never rewrites this file.

The root development dependency and pre-commit hook pin Ruff **0.16.9**.
The gate reads Ruff's JSON diagnostics and extracts measured values from the
`C901`/`PLR0913` message text. An unexpected format fails the gate. A Ruff upgrade
must review that parser and its function-identity and budget regressions together;
see [ADR 0011](../packages/contracts/docs/decisions/0011-retain-the-pinned-ruff-budget-parser.md).
