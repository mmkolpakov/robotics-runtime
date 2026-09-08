# Changelog

## 0.17.0rc1 - Release candidate

The first candidate from the shared `robotics-runtime` workspace. Its distribution
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
