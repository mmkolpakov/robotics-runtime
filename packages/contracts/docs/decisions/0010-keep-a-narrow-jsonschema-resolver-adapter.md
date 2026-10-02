# Keep a Narrow jsonschema Resolver Adapter

- Status: accepted
- Date: 2026-10-02
- Decision: T08

## Context and Problem Statement

Caller-supplied extension schemas must be offline, digest-pinned and valid at
each reference target used during validation. jsonschema 4.26 has no public
per-lookup hook for this check; replacing its validator or traversing every
possible schema interpretation would widen the maintenance boundary.

## Decision Outcome

Keep private `_resolver` injection confined to
[`extensions.py`](../../src/robotics_runtime_contracts/extensions.py).
`referencing` owns lookup, scope and dynamic-reference behavior. The adapter
checks each encountered target's metaschema and remains attached across
validator evolution. This per-lookup adapter adds no eager walk of local-reference targets.

The root [lockfile](../../../../uv.lock) resolves jsonschema **4.26.0** and
referencing **0.37.0**. Library requirements remain `jsonschema>=4.26,<5`
with `format-nongpl`, and `referencing>=0.37,<1`. Dependency upgrades must review
this private integration and run the extension regressions covering offline
references, malformed targets, scopes, cycles, boolean schemas and dialect changes.

## Consequences

The adapter has a deliberate upstream compatibility risk; a locked development
run does not prove every version permitted by library metadata. Keep the seam
small and add regressions for changed upstream behavior. Prefer a public hook
when one can preserve these semantics. The adapter is not a general schema
sandbox, execution deadline or proof of universal JSON Schema compatibility.
