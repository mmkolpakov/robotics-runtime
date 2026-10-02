# Preserve Deterministic JSON and Exact Byte Bindings

- Status: accepted
- Date: 2026-10-02
- Decision: T02

## Context and Problem Statement

Contract nanoseconds use integer JSON tokens, including values beyond 2**53.
Receipts, evidence indexes and qualification subjects bind original artifact
bytes. Adopting RFC 8785/JCS would change the numeric domain and serialized
bytes of existing producers.

## Decision Outcome

Retain the current `dumps_canonical` project profile: exact integers, finite
native Python float spelling, compact UTF-8 and recursive Unicode code-point
key ordering. It is deterministic JSON, not JCS. Keep integer nanoseconds and
the public schemas unchanged.

Hash existing artifacts from their original bytes with `file_sha256`; never
parse and reserialize them to verify a receipt or signature. New producer files
are hashed only after their bytes are written. The
[README profile](../../README.md#deterministic-json-and-artifact-hashes) and
[canonical regressions](../../tests/test_canonical.py) define the supported values,
limits and byte spellings.

## Consequences

Consumers must use the same profile when reproducing producer output. A future
JCS interface would need a separate versioned boundary and migration; it cannot
replace existing bytes or convert nanoseconds to strings implicitly. This
decision does not provide signature verification or authenticate producer facts.
