# Validate Domain Extensions Offline

- Status: accepted
- Date: 2026-07-26

## Context and Problem Statement

Consumers need local fields while common contracts must remain neutral and
validation must remain reproducible in CI and restricted environments.

## Decision Drivers

- No network access during validation
- Consumer ownership of experimental fields
- Content integrity
- Namespace isolation

## Considered Options

- Add every consumer field to the common schema
- Resolve extension schemas over the network
- Accept caller-supplied, digest-pinned extension schemas

## Decision Outcome

The caller supplies extension-schema bytes. A declaration binds namespace,
canonical URI, and SHA-256 digest. External schema references are rejected;
local fragment references remain available.

This applies to every public catalog role. Qualification bundle declarations
and payloads live in the predicate; other roles keep them at the document root.
Existing roles that accepted unpinned v1 extensions retain that behavior while
the new `extension_schemas` field is absent. Its presence opts into strict
verification. The README lists these seven compatibility cases explicitly.
Internal schema resources do not independently enforce public-role semantics.

### Consequences

- Validation is deterministic and network-free.
- Consumers can develop extensions without changing the common catalog.
- Extension owners distribute and version their own schemas.
- Promotion into the common catalog requires a new common schema version.
