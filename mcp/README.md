# Offline MCP tools

This optional source package exposes six read tools through the maintained MCP
SDK's stdio transport. It uses the published host RC1 package and installed
contracts 0.21.1/harness 0.22.3 CLIs. Install this adapter from source using the
locked dependencies below. The [assistant integration guide](../docs/agent-integration.md)
relates these tools to configuration, campaigns, execution and archive assessment.

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

Supported document versions come from the selected installed workers and the
operator's schema catalog. The locked published workers support canonical role
defaults and explicit native v2 documents. The adapter forwards both versions
as exact files without adding ROS fields.
A native incomplete verdict remains incomplete through `explain_result`.

## Install and configure

Use Node 24.21.0/npm 11.19.0. Install the locked dependencies and published
Python workers in separate environments:

```bash
cd mcp
npm ci --ignore-scripts --engine-strict
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
the SDK handles discovery and tool calls for MCP 2026-07-28 and negotiated
legacy clients. Current-protocol clients use `server/discover` and per-request
capabilities; legacy clients use their negotiated initialization path.
The [protocol specification](https://modelcontextprotocol.io/specification/2026-07-28)
defines that distinction; client setup does not add domain operations.

## Build and consume an offline MCPB

The MCP CI job builds one `.mcpb` containing the server, preparation helper,
license and production Node dependencies from `package-lock.json`. It validates
the manifest against the official MCPB 0.3 schema from MCPB 2.1.2, pinned by SHA,
and uses Python's standard ZIP CLI. Source locks remain separate build inputs.
CI compares two archives built with normalized mtimes in the same toolchain.

The current profile is Linux with an operator-selected Node 24.21.0 executable
and bootstrap file. A standard MCPB client substitutes `node_executable` and
`bootstrap_file` into the manifest's literal command/arguments. The separately
installed C0.21.1/H0.22.3 workers remain selected by that bootstrap; startup
performs no package installation. A generic stdio client can use the extracted
bundle directly:

```bash
python3 -m zipfile -e robotics-runtime-mcp-0.1.0-rc.1.mcpb /approved/bundle
/approved/node-24.21.0/bin/node /approved/bundle/bin/server.mjs \
  --config /approved/bootstrap.json
```

Select and verify the bundle as executable code before configuring the client.
The installed consumer check runs the existing six-tool test with a read-only
filesystem, disabled network and separate artifact/client mounts. Its dependency
image supplies the explicit published Python workers. These are offline document
checks; native execution and desktop client qualification have separate gates.

## Prepare a qualification package

For an externally verified qualification package, prepare the existing bootstrap
from its writer-produced `qualification-arguments.txt`. Select a stable read-only
operator corpus and a private scratch directory, then run the helper with the
same installed contracts Python used by the workers:

```bash
.public-workers/bin/python tools/prepare-bootstrap.py \
  --package-root /absolute/verified-package --domain primary \
  --scratch-root "$PWD/mcp-scratch" \
  --contracts-cli "$PWD/.public-workers/bin/robotics-contracts" \
  --harness-cli "$PWD/.public-workers/bin/robotics-acceptance" > bootstrap.json
```

Repeat `--domain` for each selected qualification domain. The helper prints the
artifact/bundle ID mapping to stderr and the existing bootstrap JSON to stdout.
Success exits 0; a refused input exits 2 without emitting a bootstrap.
IDs derive from logical subject names and remain stable when the corpus moves.
Built-in schema IDs use the installed public catalog, replacing dots with
underscores. No document bytes or signed subject names are rewritten.

The imported file contains literal arguments on separate lines, not a shell
command. Only artifact/extension bindings and the public qualification profile
pair are accepted: v1 without a comparison rule, or v2 with
`exact_assertion_outcome`. These profile fields are data, never forwarded to a
worker. The public contracts loader validates selected contract documents and
provides their exact SHA-256/size. Contract documents, metrics and declared
extension schemas enter the existing catalog; recordings, packages and other raw
payloads stay outside this read corpus. A bundle needs one scenario and the
selected `runtime-manifests/<domain>.json`; optional roles must be unambiguous.

Preparation refuses links, nonregular/outside inputs, changed selected files,
unknown arguments and existing MCP size/count violations. It assumes a stable
operator-owned corpus: its path/stat checks do not establish raceproof admission
against malicious concurrent directory replacement. It neither verifies
signatures nor qualifies the package. Each later MCP call still verifies the
registered identities through the existing private snapshot mechanism.
Executables, roots and trust remain explicit operator choices.

Resource-aware clients can discover the registered choices by listing resources
and reading `robotics-runtime://catalog`. This bounded, fixed bootstrap view
contains schema IDs/names, relative artifact paths with SHA/size and bundle
roles. Reading it launches no worker. Tool calls still capture and verify the
selected bytes; catalog metadata is neither a fresh file check nor qualification.

For a [stock mcporter 0.16.1 configuration](https://github.com/openclaw/mcporter/blob/v0.16.1/docs/config.md)
whose `robotics_runtime` entry selects the approved Node/entrypoint/config argv,
list and read the catalog, then use its IDs in the six existing tools:

```bash
mcporter --config /absolute/operator/mcporter.json resource robotics_runtime --output json
mcporter --config /absolute/operator/mcporter.json resource robotics_runtime robotics-runtime://catalog --output json
```

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
Execution integrations use actual admitted consumer/controller operations and
the existing capture/drain/export/cleanup lifecycle. The
[server integration contract](../docs/agent-integration.md#server-operations-through-mcp)
keeps read, execute, cancel and recovery permissions distinct. An optional Tasks
projection reports an existing operation handle; it adds no execution owner.
Dagu's own MCP endpoint belongs to the selected local campaign workbench and has
broader operator powers. It does not replace this document adapter.

## Test

```bash
MCP_TEST_CONTRACTS_CLI="$PWD/.public-workers/bin/robotics-contracts" \
MCP_TEST_HARNESS_CLI="$PWD/.public-workers/bin/robotics-acceptance" \
  npm test
```

Tests use the official MCP client and the installed public CLIs. Controlled
worker probes separately exercise raw 64-bit output, timeout, output overflow
and request cancellation. These probes are subprocess-boundary checks.

With the locked published workers, run the native v2 document integration check:

```bash
MCP_TEST_CONTRACTS_CLI="$PWD/.public-workers/bin/robotics-contracts" \
MCP_TEST_HARNESS_CLI="$PWD/.public-workers/bin/robotics-acceptance" \
  npm run test:native
```

This check prepares the public native archive example before starting MCP. It
then exercises all six read operations, original source hashes, missing
observation diagnostics and large integer preservation through real CLI
validation. It does not execute a native workload through MCP.

See [result and recording inspection](../docs/viewing-results.md) for the
CLI/JUnit path and compatible upstream viewers.
