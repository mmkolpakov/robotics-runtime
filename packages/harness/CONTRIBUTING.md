# Contributing

Open an issue before changing a public contract, safety boundary, or supported
execution mode. Keep product scenes, robot commands, model weights, and launch
orchestration in consuming repositories.

## Local Checks

Run from the workspace root:

```bash
uv sync --locked --all-packages --all-groups
uv run pre-commit run --all-files --show-diff-on-failure
uv run --directory packages/harness pytest \
  -p robotics_acceptance_harness.plugin \
  --robotics-scenario tests/fixtures/simulation/scenario.yaml \
  --robotics-runtime tests/fixtures/simulation/runtime.yaml
uv build --package robotics-acceptance-harness --no-sources
```

Contracts lives in `packages/contracts` in the same workspace. The standard
dependency remains a Semantic Versioning range; `tool.uv.sources` selects that
workspace member only for development. Run the package suites separately to
avoid their independent `tests` support modules sharing one interpreter.

Every behavioral change needs a focused test. Changes to Semgrep policy need a
matching `ruleid` or `ok` example in `.semgrep/attach-only.py`. Pull requests
must pass the required `validate` check and resolve all review conversations.

Use Conventional Commit subjects. Do not commit generated results, evidence,
private scenarios, credentials, or hardware identities.
