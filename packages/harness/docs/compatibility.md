# Compatibility

## Package Line

The `0.21.x` harness line requires Python `>=3.12,<3.15` and
`robotics-runtime-contracts>=0.20,<0.21`.
[Harness 0.21.0](https://pypi.org/project/robotics-acceptance-harness/0.21.0/) and
[contracts 0.20.0](https://pypi.org/project/robotics-runtime-contracts/0.20.0/)
are published under `harness-v0.21.0` and `contracts-v0.20.0`.
Independent installs outside the workspace checked the exact pair, public API,
CLI and archive contents against their tagged sources.

Each role retains its canonical default. Datasets use v2 for one or multiple
MCAP members. The native document path adds explicitly supported v2 versions for
scenario, runtime, observation and result roles. The published 0.20.0/0.21.0
pair predates that native path; use a package build containing those roles for
the [native archive example](../../contracts/consumer-examples/minimal-native-archive/README.md).
Historical datasets require their matching archived package. Readers do not
convert old dataset forms.

## Document Set

The authoritative role-to-schema mapping is the contracts package catalog. The
harness calls its public `schema_for_role()`, `schema_versions_for_role()` and
`validate_role()` APIs and maintains no second compatibility table.
`schema_for_role(role)` preserves the canonical default;
`schema_for_role(role, version=2)` selects an explicit supported version.
Declared supported versions are validated without converting input bytes.

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

The Python commands install without ROS. V1 document formats retain required
ROS graph, lifecycle and timing fields; live observation uses the ROS 2 packages
and interfaces declared by the runtime. V2 evaluates captured native software
or simulation observations without constructing ROS fields. It does not launch
SDK operations. V2 physical qualification and v1 transport evaluation of v2
profiles are refused.

V2 results separate original run/source/evidence hashes from method configuration,
actual software environment and UTC assessment time. Captured source measurement
windows and assessment windows use explicit clock identities and integer bounds.
The built-in OTLP method accepts unix_ns; selected product assessments may use
native_ns without an inferred UTC conversion. Empty criteria or entirely absent
measurement coverage cannot produce a passed verdict. Existing v1 run, aggregate
and qualification wrappers cover one original run and its assessment chain; they
do not implement independent archive re-evaluation.

Exact provider and hardware support belongs to a qualified runtime artifact;
installing the package or selecting an SDK binding does not establish it.

## Dependency Reproducibility

The root [uv.lock](../../../uv.lock) pins the workspace's development dependency graph. The contracts
workspace source override applies only to development. Releases use
`uv build --package robotics-acceptance-harness --no-sources` and standard index
requirements, then test wheel and
source distributions outside the workspace with the exact released contracts
version from PyPI. See the [workspace release procedure](../../../docs/releasing.md)
for the source, metadata and provenance checks.
