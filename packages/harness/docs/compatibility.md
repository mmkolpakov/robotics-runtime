# Compatibility

## Package Line

The `0.21.x` harness line requires Python `>=3.12,<3.15` and
`robotics-runtime-contracts>=0.20,<0.21`.
[Harness 0.21.0](https://pypi.org/project/robotics-acceptance-harness/0.21.0/) and
[contracts 0.20.0](https://pypi.org/project/robotics-runtime-contracts/0.20.0/)
are published under `harness-v0.21.0` and `contracts-v0.20.0`.
Independent installs outside the workspace checked the exact pair, public API,
CLI and archive contents against their tagged sources.

Each role has one canonical schema. Datasets use v2 for one or multiple
MCAP members; other current roles use v1. Historical datasets require the
matching archived package. Current readers do not convert old dataset forms.

## Document Set

The authoritative role-to-schema mapping is the contracts package catalog. The
harness calls its public `schema_for_role()` and `validate_role()` APIs and does
not maintain a second compatibility table.

Unknown schema versions, wrong document roles, and contradictory bundle facts
fail before observation or evaluation begins. Scenario extensions remain
separately versioned and digest-pinned by their canonical URI.

The 0.21.0 wheel forwards the caller's extension registry to the scenario only
when loading a bundle. Extension-bearing runtime, model, dataset, permit or
verification documents do not receive it on that path. Current development
source fixes the forwarding; that fix is not a published 0.21.0 capability.
The [first-result path](../../../docs/first-result.md) uses no custom extensions.

## Provider Compatibility

The stable interface contains observed capabilities and implementation
bindings, not a closed simulator, middleware, storage, or accelerator list.
Provider qualification belongs to runtime infrastructure. A new provider is
compatible when it emits the existing canonical documents and passes the same
conformance suite.

[Preserved run and release records](../../../docs/run-history.md) hold the
original package versions, source identities and native profile outcomes.
A current package install or source fixture does not qualify those compositions.

The Python-only commands work without ROS. Live observation requires the ROS 2
packages and message interfaces declared by the runtime. Exact provider and
hardware support is stated by the qualified runtime artifact, not inferred from
installing this package.

## Dependency Reproducibility

The root [uv.lock](../../../uv.lock) pins the workspace's development dependency graph. The contracts
workspace source override applies only to development. Releases use
`uv build --package robotics-acceptance-harness --no-sources` and standard index
requirements, then test wheel and
source distributions outside the workspace with the exact released contracts
version from PyPI. See the [workspace release procedure](../../../docs/releasing.md)
for the source, metadata and provenance checks.
