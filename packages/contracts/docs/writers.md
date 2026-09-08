# Document writers

The public producer APIs are in `robotics_runtime_contracts.writers` and
`robotics_runtime_contracts.recordings`. They return validated dictionaries;
`write_document` validates again and atomically replaces the output. Commands
write compact UTF-8 using SPEC19's **project deterministic JSON profile, not
RFC 8785/JCS**. Arrays preserve order. Artifact SHA-256 always hashes the original
file bytes, including whitespace; it is not a JSON content hash.

Writers operate on facts already collected by a producer. They do not discover
ROS/runtime configuration, invent policy observations, upload evidence, or imply
a passed acceptance verdict. The caller supplies all required template fields.
The writer validates structure and semantic consistency, not the truth of a
caller's declared observation or retained-storage claim.

## Runtime manifest

```sh
robotics-contracts runtime-manifest init --template observed-runtime.yaml --output runtime.json
```

The template supplies every `runtime-manifest.v1` field except the optional
`schema_version`, which the producer sets when absent. No clock offsets, platform
versions, security settings, provider bindings, identifiers or timestamps are
guessed. `create_runtime_manifest(template, extension_schemas=...)` is the Python
equivalent. Templates with extensions may supply repeatable
`--extension-schema URI=PATH` just like `validate`.

## Evidence index

Published `evidence-index.v1` requires `finalized: true` and at least one artifact.
Therefore init/add-artifact write **writer state**, an object with
`writer_state: evidence-index-draft.v1` and an `index` member. This is deliberately
not a public evidence index and consumers must not accept it as one. The internal
index is checked against the public schema with only finalized/cardinality
relaxed; policy observations, artifacts and semantic checks remain enforced.

```sh
robotics-contracts evidence-index init --template index-metadata.json --output draft.json
robotics-contracts evidence-index add-artifact draft.json --source metrics.jsonl --metadata artifact.json
robotics-contracts evidence-index finalize draft.json --output evidence-index.json
```

`index-metadata.json` contains the explicit `run_id`, `generated_at`,
`policy_observation` (including measured spool/upload figures), and optional
extensions; omit `artifacts` and `finalized`. The timestamp is caller-owned and
is never replaced with the current time. `artifact.json` supplies `artifact_id`,
`kind`, `media_type`, `retention_class`, `storage_state`, and optional segment
index. Local URI/path, byte size and SHA-256 are derived from `--source`; supplied
values must agree exactly. Retained artifacts additionally require the caller's
URI, immutable revision and receipt digest. No upload or receipt verification is
performed by this construction command; qualification validation handles links.

Recording artifacts additionally require `--recording-summary summary.json`.
The summary must validate and identify the recording's exact SHA-256. Its own
reference binds its original file bytes. Drafts retain absolute local paths;
all original sources and summaries must still be available during finalize.
Finalize rechecks bytes, rejects empty or contradictory indexes, and emits the
unmodified public schema. Add-artifact defaults to atomic replacement of the
draft; `--output` selects another path. Failed operations preserve previous
outputs, and commands reject outputs that would overwrite evidence inputs.

Python equivalents: `create_evidence_index`, `add_evidence_artifact`,
`write_evidence_draft`, and `finalize_evidence_index`. Inputs are copied.

## Artifact receipt

```sh
robotics-contracts artifact-receipt create \
  --template receipt-metadata.json --source recording.mcap \
  --verification artifact-verification.json \
  --dependency statement.json --dependency trust-policy.json \
  --dependency verification-evidence.json --output artifact-receipt.json
```

The template supplies `receipt_id`, `created_at` and the optional `run_id`.
The artifact descriptor, producer identity/implementation and statement digest
come from a validated `artifact-verification.v1`; any values supplied in the
template must agree. The receipt hashes the original verification file bytes,
checks the source file's SHA-256 and size against that descriptor, and requires
all provenance dependencies by their raw-byte digests. Include the content
manifest when the verification references one. Missing, duplicate and unreferenced
dependency bytes are rejected. The receipt must not predate verification.

The Python API is `create_artifact_receipt(template, source, verification,
dependencies)`. Like the other producers, it checks consistency of supplied
facts. It does not run a signature verifier or establish trust in an arbitrary
verification JSON. The caller must first verify provenance through its trusted
external verifier and preserve the verification evidence. S3 object metadata or
an upload checksum alone cannot supply that verification. CLI output cannot
overwrite the source, template, verification, or any dependency file.

## Recording summary

Install `robotics-runtime-contracts[mcap]` (MCAP Python 1.4 or later, below 2).
The development lock includes MCAP so these tests run in the normal CI matrix.

```sh
robotics-contracts recording-summary from-mcap recording.mcap --output summary.json
```

`recording_summary_from_mcap(path)` uses the upstream MCAP Python reader, with CRC
validation enabled, on a private file snapshot. It requires a finalized footer
and Statistics record, cross-checks counts/timestamps against actual records,
and reports observed chunk compression (`none` for no compression). No ROS
message decoding is needed. Empty recordings have measured zero counts.
Missing Statistics, truncated files, mismatched statistics, schemaless channels,
and channels that cannot fit `recording-summary.v1` are rejected. Temporary disk
space up to the source recording size is required.

Streamed data-section channel/schema definitions are authoritative. Definitions
must precede their uses, and repeated definitions must agree, including summary
copies. Optional summary copies and unavailable per-channel Statistics do not
prevent extraction: the producer counts the actual messages. Nonempty per-channel
Statistics are checked against those counts.

MCAP 1.4's public reader validates data-section and chunk CRCs. A separate narrow
check verifies nonzero attachment and footer-summary CRCs over original snapshot
bytes, in 64 KiB blocks. It reads record envelopes and checksum field locations;
MCAP decoding and decompression remain with the upstream library. A zero CRC
means unavailable. All producer commands protect supplied extension-schema files
from output replacement, including path aliases and in-place draft updates.

Upstream references: [MCAP Python 1.4.0](https://pypi.org/project/mcap/1.4.0/),
[reader API](https://mcap.dev/docs/python/mcap-apidoc/mcap.reader),
[stream reader API](https://mcap.dev/docs/python/mcap-apidoc/mcap.stream_reader).

The CLI producer regression in `tests/test_writers.py` generates a runtime and
evidence index from the existing minimal-simulation example, validates both, and
checks file-byte bindings. Those inputs are labelled fixtures, not live observations.

## Qualification statement

```sh
robotics-contracts qualification statement \
  --artifact scenario:scenario.json=scenario.json \
  --artifact acceptance_run:acceptance-run.json=run.json \
  --artifact runtime_manifest:runtime-manifests/primary.json=runtime.json \
  --artifact domain_result:results/primary.json=result.json \
  --artifact acceptance_aggregate:acceptance-aggregate.json=aggregate.json \
  --artifact evidence_index:evidence-indexes/primary.json=evidence-index.json \
  --artifact other_evidence:evidence/metrics.json=metrics.json \
  --output qualification-statement.json
```

This illustrates labels, not a complete artifact inventory. Supply **every**
artifact required by the run, including provider configuration/profile/conformance,
recording summaries, retained evidence and authorization when applicable. Domain
labels must equal the IDs in `acceptance-run.domains`, not generic filenames.
The existing complete qualification validation is mandatory before writing.
Inputs use the same `KIND:SUBJECT=PATH` syntax as `validate-qualification`.

The public API is `robotics_runtime_contracts.statements.create_qualification_statement`
or `write_qualification_statement(specifications, output, extension_schemas=...)`.
The result is an unsigned [in-toto Statement v1](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md):
`_type`, `subject`, `predicateType`, `predicate`. Each subject's SHA-256 comes
directly from the bytes consumed by qualification validation. The writer does
not reserialize or reread subjects to construct their digests. The run ID and
timestamp come from the validated run and aggregate respectively; subject/kind
lists sort by subject name.
Reordering command arguments therefore leaves output bytes unchanged.

This constructs an unsigned bundle statement, not a signature or a passed-verdict
claim. It does not sign, upload or grant execution authorization. Invalid links,
missing/duplicate subjects, changed file bytes and output/input aliases fail
before output replacement. Tests generate statements for the complete transport,
inference and physical fixtures and validate the existing public statement schema.
