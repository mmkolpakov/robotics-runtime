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

Upstream references: [MCAP Python 1.4.0](https://pypi.org/project/mcap/1.4.0/),
[reader API](https://mcap.dev/docs/python/mcap-apidoc/mcap.reader),
[stream reader API](https://mcap.dev/docs/python/mcap-apidoc/mcap.stream_reader).

The CLI producer regression in `tests/test_writers.py` generates a runtime and
evidence index from the existing minimal-simulation example, validates both, and
checks file-byte bindings. Those inputs are labelled fixtures, not live observations.
