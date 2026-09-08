# Changelog

## Unreleased

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
  resource-inventory tripwire; structural compatibility checking remains planned.
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
