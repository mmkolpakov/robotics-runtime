# Function complexity budgets

CI runs Ruff `C901` (complexity 10) and `PLR0913` (five arguments) across both
packages. The initial workspace contains 68 existing violations. Their measured
values are recorded by file, qualified function name and rule in
`complexity-budgets.json`; line changes do not change a function's identity.

New violations and increases fail CI. Existing violations remain visible debt,
to be removed by the planned module refactorings. This gate supplements the
unconditional Ruff checks; it does not claim the existing functions meet the
default limits.

After reducing a function's complexity, lower or remove its budget in the same
commit. `uv run python scripts/ci/check_complexity.py --write-baseline` generates
the candidate file. Review the diff: an unrelated increase is a regression, not
a reason to refresh all budgets. CI never rewrites this file.
