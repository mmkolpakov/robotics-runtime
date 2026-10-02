# Compatibility Policy

This policy covers the Python distribution and its JSON Schema contracts.

## Known Consumers

The published package pair and infrastructure evidence have distinct scopes:

| Consumer | Contracts pin | Scope of evidence |
| --- | --- | --- |
| [Acceptance harness 0.19.0](https://pypi.org/project/robotics-acceptance-harness/0.19.0/) | `>=0.18,<0.19`; release checks pin 0.18.1 | Independent PyPI installs, public API/CLI checks and verified archive identities |
| Current infra source foundation | contracts 0.18.1 / harness 0.19.0 | Integration of pinned sources; no current OCI release qualification |
| [Infra OCI v0.8.0-rc.1](https://github.com/mmkolpakov/robotics-runtime-infra/releases/tag/v0.8.0-rc.1) | contracts 0.15.4 / harness 0.17.1 | Historical release only; it does not establish support for the current pair |

Library requirements permit a minor line; execution and release evidence must
identify the exact installed pair. The 0.15 and 0.16 generations are incompatible. See the
[migration guide](docs/migrations/0.15-to-0.16.md) and [changelog](CHANGELOG.md).

## Current Catalog

Release 0.18.1 maps each document role to exactly one schema in
[`catalog.v1.json`](src/robotics_runtime_contracts/schemas/catalog.v1.json).

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
- Writers emit only the catalogued schema for a role.
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

The canonical IDs use the `urn:robotics-runtime-contracts:v1:*` namespace.
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

Common contracts do not select a robot or product. They model ROS 2/SROS2 and
runtime-specific constraints; concrete provider identities and capabilities are
observed data. All public roles support digest-pinned, reverse-domain extension
schemas. Seven existing roles retain unpinned legacy extensions only when
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
