# Retain the Pinned Ruff Budget Parser

- Status: accepted
- Date: 2026-10-02
- Decision: T09

## Context and Problem Statement

The shared workspace tracks existing complexity and argument-count debt by
function. Ruff's JSON diagnostics identify violations, but their measured
values are currently extracted from diagnostic message text.

## Decision Outcome

Keep Ruff **0.16.9** pinned in the root development dependency, lockfile and
pre-commit hook. Retain the narrow parser in
[`check_complexity.py`](../../../../scripts/ci/check_complexity.py) for `C901`
and `PLR0913`. Unexpected message shapes or rules fail rather than inventing
measurements. Budgets use file, qualified function name and rule, so moving a
function's lines cannot transfer or reset its allowance.

Ruff upgrades must review the parser and
[gate regressions](../../../../tests/ci/test_complexity_gate.py) together.
New violations, growth and stale budgets remain failures; the CI gate never
refreshes the baseline automatically.

## Consequences

This decision governs both workspace packages. Run the gate through the locked
environment: the script itself does not enforce Ruff's version. This small
upstream-dependent seam remains visible debt, without introducing another
complexity engine. Passing budgets prevents regressions; it does not establish
that existing functions meet Ruff's default limits.
