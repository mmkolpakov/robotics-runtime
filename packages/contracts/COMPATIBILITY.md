# Compatibility Policy

This policy covers the Python distribution and its JSON Schema contracts.

## Package Cohort

This release pairs contracts 0.21.1 with harness 0.22.0. Harness metadata requires
`robotics-runtime-contracts>=0.21,<0.22`; release checks select the exact
`contracts-v0.21.1` prerequisite. See [package release notes](CHANGELOG.md) and
[harness compatibility](../harness/docs/compatibility.md).

Package/API support does not qualify an infrastructure image or native profile.
[Preserved run and release records](../../docs/run-history.md) retain historical
versions, source identities and actual outcomes; this release does not rewrite
those records. Consumers must bind their exact installed distributions and
profile evidence when adopting this cohort.

## Current Catalog

The role-to-schema mapping is maintained in
[`catalog.v1.json`](src/robotics_runtime_contracts/schemas/catalog.v1.json).
Canonical defaults are retained; `supported_versions` in that same catalog
adds opt-in v2 scenario, runtime, observation, result and qualification schemas.
`schema_versions_for_role()` lists those supported versions, while
`schema_for_role(role, version=2)` selects an explicit version.

Superseded experimental readers and writers are removed rather than carried as
parallel APIs. Historical releases remain reproducible from immutable Git tags
and release artifacts, but the current package does not promise to read their
documents.

## Package Versions

The Python distribution follows Semantic Versioning:

- patch: implementation or documentation changes that preserve the active
  contract set;
- minor before `1.0`: a new public capability or a documented breaking API
  change; a breaking schema change also requires a new schema major;
- major after `1.0`: a breaking public API or contract change.

Every pre-1.0 breaking change requires release notes and migration notes for
known consumers. Package versioning does not permit incompatible reuse of a
published schema identifier; [ADR 0007](docs/decisions/0007-preserve-published-schema-compatibility.md)
supersedes the former pre-1.0 replacement policy.

## Readers And Writers

- Documents declare `schema_version`; historical 0.15/0.16 evidence also needs
  its producer's exact package version because some identifiers were reused.
- Readers resolve document roles through the catalog and never guess a version.
- Writers emit a declared supported schema for the role; canonical defaults remain unchanged.
- Validation never mutates input and never retrieves a schema from the network.
- Migrations are introduced only for a real consumer and remain separate from
  validation.
- There is no implicit downgrade path.

For `campaign-summary.v1`, a shortage of passed runs with no failed or error runs
may be reported as `incomplete`. The reader also accepts the legacy `failed`
verdict for an all-passed shortage, as emitted by the 0.16.0 generation. Retained
documents remain valid without rewriting their bytes or digest links. New harness
writers emit `incomplete` for that shortage; they require a reader with this
additive semantic relaxation. A `passed` verdict still requires every campaign
acceptance threshold to be met. Existing failure/error precedence and tolerated
run limits are unchanged, including when the passed-run minimum is not met.
The schema identifier, schema bytes and catalog are unchanged.

## Schema Identity

Dataset and native v2 IDs use `urn:robotics-runtime-contracts:v2:*`.
Retained v1 roles keep `urn:robotics-runtime-contracts:v1:*` and their original
schema bytes and semantics.
Public role schemas and internal reusable resources have disjoint IDs. Schema
digests are derived from packaged bytes with `schema_digest()`.

[`docs/schema-digests.json`](docs/schema-digests.json) records SHA-256 for all
schema resources and the catalog. The test compares
raw packaged bytes and the complete file inventory with this checked-in
snapshot. Whitespace changes, modified internal cores, missing files and new
files all require review; JSON is not normalized before hashing.

The snapshot also ships in the source distribution so its bundled tests can
run. Tests never regenerate expected digests. With the structural gate,
an intentional snapshot update must accompany a changelog entry and a passing
compatibility comparison, or a new schema major and migration notes for a
breaking change. Updating hashes merely to make a failure disappear is not a
compatibility review.

Tagged release artifacts and their attestations are immutable. Under a published
name only additive changes are permitted. Breaking changes require a new schema
major, a catalog role and migration notes. The workspace's
[published compatibility gate](docs/schema-compatibility.md) compares actual
released Git sources with the candidate using bounded D10 structural rules and
public API semantic regressions. Unsupported cases require explicit review;
neither this finite check nor a digest comparison proves universal compatibility.

This workspace validates package fixtures and consumer examples against the
current checkout. Clean release installs separately check wheel and sdist
contents outside the workspace. Neither gate establishes that an arbitrary
consumer or published infra image supports the pair; consumers must retain
their integration evidence when adopting a release.

## Neutrality

Common contracts do not select a robot or product. V1 retains its ROS 2/SROS2
constraints. Native v2 profiles declare the actual type support or codec, backend,
wire envelope, executor/clock bindings and recorder transformations in use.
Descriptors and native models are ArtifactRef bindings where they exist; IDL
and URDF are not universal requirements. Observations belong to the selected
profile and distinguish measured, not_applicable, unobserved and invalid states.
V2 physical qualification remains unsupported. Concrete provider identities and
capabilities are observed data. All public roles support digest-pinned, reverse-domain extension
schemas. Six existing v1 roles retain unpinned legacy extensions only when
`extension_schemas` is absent; the [README](README.md#extensions) lists that boundary.

Moving an extension into the common contract requires reusable semantics,
positive and negative fixtures, and an architecture decision.

## Change Review

Every contract change states:

- the affected document roles and producers;
- positive, negative, and cross-repository tests;
- evidence and physical-safety impact;
- the package-version impact;
- the migration plan for any known consumer.
