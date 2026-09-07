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
uv run --directory packages/contracts mypy src
uv run --directory packages/harness mypy src
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
