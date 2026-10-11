# Compatibility

## Package Line

The `0.22.x` harness line requires Python `>=3.12,<3.15` and
`robotics-runtime-contracts>=0.21,<0.22`. This release selects contracts 0.21.0
and harness 0.22.0, with exact prerequisite `contracts-v0.21.0`.
Package metadata, tagged source and distribution digests identify the installed
pair; package support and native-profile qualification remain separate.

Each role retains its canonical default. Datasets use v2 for one or multiple
MCAP members. Explicit v2 scenario/runtime/observation/result/qualification roles
support the [native archive example](../../contracts/consumer-examples/minimal-native-archive/README.md)
and [distinct archive assessments](archive-assessment.md). Historical datasets
require their matching archived package; readers do not convert old forms.

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

The caller's pinned extension registry is forwarded to every loaded bundle
document, including scenario, runtime, model, dataset, permit and verification.
Unknown namespaces, wrong schema digests and invalid payloads fail validation.

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
Nanosecond document integers are exact on the Python file path. JavaScript
bridges must preserve exact files/text, and pass CLI window arguments as decimal
strings or bigint. JSON.parse/re-emission through JavaScript Number is outside
that exact-byte path. The host rejects numeric window arguments; read-only MCP
operations forward file snapshots and keep worker payloads as text.
The built-in OTLP method accepts unix_ns; selected product assessments may use
native_ns without an inferred UTC conversion. Empty criteria or entirely absent
measurement coverage cannot produce a passed verdict. Acceptance-run.v1 and
acceptance-aggregate.v1 retain their existing document semantics; separate
assessment cohorts use separate aggregates. Explicit assessment controls
and qualification-bundle.v2 add the [archive assessment path](archive-assessment.md),
retaining the original result separately from each new assessment. Canonical
qualification-bundle.v1 defaults and historical signed readers are unchanged.

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
