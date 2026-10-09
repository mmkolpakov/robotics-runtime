# Contributing

## Scope

Changes must remain independent of a specific robot, simulator scene, model
family, or product rule. Domain data belongs in a digest-pinned namespaced
extension, not in a common schema.

Follow [COMPATIBILITY.md](COMPATIBILITY.md). Published names allow only additive
schema changes; breaking changes require a new schema major, a catalog role,
release notes and a migration plan for every known consumer. Published schema
changes must pass `scripts/check_schema_compatibility.py`, which compares them
with the last release structurally and replays its published documents.
Tagged releases remain immutable.

Architectural changes to this package require an accepted
[MADR](https://adr.github.io/madr/) record in
[`docs/decisions`](docs/decisions/). Product and robot-specific decisions do
not belong in this repository.

## Development

See the workspace [documentation reader instructions](../../README.md#documentation-reader)
when updating public Markdown or SVG documentation.

Requirements: Python 3.12 through 3.14 and [uv](https://docs.astral.sh/uv/).
Run from the workspace root:

```bash
uv sync --locked --all-packages --all-groups
uv run pre-commit run --all-files --show-diff-on-failure
uv run --directory packages/contracts mypy src tests
uv run --directory packages/contracts pytest
uv build --package robotics-runtime-contracts --no-sources
```

Every schema change requires positive and negative fixtures, a metaschema test,
semantic tests where JSON Schema cannot express the invariant, and consumer
integration evidence. The workspace `consumers` job validates producer examples
and harness fixtures together. Update `consumer-examples/` when a public workflow
changes. Pull requests must not include credentials, private data, model
weights, recordings, or hardware identifiers.

## Pull Requests

Keep each commit independently reviewable. Explain the compatibility effect,
the consumer problem being solved, and why an existing schema or extension is
insufficient. CI must pass before merge.

## Dependency Updates

The workspace root `renovate.json` configures Renovate for both packages.
Renovate tracks Python runtime, development and build requirements and `uv.lock`
through its [PEP 621 manager](https://docs.renovatebot.com/modules/manager/pep621/).
The [GitHub Actions manager](https://docs.renovatebot.com/modules/manager/github-actions/)
tracks action SHA pins and the `astral-sh/setup-uv` `version` input. Hook updates
are explicitly enabled through the
[pre-commit manager](https://docs.renovatebot.com/modules/manager/pre-commit/).
The [Dockerfile manager](https://docs.renovatebot.com/modules/manager/dockerfile/)
tracks base images of the live ROS test image.

CI runners are shared with other repositories, so Renovate runs before 6am on
Mondays (Helsinki time), keeps at most three open pull requests and opens at
most two per hour. Minor, patch, digest and pin updates arrive as one grouped
pull request; major updates stay separate, with Ruff and check-jsonschema
package and hook majors grouped together. Lock maintenance runs weekly;
automerge is disabled.

The Python support range, CI matrix and `.python-version` (the minimum supported
development version) are reviewed together when support changes. A dependency
bot update alone must not expand the support claim.

Validate configuration changes with Renovate's official
[config validator](https://docs.renovatebot.com/config-validation/):

```bash
# from the workspace root
renovate-config-validator --strict renovate.json
```

The hosted Renovate app is active for the repository; pending and
rate-limited updates are listed in its Dependency Dashboard issue.
