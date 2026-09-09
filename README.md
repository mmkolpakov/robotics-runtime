# Robotics runtime

Shared development workspace for the robotics runtime contracts and acceptance harness.
The packages retain separate versions and distribution names:

- `robotics-runtime-contracts` validates execution, evidence, and qualification documents.
- `robotics-acceptance-harness` observes existing executions and evaluates their evidence.

Runtime images and deployment compositions are maintained in
[robotics-runtime-infra](https://github.com/mmkolpakov/robotics-runtime-infra).

Package source and history live in `packages/contracts` and `packages/harness`.
Historical release tags use the `contracts-legacy/` and `harness-legacy/` prefixes.
Package-specific documentation remains alongside each package.

## Development

Use Python 3.12–3.14 and uv. The workspace has one lockfile and installs both
packages as editable distributions:

```bash
uv sync --locked --all-packages --all-groups
uv run --directory packages/contracts pytest
uv run --directory packages/harness pytest
uv run ruff check packages
uv run --directory packages/contracts mypy src tests
uv run --directory packages/harness mypy src tests
uv run python scripts/ci/check_complexity.py
```

Run the package test suites in separate processes: each package has its own
`tests` support module. Both distributions can be built independently:

```bash
uv build --package robotics-runtime-contracts --no-sources
uv build --package robotics-acceptance-harness --no-sources
```

The workspace source override is a development setting. Wheels retain normal
versioned package dependencies and are checked in clean environments outside the
workspace before publication.

The shared CI checks both packages on Python 3.12, 3.13 and 3.14, and runs the
[live ROS observer tests](packages/harness/docs/live-tests.md) on ROS 2 Jazzy.
[Function complexity budgets](quality/README.md) keep existing debt visible
and reject new violations or increases until the affected modules are refactored.

The consumers job also checks complete infra qualification bundles and producer
inputs at the immutable revision recorded in `.github/workflows/ci.yml`. To run
that gate locally, set `INFRA_CONSUMER_ROOT` to the infra checkout and
`INFRA_CONSUMER_REVISION` to its full commit SHA, then run
`uv run pytest tests/infra`. The gate requires the checkout to match that revision
and rejects documents supplied under the wrong contract role.
