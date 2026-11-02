# File-based Node evaluator example

This small Node 24.21 example evaluates a retained JSON counter and an explicitly
selected offset. It uses the finite `evaluator-request.v1` and
`evaluator-response.v1` files and the `org.example.evidence-bytes-node` namespace.
It is a byte-access example, not a robotics performance or calibration method.

The owner supplies `/input/request.json`, captured read-only files under `/input`,
and a separate writable `/output` directory. The evaluator verifies each selected
file's size and SHA-256 against its original reference; it never fetches the URI.
It writes `/output/response.json` with the exact request-byte SHA-256 and two
product assertions. A selected offset equal to the counter passes, a differing
offset fails, unobserved calibration skips the offset assertion, and a malformed
counter or offset produces an error with a null value. Unsupported calibration
states refuse the invocation.

The implementation uses Node's standard source-aware `JSON.parse` and
`JSON.rawJSON` with `BigInt` for integer tokens. It preserves integer values beyond
JavaScript's safe Number range without changing them into strings. The owner
validates the request, authenticates and limits the process, and validates the
response against the expected assertions and original evidence identities.
Running this example does not establish native readiness or admit an evaluator.
