# Supply-Chain Assurance

Harness releases are built by the `mmkolpakov/robotics-runtime` workspace.
The [workspace release procedure](../../../docs/releasing.md) is authoritative
for release ordering, `harness-vX.Y.Z` tags, publisher registration and protected
publication environments. GitHub release creation requires successful PyPI
publication; a local build or dry run does not establish a published release.

## Release Artifact Assessment

Maintainers assess a published wheel or source distribution against
[SLSA 1.2 Build L2](https://slsa.dev/spec/v1.2/) only when its completed release
run and verified provenance establish the following evidence. This is an
artifact-specific maintainer assessment, not an independent certification.
Unreleased candidates and local development builds have no Build L2 claim.

| SLSA 1.2 requirement | Evidence required for the released archive |
| --- | --- |
| Consistent build process | The tagged `.github/workflows/release.yml` run builds with `uv build --no-sources` |
| Hosted build platform | The release build runs on a GitHub-hosted Ubuntu runner |
| Authentic provenance | GitHub's `actions/attest` attestation binds the archive digest to the workspace release workflow |
| Provenance distribution | The released archive's attestation is discoverable and verifies against `mmkolpakov/robotics-runtime` |

Build L2 permits best-effort resolved dependency completeness. The lockfile pins
the development graph; the wheel carries standard version constraints. The
contracts source override is disabled by `uv build --no-sources`.

The release workflow builds and tests the distributions once, then publication
jobs consume those exact files. The canonical release procedure describes the
Trusted Publishing and GitHub provenance gates; neither rebuilds the archives.

## Release Verification

Download a published wheel or source archive and verify its attestation before
installation. For harness `0.19.0`, after publication:

```bash
gh attestation verify \
  --repo mmkolpakov/robotics-runtime \
  robotics_acceptance_harness-0.19.0-py3-none-any.whl
```

The repository does not claim SLSA Source-track conformance or Build L3.
Reaching Build L3 requires a separately reviewed reusable build workflow and a
published assessment of the builder controls.
