# Finite evaluator JSON

`robotics_acceptance_harness.evaluator_json` validates and encodes a prepared
request, then validates captured response bytes. It is a Python codec: it does
not open input files, launch a process, authenticate an evaluator or produce a
verdict. The caller supplies the trusted request and response bindings.

For a development checkout, install the workspace packages as described in the
[harness README](../README.md#development). Import the two functions from the
module:

```python
from robotics_acceptance_harness.evaluator_json import (
    decode_evaluator_response,
    encode_evaluator_request,
)
```

`encode_evaluator_request(request)` accepts a mapping and returns deterministic
JSON bytes. `decode_evaluator_response(raw, *, request_sha256, namespace,
expected_assertion_ids, allowed_evidence_sha256)` accepts the captured response
bytes and returns a tuple of `AssertionEvaluation` values. Both functions raise
`EvaluationError` for invalid inputs.

## Request

The request identifies the run, domain, assigned product namespace, selected
method and a nonempty set of expected assertion IDs. It references the original
scenario, runtime manifest, run, observation and evidence index; an original
result reference is optional. Controls, evidence links and method configuration
retain their existing artifact references. An optional window carries its
integer bounds, clock and timestamp encoding.

`locations` separately maps captured SHA-256 digests to unique relative POSIX
paths. Every document, method configuration and controls reference needs a
location. An evidence link may lack a location; that does not authorize a network
fetch or change its original URI. The caller prepares and verifies the captured
files and any additional method inputs before invoking an evaluator.

The request is limited to 1 MiB, with at most 256 expected IDs, evidence links
and locations. Namespace length is limited to 128 characters. Expected assertion
IDs and location digests and paths must be unique. Unsafe relative paths and a
reversed or empty window are refused. Passing these checks does not prove the
referenced bytes, clock relationship, method selection or calibration.

## Response

The response contains `schema_version`, `request_sha256` and
`assertion_results`. The digest must match the exact request bytes retained by
the caller. The caller separately supplies the assigned namespace, authoritative
expected IDs and allowed evidence digests; it must not derive these from the
response. Returned IDs must match the expected set exactly. Product assertions
must use that namespace and reference known evidence digests.

The response is limited to 1 MiB and 256 assertion rows, with at most 256 evidence
digests per row. The decoder rejects unknown fields, malformed JSON, duplicate
keys, non-finite numbers, mismatched request hashes and invalid product assertions.
A decoded assertion is not a final verdict: the harness's existing assessment path
remains responsible for calibration, coverage and result semantics.

## Resources and execution

The installed harness includes the
[request schema](../src/robotics_acceptance_harness/schemas/evaluator-request.v1.schema.json)
and [response schema](../src/robotics_acceptance_harness/schemas/evaluator-response.v1.schema.json).
They reuse published contracts fragments and do not add roles to the contracts
catalog. Python callers can inspect the package resources with
`importlib.resources.files("robotics_acceptance_harness").joinpath("schemas")`.

The [Node example](../consumer-examples/evidence-byte-check-node/README.md) takes
`--request <path>`, resolves captured locations relative to the request directory,
and writes one JSON response to stdout. The codec itself handles bytes only.
The caller owns execution, trust, timeouts, raw stream capture and cleanup,
and must bind observations to their source clocks.

The [local OCI archive path](evaluator-trust.md#local-oci-archive-assessment)
makes the harness that caller. It prepares verified read-only snapshots, invokes
the pinned local Engine with an operator profile, retains raw response bytes and
decodes them after container settlement. The codec API remains usable without
an Engine; it does not turn caller-supplied response bytes into execution proof.
