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

The published pair is
[contracts 0.18.2](https://pypi.org/project/robotics-runtime-contracts/0.18.2/) and
[harness 0.19.1](https://pypi.org/project/robotics-acceptance-harness/0.19.1/).
Harness declares `robotics-runtime-contracts>=0.18,<0.19`; release verification
uses the exact contracts 0.18.2 distribution. Both releases use tags in this
workspace and its [release procedure](docs/releasing.md).

Clean archive installs, source integration fixtures and live ROS observer tests
establish different boundaries. Package publication does not qualify an infra
image, arbitrary consumer, model backend or physical target. The current infra
foundation uses pinned sources; its older published OCI release is a separate
artifact. See the package [compatibility policy](packages/contracts/COMPATIBILITY.md).

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
