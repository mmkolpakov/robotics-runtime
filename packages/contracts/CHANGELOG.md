# Changelog

## 0.21.0

- Add opt-in acceptance-scenario.v2, runtime-manifest.v2,
  acceptance-observation.v2 and acceptance-result.v2 for captured native software
  and simulation observations. Preserve v1 canonical defaults, schema bytes and
  historical signed-document semantics.
- Separate pre-run configuration, original execution and assessment method,
  environment, UTC provenance, calibration selection and genuine source coverage.
  Preserve measured zero, non-applicability, unavailable and invalid facts.
- Add qualification-bundle.v2 with the retained in-toto Statement v1 wrapper and
  a distinct product predicate. Bind the immutable original outcome and new
  result, compare covered assertions under explicit exact_assertion_outcome,
  and keep changed/unknown context distinct from a matched comparison. Refuse
  physical v2 qualification. Keep default v1 statement creation and matching unchanged.
- Validate digest-pinned extensions for both bundle versions inside the
  predicate. Reuse the offline schema registry, generated source workflow and
  existing exact-byte loader.
- Use protobuf Timestamp for exact v2 UTC precision checks; reject more than
  nanosecond precision without changing v1 time semantics.


## 0.20.0

- Add the `transient_local` named topic QoS profile to scenario and dataset
  declarations. Existing schema versions and the four previous named profiles
  remain supported; the addition changes no readiness/metric limits.

## 0.19.0

The current dataset contract moves to `dataset-manifest.v2`. This is a breaking
pre-1.0 change: current readers and writers use one bag model for one or more
finalized MCAP members and reject v1 dataset documents. Previously published
packages and their v1 schema identities remain unchanged.

- Bind the retained native `metadata.yaml`, ordered MCAP members and each typed
  recording summary through exact artifact digests and byte sizes. Reject missing,
  extra, duplicate or unsafe member references.
- Validate aggregate message and channel counts and the full bag interval against
  per-member summaries and native metadata. Preserve recording size and duration
  limits for each segment.
- Bind capture run, timestamp basis, governance, native type hashes and declared
  custom QoS metadata to the retained source evidence. Require registered,
  digest-pinned extensions for the v2 dataset role.
- Retain native metadata bytes during qualification loading and recheck their
  digest before validation. File-backed qualification verifies the complete set
  of recordings selected for playback.
- Record the dataset-only schema transition explicitly in the published-schema
  compatibility gate; keep all other document roles under the existing checks.

## 0.18.3

- Document the frozen semantic compatibility corpus and its source-bound release
  snapshot assets. Keep the published package API and schema behavior unchanged.
- Clarify supported schema-extension, package-consumer and source-identity
  boundaries in package documentation.

## 0.18.2

- Add an optional per-file raw-evidence byte limit to MCAP summary APIs and the
  CLI. Reject invalid limits before reading evidence; omission preserves existing
  behavior and record/chunk bounds.
- Clarify that robot-description source artifacts may be authored URDF/SDF,
  while filesystem and XML admission remain the consumer's responsibility.

## 0.18.1

- Reject CLI and writer outputs that alias an input, including hard links,
  extension schemas and evidence drafts. Preserve regular file permissions
  and atomic replacement when writing through symlinks.
- Bound MCAP records and decoded chunks to 256 MiB. Validate actual decoded
  sizes through the codecs' streaming APIs before whole-chunk decoding.
- Bound hexadecimal and octal YAML integers during loading. Require canonical
  qualification subject names and the scenario role during overlay resolution.
- Reject lifecycle stability windows longer than graph readiness timeouts.
- Replay published qualification documents and consumer examples in the semantic
  compatibility gate. Update workspace release and supply-chain documentation.

## 0.18.0

Adds optional robot-description bindings, a flight-controller provider profile
and digest-pinned extensions for every document role. Schema changes are
additive against 0.17.0 under the compatibility gate. Fixes that reject inputs
0.17 accepted by mistake are listed with the other changes.

- Bind optional scenario robot-description digests to runtime workload metadata
  and the exact retained description artifact bytes during qualification. Keep
  existing workload documents and qualification artifact kinds compatible.
- `create_execution_permit` rejects a naive `now` with `input.invalid_timestamp`
  instead of reading it as host local time, which shifted `issued_at` and
  `expires_at` by the host UTC offset.
- `validate_document` and `robotics-contracts validate` reject internal schema
  resources such as `common.v1` or `*-core.v1` with `schema.unknown`. A
  document declaring `schema_version: common.v1` previously passed without any
  root constraint, and core schemas skipped role semantics and extensions.
- Add a flight-controller interface profile and qualification examples using the
  existing extensible provider identifiers, with six required capabilities and
  checks that reject missing capabilities or a mismatched provider kind.
- Support digest-pinned, offline extensions in every public role, including
  qualification predicates. Preserve legacy unpinned payloads where v1 already
  allowed them. Carry supplied schemas through qualification loading, receipt
  writers and recording-summary references; retain exact artifact byte hashes.

## 0.17.0

The first release from the shared `robotics-runtime` workspace. Its distribution
contains the contracts package independently of workspace sources. Existing 0.16
roles retain compatible assertions; the 0.15 generation still requires migration.

- Add validated runtime-manifest and evidence-index writers, recording summaries
  with optional MCAP decoding, and an in-toto qualification statement builder.
  Artifact digests continue to identify exact retained bytes. Producer outputs
  cannot replace their artifact or extension-schema inputs.
- Add an artifact-receipt writer that binds source bytes to an externally
  produced verification and its complete provenance dependency set. It preserves
  raw-byte verification digests and does not perform signature verification.
- Match decoded qualification statements to validated local artifact sets with
  `validate-qualification --statement`. Keep original signed bytes unchanged;
  object formatting is immaterial and mismatches have a typed diagnostic.
- Add execution trust policy and robot description roles, with byte-bound
  consumer examples. Trust-policy principals are unique by role and identity.
- Expose public qualification inspection with typed accumulated diagnostics and
  explicit blocked checks. Invalid cross-document execution modes cannot enter
  incompatible authorization checks. File metadata comes from one streamed read.
- Compare actual released Git schemas and semantic witnesses in CI, allowing only
  supported additive changes. Unsupported structures fail closed for review;
  the bounded gate does not claim a general proof of semantic equivalence.

- Check canonical object-key size before constructing diagnostic paths. Bound
  path escaping by the document byte budget and retain the enclosing path when
  needed, without rejecting otherwise valid keys or changing serialized bytes.
- Add `dumps_canonical` using the project's deterministic JSON profile, explicitly
  not RFC 8785/JCS: retain exact integer number tokens, including nanoseconds beyond
  2**53, and native finite float spelling. Apply the input depth/node/byte bounds
  and report invalid types/Unicode with `ContractError` paths. Add `file_sha256`
  for chunked hashing of original bytes; existing artifact hashes remain unchanged.
- Restore reproducible core schema sources and an offline generation gate. Replace
  positional conditional references with named definitions and centralize primitive
  constraints in `common.v1`, preserving resolved assertions and fixture outcomes.
  Intentionally update schema digest snapshots; see the baseline reproduction and
  equivalence evidence in [schema bundling](docs/schema-bundling.md).
- Accept `incomplete` campaign summaries when passed runs are below the minimum
  and no failed/error runs exist. Preserve legacy all-passed-shortfall `failed`
  documents under `campaign-summary.v1`; schema bytes and policy limits do not
  change. New harness writers require this reader update before emitting the
  more precise verdict. See [compatibility policy](COMPATIBILITY.md).
- Replace `json-merge-patch` with a typed RFC 7396 implementation. Semantic diff
  distinguishes booleans, integers and floats recursively, preserves input
  containers, and reports `diff.unrepresentable` for unrepresentable null members.
- Load YAML with 1.2 core scalar rules and matching output quoting; reject
  duplicate JSON/YAML keys, aliases, non-JSON values and oversized/deep input.
  JSON files and extension schemas no longer fall back to YAML parsing.
- Unify expected failures under `ContractError`; report relevant schema errors,
  argument exit code 2 and `internal.error` for unexpected CLI failures. Expand
  home paths consistently, resolve schema references offline, retain extracted
  schema paths until process exit, and share timestamp comparison parsing.
- Reject foreign qualification domains and hop channels with explicit error IDs
  and JSON paths, including failed, incomplete and error chains.
- Add the CPython 3.12-3.14 CI matrix and declare `>=3.12,<3.15` support.
- Allow `referencing>=0.37,<1` while retaining the locked resolution; enable
  Renovate hook updates and group duplicate tool pins. Hosted bot onboarding
  and the first dependency PR remain an external acceptance gate.
- Lock the published 0.16 schema resources and catalog with a byte-digest and
  resource-inventory tripwire, alongside the release compatibility gate.
- Document the breaking 0.15 to 0.16 migration and known consumer versions.
- Replace the pre-1.0 schema-name reuse policy with the compatibility rules in
  [ADR 0007](docs/decisions/0007-preserve-published-schema-compatibility.md).

## 0.16.0 - 2026-08-17

This release replaces the 0.15 contract generation. It is **not** a drop-in
upgrade for 0.15 producers or retained evidence, even where `schema_version`
still ends in `.v1`. See the
[0.15 to 0.16 migration guide](docs/migrations/0.15-to-0.16.md) before upgrading.

- Introduce a role catalog with one public schema per role and internal core
  resources; remove the former multi-generation compatibility API.
- Replace scenario, runtime, result, evidence and qualification shapes with
  the catalogued `v1` forms, including provider and evaluator declarations.
- Add artifact receipts and verification, acceptance observations, qualification
  profiles, provider conformance and shared validation/status helpers.
- Generalize MCAP summaries and Zenoh channels to recording summaries and
  transport channels; replace the qualification predicate and artifact kinds.
- Rename physical authorization image-digest fields and the permit CLI flag to
  execution-subject digest terminology.

This changelog starts with the 0.16 transition. Earlier patch history remains
in the tagged Git history; this is not a reconstructed list of every 0.15 change.
