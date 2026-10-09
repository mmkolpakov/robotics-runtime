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

## Provider Compatibility

The stable interface contains observed capabilities and implementation
bindings, not a closed simulator, middleware, storage, or accelerator list.
Provider qualification belongs to runtime infrastructure. A new provider is
compatible when it emits the existing canonical documents and passes the same
conformance suite.

The historical accepted B2 stock profile belongs to
[R9 `v0.9.0-rc.1`](https://github.com/mmkolpakov/robotics-runtime-infra/releases/tag/v0.9.0-rc.1)
and contracts 0.18.1 / harness 0.19.0. It covers one ROS domain, UInt64 and one
finalized MCAP recording.
[R10 `v0.10.0-rc.1`](https://github.com/mmkolpakov/robotics-runtime-infra/releases/tag/v0.10.0-rc.1)
uses 0.18.2/0.19.1 and has verified release identities; its
[released B3 run](https://github.com/mmkolpakov/robotics-runtime-infra/actions/runs/37157837270)
passed entity checks, then failed with a 107 ms exact-step overshoot and a
JointState timeout. B3 remains unaccepted. The infrastructure
[compatibility policy](https://github.com/mmkolpakov/robotics-runtime-infra/blob/main/docs/compatibility.md)
distinguishes caller, tooling and image-source commits. Historical
`v0.8.0-rc.1` remains bound to 0.15.4/0.17.1. Source fixtures, archive checks
and live observer tests do not establish arbitrary consumer or hardware
qualification.

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
