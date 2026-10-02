# Compatibility

## Package Line

The `0.19.x` harness line requires Python `>=3.12,<3.15` and
`robotics-runtime-contracts>=0.18,<0.19`.
[Harness 0.19.0](https://pypi.org/project/robotics-acceptance-harness/0.19.0/) and
[contracts 0.18.1](https://pypi.org/project/robotics-runtime-contracts/0.18.1/)
are published from the root workspace under `harness-v0.19.0` and
`contracts-v0.18.1`. Independent installs outside the workspace checked the
exact pair, its public API/CLI and installed archive contents.

The packages are pre-1.0. Each public document family has one canonical `v1`;
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

The current infra foundation integrates pinned sources for this pair. The
older published OCI `v0.8.0-rc.1` belongs to contracts 0.15.4 / harness 0.17.1;
it does not qualify the current pair. Source fixtures, archive checks and live
observer tests do not establish arbitrary consumer or hardware qualification.

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
