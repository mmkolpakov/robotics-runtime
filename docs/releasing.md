# Releasing workspace packages

The root `.github/workflows/release.yml` builds one package per candidate.
`contracts-vX.Y.Z` selects `robotics-runtime-contracts`; `harness-vX.Y.Z` selects
`robotics-acceptance-harness`. An RC tag uses `-rc.N`, for example
`contracts-v0.17.0-rc.1`, corresponding to package version `0.17.0rc1`.
The selected package's committed `pyproject.toml` version must match exactly.
Tag pushes must resolve to the checked-out commit and be reachable from `origin/main`.

## Current readiness and dry runs

The current candidate is **contracts 0.17.0rc1**. Dispatch
`contracts-v0.17.0-rc.1` on its reviewed branch to build and install both archives
without publishing. A successful candidate run does not establish PyPI publisher
registration or a stable release. Harness remains **0.18.0** during development;
its temporary workspace bound admits this contracts candidate. Before the stable
contracts release, replace that bound with `>=0.17,<0.18`. Harness `0.19.0` also
requires its own version, changelog and completed contracts release (SPEC 37).

`workflow_dispatch` requires a `candidate` input and always runs in dry-run mode.
Select the ref containing the reviewed source and matching version. It executes helper
tests, preflight, wheel/sdist builds and isolated installs, then uploads verification
evidence and distributions. Both publication jobs are skipped, including OIDC issuance,
PyPI publishing, GitHub release creation and attestations. There is no publish input.
The workflow must first exist on the default branch for GitHub's manual-run interface.

The same build checks can run locally from the root in a separate tools environment
(POSIX shell example; on Windows use the environment's `Scripts/python.exe`):

```bash
export UV_PROJECT_ENVIRONMENT="$PWD/artifacts/release-tools"
uv sync --locked --only-group dev --no-install-workspace --python 3.12
PY="$UV_PROJECT_ENVIRONMENT/bin/python"
"$PY" -m pytest tests/release
"$PY" -m scripts.release.plan \
  --candidate contracts-v0.17.0-rc.1 --event workflow_dispatch \
  --repository mmkolpakov/robotics-runtime --output artifacts/release/plan.json
uv build --package robotics-runtime-contracts --no-sources --out-dir artifacts/release/dist
"$PY" -m scripts.release.verify_install \
  --plan artifacts/release/plan.json --dist artifacts/release/dist \
  --python 3.12 --report artifacts/release/clean-install.json
```

Use a fresh distribution directory for each candidate. Its only distribution files must
be one wheel and one sdist; the `.gitignore` marker created by uv is allowed. The helpers
do not create tags or releases. A harness preflight also needs fetched workspace tags and
read access through `gh` to the root repository's releases.

## Contracts must be released before harness

The harness preflight derives the contracts tag from the **actual contracts package
version in this checkout**. It never selects a lexically sorted or arbitrary latest tag.
It requires all of the following, even in dry-run mode:

1. Exactly one unconditional, index-based contracts dependency with the selected minor's
   lower bound and exclusive next-minor upper bound. Harness `0.19.*` specifically requires
   `robotics-runtime-contracts>=0.17,<0.18` and a stable contracts `0.17.*` version.
2. The exact root tag `contracts-vX.Y.Z`, with a published, stable, non-draft GitHub release
   in `mmkolpakov/robotics-runtime`. Imported `contracts-legacy/*` tags do not satisfy this.
3. An identical Git tree for the entire `packages/contracts` directory at that tag and
   at the candidate commit. A change to contracts after its release blocks harness until
   contracts is versioned and released again.
4. A `packages/harness/CHANGELOG.md` section for the harness version naming that exact
   contracts tag. Maintainers should link it to the root repository's corresponding release.
5. Successful isolated installation of the exact contracts version from PyPI, with its
   installed source and schema files matching the verified checkout byte for byte.

The imported harness tree has no such changelog or root contracts release tag. Its full
release preflight is therefore blocked until those prerequisites are completed; successful
local builds alone do not establish release readiness.
During local validation on 2026-09-08, contracts wheel and sdist clean installs passed.
Harness wheel and sdist builds passed, but its wheel installation failed because PyPI
could not resolve `robotics-runtime-contracts==0.16.0` (the project JSON endpoint returned
HTTP 404). Harness sdist installation was not attempted after that shared dependency
blocker. No workspace or local-wheel substitute was used for the contracts dependency.

The plan records both commits and package tree IDs, the contracts requirement and source
file SHA-256 digests. The clean-install check binds PyPI's contracts code and resources to
that plan. Merely finding a similarly named tag or an installable version is insufficient.

## Build and installation boundary

The build uses `uv build --package <name> --no-sources`, as recommended by
[uv's packaging guide](https://docs.astral.sh/uv/guides/package/).
Wheel and sdist metadata must agree with their filenames, the candidate and the expected
dependency bounds. Direct URL, local path and VCS dependencies are rejected.

Each archive is copied to its own temporary directory outside the workspace and installed
into a new venv. The installer disables uv configuration and workspace sources, clears
Python/index environment overrides, and uses only PyPI plus that archive. The sdist is
actually built and installed there. Harness installs pin the selected released contracts
version explicitly. `uv pip check` verifies dependency compatibility.

Smoke runs use the clean interpreter with `-I`, without `PYTHONPATH` or editable packages.
They check installed file inventories and digests, schema resource loading, API validation
of the copied consumer example, runtime writer round-trip, structured qualification
diagnostics, the new role resources, and `robotics-contracts validate`. Harness additionally
checks its existing `EvaluationContext`/`ProductEvaluator` exports and
`robotics-acceptance explain`. Contracts has no `--version` option; no harness SDK is assumed
before SPEC 56 introduces one. A temporary directory configured inside the workspace fails.

## External setup before the first publication

Repository code cannot complete or attest to the following account settings. A maintainer
must verify them before enabling publication:

1. Register a GitHub Trusted Publisher separately for **both PyPI projects**, with
   owner `mmkolpakov`, repository `robotics-runtime`, workflow filename `release.yml`, and
   environment `pypi` for contracts and `pypi-harness` for harness. Pending publishers
   for two new projects cannot share the same repository/workflow/environment tuple.
   Follow [PyPI's publisher registration guide][publisher], or configure
   a [pending publisher][pending] if the project does not exist yet. Registration itself
   does not establish that a version is available from PyPI. Do not add
   a long-lived PyPI API token to this workflow.
2. Create the GitHub `pypi` and `pypi-harness` environments, each with required reviewers.
   Permit only `contracts-v*` tags in `pypi` and `harness-v*` tags in `pypi-harness`.
   Check required branch/tag protection independently;
   this workflow does not change rules or the stable `validate` CI context.
3. Enable immutable GitHub releases. The final job deliberately fails if
   [`gh release verify`][verify-release] or [`gh release verify-asset`][verify-asset]
   cannot verify the released tag and downloaded asset bytes.
4. Set repository variable `PYPI_PUBLISH_ENABLED` to exactly `true` only after publisher
   registration and release prerequisites are verified. Without it, tag builds run but
   publication jobs are skipped. A green build alone does not mean anything was published.

All actions are pinned to full commit SHAs. Build jobs have only `contents: read`; the PyPI
job uses the environment selected by the validated release plan with `id-token: write`.
There is no user-supplied environment input. The separate GitHub release
job has the contents, attestation and OIDC permissions it needs, and runs only after PyPI
succeeds. Failed, cancelled or skipped prerequisites cannot publish a GitHub release.
Both jobs consume the exact uploaded distributions; neither rebuilds them.

PyPI Trusted Publishing emits its publish attestations. The GitHub job creates build
provenance using `actions/attest`. Consumers must expect the new workflow identity
`https://github.com/mmkolpakov/robotics-runtime/.github/workflows/release.yml@refs/tags/<tag>`;
infra's old identity constraints need their separately planned migration. Old package
publishers and repositories are not removed or archived by this workflow.

Publishing does not use `skip-existing`, overwrite assets, or move tags. If PyPI succeeds
and the GitHub job fails, inspect the failed job and retained artifacts and rerun only that
failed job after resolving the cause. A full rerun can fail on PyPI's existing files; do not
hide that conflict or substitute rebuilt bytes. Retained workflow evidence expires after
seven days; maintainers must preserve it when investigating a partial publication.

[publisher]: https://docs.pypi.org/trusted-publishers/adding-a-publisher/
[pending]: https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/
[verify-release]: https://cli.github.com/manual/gh_release_verify
[verify-asset]: https://cli.github.com/manual/gh_release_verify-asset
