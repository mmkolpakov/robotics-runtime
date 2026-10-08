# Offline MCP tools

This optional source package exposes six read tools through the maintained MCP
SDK's stdio transport. It uses the published host RC0 package and installed
contracts 0.19.0/harness 0.20.1 CLIs. It has no published MCP release artifact.

- `describe_contract`: describe a schema ID from the operator's catalog.
- `validate_documents`: validate registered immutable document IDs.
- `explain_bundle`: explain a registered scenario/runtime bundle and its optional
  model, dataset, permit or verification documents.
- `summarize_otlp`: summarize one registered OTLP JSON-lines artifact.
- `explain_result`: explain one registered canonical result.
- `inspect_offline_readiness`: inspect the installed offline environment.

These operations do not start observations or run evaluators. Trusted bootstrap
may supply domain extension schemas as registered immutable artifact IDs.
Bundle-specific evaluator receipts and live readiness remain outside this interface.

## Install and configure

Use Node 24.21.0/npm 11.19.0. Install the locked dependencies and published
Python workers in separate environments:

```bash
cd mcp
npm ci --ignore-scripts
uv venv --python 3.12 .public-workers
uv pip install --python .public-workers/bin/python --require-hashes --no-deps \
  --only-binary :all: --requirement public-cli.lock
```

The trusted operator selects CLI executables and an approved corpus of local
regular files. Files must be read-only and have exact SHA-256/size identities.
Artifact and scratch roots must be canonical directories with no group/other
write access. Request arguments contain IDs; they cannot supply paths, URLs,
executables, environments or arbitrary flags.

For example, prepare read-only `evidence/scenario.json` and
`evidence/runtime.json`, then generate a bootstrap using public byte references:

```bash
mkdir -m 700 mcp-scratch
chmod 444 evidence/scenario.json evidence/runtime.json
CONTRACTS_CLI="$PWD/.public-workers/bin/robotics-contracts" \
HARNESS_CLI="$PWD/.public-workers/bin/robotics-acceptance" \
  node --input-type=module > bootstrap.json <<'JS'
import { referenceFile } from '@robotics-runtime/host';
import { resolve, join } from 'node:path';
const root = resolve('evidence');
const artifacts = [];
for (const id of ['scenario', 'runtime']) {
  const path = id + '.json';
  const ref = await referenceFile(join(root, path));
  artifacts.push({ id, path, sha256: ref.sha256, size_bytes: ref.size_bytes });
}
console.log(JSON.stringify({
  artifactRoot: root, scratchRoot: resolve('mcp-scratch'),
  contractsCli: process.env.CONTRACTS_CLI, harnessCli: process.env.HARNESS_CLI,
  artifacts, schemas: [{ id: 'scenario', schema: 'acceptance-scenario.v1' }],
  bundles: [{ id: 'example', scenario: 'scenario', runtime: 'runtime' }]
}, null, 2));
JS
```

Configure an MCP client to launch `node bin/server.mjs --config bootstrap.json`
from this directory. Use the equivalent absolute executable/config paths when
the client launches from another directory. The client owns the stdio process;
standard SDK transport handles initialization, tool discovery and calls.

## Results and limits

Each tool returns a JSON text envelope with the public `Jobs` result:
`ok`, `exitCode`, `signal`, `timedOut`, `canceled`, `stdout`, `stderr`,
`diagnostic`, `code`, `durationMs`, and captured input IDs/digests/sizes.
Bootstrap may include `extensionSchemas: [{ uri, artifact_id }]`. Schema bytes
pass the same identity/snapshot checks and count toward the combined input limit.
Only `validate_documents` and `explain_bundle` receive the public CLI extension
registry; requests cannot choose a URI or path. `describe_contract` describes
registered built-in schemas. Explain validates document relationships and metadata;
it does not fetch model/dataset/permit asset URIs or verify those asset bytes.

Worker stdout/stderr remain text; their JSON is never parsed or reserialized.
This preserves large integer values. Public Jobs uses upstream Execa text
semantics, including normalization of the terminating newline.

`isError` describes an invocation or admission failure. A successful explanation
of a failed result preserves that result's failure; it does not make the run pass.
An offline dependency report is not native readiness or qualification.

Default limits are 30 seconds per worker, 1 MiB per output stream and 16 MiB
combined input. Bootstrap overrides are capped at 120 seconds, 4 MiB output and
64 MiB input. Four calls may execute concurrently. Inputs are captured into
private verified read-only copies, removed after the worker settles. Symlinks,
changed bytes, outside paths and unknown IDs refuse before worker startup.
Byte bounds apply to regular-file capture. Worker deadlines do not interrupt
blocked filesystem calls; the client must separately bound ownership of the
stdio server process, including startup and filesystem operations.

Stdio trusts the local operator's bootstrap and installed worker code. Tool
annotations are hints, not authorization or an OS sandbox. This package exposes
no HTTP/OAuth listener, native run catalog, start/cancel command or cleanup API.
Future effectful tools require actual admitted consumer/controller operations
and the existing capture/drain/export/cleanup lifecycle.

## Test

```bash
MCP_TEST_CONTRACTS_CLI="$PWD/.public-workers/bin/robotics-contracts" \
MCP_TEST_HARNESS_CLI="$PWD/.public-workers/bin/robotics-acceptance" \
  npm test
```

Tests use the official MCP client and the installed public CLIs. Controlled
worker probes separately exercise raw 64-bit output, timeout, output overflow
and request cancellation. These probes are subprocess-boundary checks.
