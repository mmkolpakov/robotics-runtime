# Product evaluator SDK

Product packages use the public `robotics_acceptance_harness.sdk` module, available
from harness `0.20.0` (currently an unreleased development candidate). It exports
`EvaluationContext`, `ProductEvaluator`,
`AssertionEvaluation`, `HarnessError`, `EvidenceAccessError` and
`EvidenceValidationError`. Product code should not import private harness modules,
construct evidence paths, or duplicate the harness's evidence verification.

The runnable [evaluator template](../examples/evaluator-template/README.md) has a
`src` layout, a `py.typed` marker and a standard
[PyPA entry point](https://packaging.python.org/en/latest/specifications/entry-points/):

```toml
[project.entry-points."robotics_acceptance.evaluators"]
"org.example.recording" = "recording_evaluator:evaluate"
```

Its wheel declares `robotics-acceptance-harness>=0.20.0,<0.21`, `mcap>=1.4,<2` and
`zstandard>=0.25.0,<1`. Zstandard is a direct dependency because the evaluator
imports its `ZstdError`; 0.25.0 is the tested minimum. MCAP supplies LZ4 as a dependency.
The harness supplies the contracts dependency, with a 0.18 floor. The SDK version
floor is not satisfied by an older installed distribution with similar source code.

Extension registries are supplied explicitly by the host; the SDK does not discover
or automatically load extension schemas. `load_bundle(..., extension_schemas=...)`
forwards the supplied registry to all bundle inputs, including the runtime document.
Registry propagation through evidence indexes, receipts and application CLI paths
has separate integration checks. The template's wheel proof uses core-schema
documents and does not qualify extension support across those paths.

Host-side readers can pair a path with its local schema registry using
`DocumentSource` from `robotics_acceptance_harness.documents`. For example,
`load_evidence_index(DocumentSource(index_path, registry))` validates the index,
recording summaries and receipts against the same registry. The source copies
the registry so later caller changes cannot replace the schemas. Existing path-only
calls remain valid for documents without pinned extensions.

## Evaluator inputs and results

A `ProductEvaluator` accepts an immutable `EvaluationContext` and returns an
iterable of `AssertionEvaluation` objects. The context provides `scenario`,
`runtime`, `run_id`, `domain_id`, the observation window, metric samples and
verified evidence metadata. `context.evidence.links` remains the metadata API;
the same object is callable to open evidence by its SHA-256 digest:

```python
from robotics_acceptance_harness.sdk import EvaluationContext

def read_prefix(context: EvaluationContext, digest: str) -> bytes:
    with context.evidence(digest) as snapshot:
        prefix = snapshot.read(8)
        snapshot.seek(0)
        assert snapshot.read(8) == prefix
        return prefix
```

The stream is a read-only, seekable **verified snapshot**, positioned at zero.
The SDK rechecks the complete local payload's size and digest before yielding it;
later changes to the original file do not change bytes read from that snapshot.
Closing the context manager releases the snapshot. Do not retain the stream for
use outside the `with` block. Small snapshots use memory; large files spill to
temporary disk, so evaluation needs scratch space for the active snapshots.

Access is local only. A retained S3/HTTPS link and its receipt do not make local
bytes available, and `context.evidence(digest)` does not fetch remote objects.
Unknown digests or unavailable local payloads raise `EvidenceAccessError`; missing,
changed or otherwise unverifiable files raise `EvidenceValidationError`. These
are input failures, not evidence that the product property failed.

The example reads every MCAP message in file order using the public
[MCAP reader](https://mcap.dev/docs/python/mcap-apidoc/mcap.reader), with CRC checking.
It counts messages instead of trusting summary statistics, does not decode product
message bodies, and does not sort the whole recording in memory. Each distinct
verified `application/mcap` digest gets one assertion:
`org.example.recording.nonempty.<sha256>`. A nonempty recording yields `passed`,
an empty but readable recording yields `failed`, and unavailable/unreadable evidence
yields `error` with an `InputError` message. No MCAP artifacts is an `InputError`
exception because there is no verified digest to attach to an assertion.
Corrupt ZSTD/LZ4 chunks are input errors even when their evidence-index digest
matches: the example handles `ZstdError` and LZ4's `RuntimeError` explicitly and
keeps the verified digest on the error assertion.

The only assertion statuses are `passed`, `failed`, `error` and `skipped`.
Use `source="product"`, your registered namespace, an assertion ID under that
namespace, and at least one `evidence_sha256` drawn from verified evidence. The
example keeps the digest even on input-error results, and never turns an unreadable
recording into a passing assertion. Product-specific assertions should define their
own property, units, missing-data behavior and namespace.

## Qualification and identity

Use the same qualification described in the [harness README](../README.md#product-evaluators).
The scenario's `evaluator_requirements` and runtime's `evaluator_bindings` must
agree on namespace, entry-point target, distribution, version, wheel SHA-256 and
receipt SHA-256. Retain the released wheel's receipt, typed external verification,
and referenced statement/trust-policy/verification-bundle dependencies.

```sh
robotics-acceptance doctor --scenario scenario.json \
  --evaluator-receipt evaluator-receipt.json \
  --evaluator-verification evaluator-verification.json \
  --evaluator-receipt-dependency evaluator-statement.json \
  --evaluator-receipt-dependency evaluator-trust.json \
  --evaluator-receipt-dependency evaluator-verification.bundle
```

Qualified `doctor` checks metadata, the receipt chain and installed `RECORD` without
importing the evaluator. The release receipt authenticates the recorded wheel
identity; installed file hashes are checked separately inside the observed
execution-subject image. An installed `RECORD` or PEP 610 `direct_url.json` does
not prove released wheel identity. Dependencies outside the evaluator's namespace
remain part of the image's trust boundary. This is not a Python sandbox.

Install without generated bytecode, unset `PYTHONPYCACHEPREFIX`, and use a fresh
interpreter. Do not pre-import the evaluator before qualified loading. Production
qualification must use your real external verification chain; the receipt helper
used by the tests creates typed fixtures, not a production signature.

## Reproduce the wheel proof

From the repository root, after syncing the candidate SDK and metadata:

```sh
EVALUATOR_TEMPLATE_PROOF_DIR=/tmp/spec56-wheel-proof \
EVALUATOR_TEMPLATE_REQUIRE_INTEGRATION=1 \
uv run --no-sync python -B -m pytest -p no:cacheprovider -v \
  packages/harness/tests/test_evaluator_template.py
```

In PowerShell set those two environment variables with `$env:NAME = 'value'` and
use an absolute directory under `$env:TEMP` for the proof directory. Every run gets
its own subdirectory. The tests copy build sources outside the repository, build
the template and matching harness/contracts wheels, then install them together
with dependency resolution into a clean venv outside the workspace. They run
`uv pip check`, discovery, `doctor --scenario` with actual typed receipt helpers,
a rejected qualification, and qualified positive/empty/invalid-MCAP evaluation,
including readable and corrupted ZSTD/LZ4 chunks with matching evidence digests.
Mypy checks the installed wheel using `proof/typing_probe.py` and must reject an
incorrect argument in a separate negative consumer.

The proof directory retains wheels, SHA-256 identities, typed receipt fixtures,
doctor/evaluation output, type-check logs and `wheel-proof.json`. A `passed` proof
is written only after all checks succeed. Before the harness and contracts version
floors are present, the integration test reports a skip with a `blocked` proof;
`EVALUATOR_TEMPLATE_REQUIRE_INTEGRATION=1` makes that condition a failure. Building
the template alone or running source-level tests is not a passing installation proof.
