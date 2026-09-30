# Supply-Chain Assurance

This document records the actual build assurance of each released component
against the [SLSA v1.2 Build Track](https://slsa.dev/spec/v1.2/).

GitHub documents artifact attestations from hosted workflows in SLSA v1.0
terms. The project assessment below maps the same controls to the current v1.2
requirements. It is a maintainer assessment, not an independent certification.

## Component Table

| Component | Source and builder | Provenance | Actual level |
| --- | --- | --- | --- |
| Python wheel (`.whl`) | `contracts-vX.Y.Z` tag of `mmkolpakov/robotics-runtime` whose commit is reachable from `origin/main`; root `.github/workflows/release.yml`; GitHub-hosted Ubuntu 24.04; `uv build --package robotics-runtime-contracts --no-sources` | PyPI Trusted Publishing attestations and `actions/attest` build provenance bound to the artifact digest | Build L2 |
| Source distribution (`.tar.gz`) | same tag, workflow and build command | same | Build L2 |

The workspace release workflow builds one package per tag. Both distributions
are built and checked once in a job without OIDC authority. The resulting
workflow artifact is consumed unchanged by the publication jobs:

- `publish-pypi` publishes to PyPI through Trusted Publishing when the
  repository variable `PYPI_PUBLISH_ENABLED` is `true`, using the protected
  environment `pypi`;
- `github-release` runs only after a successful `publish-pypi`, attests the
  distributions, creates the GitHub Release without overwriting existing
  assets and verifies the immutable release assets.

Both publication jobs have `id-token: write`: `publish-pypi` uses it for Trusted
Publishing, and `github-release` uses it for attestations (with
`attestations: write` and `contents: write`). Neither job checks out the
repository or executes project code. No PyPI API token is used or stored.
The hosted builder and authentic provenance meet the L2 shape. Build L3 is not
claimed because the project does not use and verify an isolated reusable build
workflow as its trusted builder boundary.

The repository does not claim a SLSA Source Track level.

## Consumer Verification

Download an artifact from the GitHub Release, then verify its attestation:

```bash
gh attestation verify \
  robotics_runtime_contracts-<version>-py3-none-any.whl \
  --repo mmkolpakov/robotics-runtime \
  --signer-workflow mmkolpakov/robotics-runtime/.github/workflows/release.yml
```

The same command applies to the source distribution. Releases up to 0.16 were
built by the former `mmkolpakov/robotics-runtime-contracts` repository and carry
that repository's workflow identity.

Verification establishes artifact identity and build provenance. It does not
qualify a robotics runtime, dataset, model, or physical target.

## Release Controls

- Dependencies are resolved from the committed `uv.lock`.
- Actions are pinned by immutable commit SHA.
- Pull requests and `main` run the package tests on CPython 3.12, 3.13 and
  3.14, the compatibility gate against the last release and the workspace
  consumer checks. The release job itself runs only the release-guard tests.
- The release job builds the wheel and source distribution without workspace
  sources and installs each into a clean CPython 3.12 environment.
- The tag must equal `contracts-v` followed by the package version (`-rc.N`
  for release candidates), resolve to the checked-out commit and be reachable
  from `origin/main`.
- The repository tag ruleset "Immutable package release tags" protects release
  tags from being moved or deleted.

Any change to the builder boundary, attestation action, release trigger, or
artifact set requires updating this table.

## Trusted Publisher

PyPI project `robotics-runtime-contracts` trusts owner `mmkolpakov`, repository
`robotics-runtime`, workflow `release.yml` and environment `pypi`; version
0.17.0 was published through it. Once enabled, a PyPI publication failure fails
the release workflow and no GitHub Release is created.

Release `robotics-runtime-contracts` before releasing a version of
`robotics-acceptance-harness` that depends on it (see
[`docs/releasing.md`](../../docs/releasing.md)).
