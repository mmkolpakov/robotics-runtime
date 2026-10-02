# Compatibility

## Package Line

The `0.19.x` harness line requires Python `>=3.12,<3.15` and
`robotics-runtime-contracts>=0.18,<0.19`. Harness `0.19.0` is prepared against
the exact `contracts-v0.18.1` release; its publication requires that contracts
version to be available on PyPI and GitHub.

The repository is pre-1.0. Each public document family has one canonical `v1`;
superseded experimental v2-v5 schemas and compatibility branches are intentionally
absent. The first stable release
will establish the long-term compatibility baseline.

## Document Set

The authoritative role-to-schema mapping is the contracts package catalog. The
harness calls its public `schema_for_role()` and `validate_role()` APIs and does
not maintain a second compatibility table.

Unknown schema versions, wrong document roles, and contradictory bundle facts
fail before observation or evaluation begins. Scenario extensions remain
separately versioned and digest-pinned by their canonical URI.

## Provider Compatibility

The stable interface contains observed capabilities and implementation
bindings, not a closed simulator, middleware, storage, or accelerator list.
Provider qualification belongs to runtime infrastructure. A new provider is
compatible when it emits the existing canonical documents and passes the same
conformance suite.

The Python-only commands work without ROS. Live observation requires the ROS 2
packages and message interfaces declared by the runtime. Exact provider and
hardware support is stated by the qualified runtime artifact, not inferred from
installing this package.

## Dependency Reproducibility

`uv.lock` pins the workspace's development dependency graph. The contracts
workspace source override applies only to development. Releases use
`uv build --no-sources` and standard index requirements, then test wheel and
source distributions outside the workspace with the exact released contracts
version from PyPI. See the [workspace release procedure](../../../docs/releasing.md)
for the source, metadata and provenance checks.
