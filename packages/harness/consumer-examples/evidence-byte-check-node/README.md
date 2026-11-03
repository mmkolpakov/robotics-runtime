# Node evaluator example

This Node 24.21 example evaluates a retained JSON counter and an explicitly
selected offset in the `org.example.evidence-bytes-node` namespace.
It is a byte-access example, not a robotics performance or calibration method.

Pass one prepared request path and capture stdout:

```bash
node evaluate.mjs --request /absolute/prepared/request.json > response.json
```

The request uses `evaluator-request.v1`. Captured locations are relative to its
directory; original reference URIs remain identity data and are never fetched.
The evaluator checks regular files, rejects symlinks and unsafe relative paths,
and verifies each selected file's size and SHA-256. The owner must keep the
prepared directory stable and read-only for the invocation.

Stdout contains one `evaluator-response.v1` JSON packet with the exact request-byte
SHA-256 and two product assertions. The evaluator creates no response file or
output directory. Invocation failures exit nonzero with diagnostics on stderr.
A selected offset equal to the counter passes, a differing offset fails,
unobserved calibration skips the offset assertion, and a malformed counter or
offset produces an error with a null value. Unsupported calibration states
refuse the invocation.

The implementation uses Node's standard source-aware `JSON.parse` and
`JSON.rawJSON` with `BigInt` for integer tokens. It preserves integer values beyond
JavaScript's safe Number range without changing them into strings. The owner
validates the request, authenticates and limits the process, captures raw stdout
and stderr separately, and validates the response against the expected assertions
and retained evidence identities.

The Dockerfile packages the same entry point on the pinned Node base and selects
UID/GID 65532. The execution owner supplies `--request <path>`, read-only inputs
with the required user mapping, resource limits and network isolation.
Running this example does not establish native readiness or admit an evaluator.

See the [finite evaluator JSON reference](../../docs/evaluator-json.md) for the codec.
