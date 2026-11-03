# Integrate an assistant with testing and evidence

An assistant can help author scenarios, validate inputs, request an admitted
execution, inspect its observations and explain retained results. The same
files and operation identities serve a person at the CLI, CI and an MCP client.
The model does not become the execution owner or the authority for a verdict.

This guide defines the integration architecture and its ownership rules.
The command examples use the published contracts and harness interfaces.
The execution and server sections define the contract for a deployment that
supplies those operations; they do not assign new command or tool names.
Use the [first-result guide](first-result.md) for a complete document example,
[architecture](architecture.md) for native boundaries, and the
[MCP package guide](../mcp/README.md) for the six concrete offline tools.

## Choose an entry point

Use the CLI for a local task or CI job. Use the optional domain MCP adapter to
inspect a registered collection of immutable documents. Any compatible MCP
client can use that adapter; model selection belongs to the client. Neither
robot execution nor evidence evaluation depends on a model provider or a
coding-agent CLI.

For a local campaign workbench, the selected integration profile is
[Dagu](https://github.com/dagucloud/dagu/releases/tag/v2.24.0): its existing UI,
YAML workflows, run history, scheduling and MCP endpoint invoke the same finite
commands. For Kubernetes campaigns, the selected profile is
[Argo Workflows](https://github.com/argoproj/argo-workflows/releases/tag/v4.1.6).
These are alternative deployment profiles. A campaign selects one scheduler;
it does not pass an attempt through both engines.

The CLI and retained files remain usable without either campaign system.
Contracts-only validation and built-in offline assessment require no Node,
simulator or container Engine. The domain MCP adapter adds Node. A selected
native execution profile supplies its own runtime. The isolated OCI evaluator
design requires an Engine for that evaluator, independently of document reading.

## Interaction matrix

Each row describes a user task, its interface and the owner of its effects.
A permission to read evidence does not grant permission to execute a workload.

| User task | Entry and protocol | Identity to retain | Owner and permissions | Reused mechanism | Meaning of the response |
| --- | --- | --- | --- | --- | --- |
| Author configuration and a test plan | Editor or assistant proposes scenario/overlays and deployment workflow files; reviewed files enter Git | Source revision, resolved input digests and overlay trace | Product author owns configuration; write access to a working copy, with separate execution permission | Existing contract schemas, RFC 7396 overlays, Dagu YAML or Argo templates | A saved proposal describes intended work; it establishes no runtime fact |
| Validate and explain inputs | Person/CI uses contracts and harness CLI; domain MCP uses registered IDs | Schema IDs, artifact IDs, original SHA-256/size and bundle selection | Contracts/harness validate; local filesystem permissions or trusted MCP bootstrap scope access | JSON Schema, public CLIs, official MCP SDK | Validation or explanation outcome; no workload starts |
| Admit and execute one attempt | Reviewed CLI composition or campaign step invokes the deployment's finite attempt entry point | Request/operation ID, distinct attempt ID, admitted profile/image/input digests, actual resource identities | Deployment admits the request; finite attempt owner acquires resources; execution credentials stay with that owner | Literal argv process execution, Compose/Engine or Kubernetes workload mechanisms | Admission or start acknowledgement; command acceptance and observed completion remain separate |
| Observe progress and request cancellation | CLI/CI reads the operation; campaign UI/MCP reads or requests stop; native observers use their selected SDK | Operation/attempt IDs, native goal/request IDs and resource UIDs | Attempt owner controls native effects; read and cancel permissions are separate | Dagu or Argo status/log interfaces, native SDK observations, bounded process supervision | Last observed progress or cancellation request; neither proves stopped producers or cleanup |
| Verify and explain a closed archive | Contracts qualification validation, harness explanation, or domain MCP inspection | Original subjects/digests, evidence inventory, result IDs and verification records | Contracts/harness validate relationships; external verifier authenticates signatures using operator trust | Existing receipt inventory, in-toto statements, Cosign and public CLIs | Structural validity, authenticated provenance and domain verdict are separate facts |
| Reassess an archive with a custom method | Person/CI invokes the documented assessment CLI with selected controls; a campaign can schedule it | Original execution/result digest, new result ID, method/environment/calibration identities | Harness owns coverage and final verdict; admitted evaluator owns only its assertions; code execution requires separate trust | Existing assessment controls and evaluator trust; Cosign and finite OCI runtime isolation in the execution design | A new assessment with its own coverage; the original result and signed bytes remain intact |
| View results and recordings | CLI explanation, JUnit CI viewer, or stock Rerun Viewer MCP | Result/original recording identities, viewer recording ID and declared time domain | Viewer reads artifacts and may change viewer state; it has no native execution authority | JUnit, Rerun Viewer MCP (stdio to local gRPC), PlotJuggler and native readers | A rendering of retained facts; layouts/screenshots are derived outputs and supply no missing observation |
| Recover export and release resources | Operator/CI requests recovery for the identified attempt; campaign records that operation | Sealed attempt journal, exact resource UIDs and export references | Domain recovery owner verifies the previous producer stopped, then exports or cleans only owned resources | Retained storage, native resource APIs and existing evidence writers | Export/cleanup proof or an incomplete outcome; recovery does not replay an unknown native effect |

The execution rows require an admitted deployment operation. The offline MCP
adapter's concrete interface is the six tools below; it does not infer an
execution operation from a document or expose arbitrary commands.

## Author, validate and explain

An assistant edits ordinary configuration in the product working copy. Use
existing scenario documents and deployment files to express the plan. Keep the
resolved scenario and origin trace with the reviewed source revision. For
example, the published contracts CLI resolves reviewed overlays:

```bash
robotics-contracts scenario resolve base.yaml \
  --overlay camera.yaml --overlay limits.yaml \
  --output resolved.yaml --trace-output resolution-trace.json
robotics-contracts validate resolved.yaml
robotics-acceptance explain --scenario resolved.yaml --runtime runtime-manifest.json
```

These filenames name inputs supplied by the integration; the
[contracts reference](../packages/contracts/README.md#cli) describes the commands.
An assistant cannot establish runtime readiness by filling a manifest from a
configuration file. The runtime producer obtains facts from the actual native
endpoint. Signed subjects remain exact files; author a new configuration rather
than editing a retained signed document.

## Use the domain MCP tools

The adapter exposes the following tools through stdio. The trusted operator
registers the catalog and artifact IDs before the client starts.

| Tool | Request arguments | Public worker operation | Effect |
| --- | --- | --- | --- |
| `describe_contract` | `schema_id` | Contracts schema description | Reads a registered schema choice |
| `validate_documents` | `artifact_ids` | Contracts document validation | Reads verified snapshots of registered files |
| `explain_bundle` | `bundle_id` | Harness bundle explanation | Reads the configured bundle and checks its relationships |
| `summarize_otlp` | `artifact_id` | Harness OTLP summary | Reads one registered metrics artifact |
| `explain_result` | `artifact_id` | Harness result explanation | Explains a stored verdict without evaluating it again |
| `inspect_offline_readiness` | Empty object | Harness offline dependency inspection | Reports installed dependencies, not native readiness |

A resource-aware client lists resources, reads `robotics-runtime://catalog`, and
uses the returned schema, artifact and bundle IDs with the six tools. The catalog
is a bounded view of registered bootstrap metadata; it does not recheck files.
Each tool call captures and verifies the selected bytes before invoking its worker.

For the bootstrap in the [MCP guide](../mcp/README.md#install-and-configure-from-source),
a client can call `describe_contract` with `{"schema_id":"scenario"}` and
`explain_bundle` with `{"bundle_id":"example"}`. Register a result or metrics
artifact through the same trusted bootstrap before using its ID.

The standard client uses MCP discovery and tool calls, not a model-specific
plugin or custom command protocol. The selected SDK supports MCP 2026-07-28
and negotiated legacy clients. Per-request capabilities and
`server/discover` belong to the current protocol; legacy clients use their
negotiated initialization path. The SDK handles the wire differences. See the
[MCP specification](https://modelcontextprotocol.io/specification/2026-07-28)
and the [SDK release](https://github.com/modelcontextprotocol/typescript-sdk/releases/tag/v2.4.0).
The locked server and core packages are version 2.4.0.

Stdio authenticates no remote user. The local operator controls the executable,
bootstrap, admitted read-only files and process permissions; the client owns the
server process. Request arguments contain registered IDs, never arbitrary paths,
URLs, executables, environment variables or flags. Tool annotations describe
effects but do not authorize them. A server deployment adds its own identity and
permissions rather than widening this local bootstrap silently.

## Execute through a campaign profile

The finite attempt interface is the common execution contract. A deployment
must document its argv, admitted configuration, operation identity, output files,
cancellation request and recovery operation before exposing execution to clients.
The [host lifecycle](../host/README.md) supplies the existing ownership rules.
An execution adapter must return the observed native outcome and evidence
references, not infer success from an accepted command or a process exit alone.

### Local workbench with Dagu

Use Dagu's existing UI, queue, history and MCP server for local campaigns. The
reference integration uses v2.24.0 and stock `action: exec` with
`with.command` and `with.args` to invoke reviewed finite CLI operations.
The deployment supplies the real installed command and literal argv. Use this
route for an existing launcher or a complete workload manifest that a specialized
action does not express. No separate workflow engine or queue adapter is needed.

Dagu provides three MCP tools at its authenticated `/mcp` endpoint:

- `dagu_read` inspects workflow definitions, runs and logs.
- `dagu_change` previews or applies workflow and Wiki changes.
- `dagu_execute` starts, enqueues, retries or stops runs and decides waiting steps.

This is an operator workbench with broad powers, including inline workflow
execution. Configure stock authentication and the credential's MCP surface,
roles and workspace access for the intended deployment. A single operator can
use Community; team IAM, SSO and audit requirements select the applicable
self-host plan. A read-only client tool selection is not a substitute for
server-side authorization. Keep domain document inspection on its narrower
adapter when execution permission is unnecessary.

The recipe must separate the Dagu run ID from the domain attempt ID. Disable
root and step/default retries around a native measurement unless the attempt
owner explicitly admits a new attempt; do not replay an unknown native effect.
Dagu may retry repeatable document work under its workflow policy. A
`dagu_execute` wait timeout leaves the run executing. Its `stop` operation
controls the workflow; the native owner must still retain cancellation, drain,
export and cleanup facts. Workflow history is an operational record, not the
immutable qualification archive.

Dagu's Kubernetes action is useful for Jobs within its supported configuration.
For a retained multi-worker attempt, stock literal `exec` invokes the same
finite attempt interface as the CLI. A deployment choosing Argo leaves cluster
workflow ownership with Argo; Dagu adds no direct Kubernetes backend beside it.
Dagu does not own the domain export barrier. Its source is GPL-3.0-or-later; CLI/server use as
a separate program and commercial embedding have distinct terms. See
[Dagu MCP tools](https://docs.dagu.sh/mcp/tools),
[authentication](https://docs.dagu.sh/mcp/authentication),
[self-host plans](https://docs.dagu.sh/overview/self-host-license) and
[licensing](https://github.com/dagucloud/dagu/blob/v2.24.0/LICENSING.md).

### Kubernetes campaigns with Argo

Argo Workflows supplies the campaign DAG, fan-out, retry policy, status and UI.
The reference integration uses v4.1.6, licensed under Apache-2.0. Its resource
template can create the complete finite Job manifest. Retained storage has a
lifetime independent of Workflow garbage collection. Narrow domain admission,
actual Job/Pod/PVC UID bindings and a retained attempt journal remain with the
execution integration; they do not form another general scheduler.

Keep measurement retries disabled at both workflow and Job boundaries until a
new attempt is admitted. Independent archive assessments may use ordinary
workflow retries with separate output identities. An operator can use Argo's
standard `stop` or `terminate` operations: `stop` allows exit handlers,
while `terminate` skips them. Neither operation proves native drain or exact
export, especially after node loss. See the upstream
[resource template](https://github.com/argoproj/argo-workflows/blob/v4.1.6/docs/walk-through/kubernetes-resources.md),
[`stop`](https://github.com/argoproj/argo-workflows/blob/v4.1.6/docs/cli/argo_stop.md)
and [`terminate`](https://github.com/argoproj/argo-workflows/blob/v4.1.6/docs/cli/argo_terminate.md)
contracts.

## Observe, cancel and recover

The attempt owner coordinates readiness, the measurement window, last-state
capture, recorder drain, evidence export and observed cleanup in that order.
Native SDK/control/media connections remain between the selected workers and
their endpoints. MCP requests and campaign logs are outside those data paths.

Keep these outcomes distinct in the CLI report, UI and assistant response:

- Invocation/admission: was the request valid and authorized, and which operation
  or attempt did it identify?
- Native execution: was a command accepted, did the operation reach an observed
  terminal state, and was its required postcondition measured?
- Retention and cleanup: are producers settled, are exact evidence bytes sealed
  and exported, and were only the bound resources released?
- Assessment: which assertions passed, failed or remained unevaluated, under
  which method, clock, calibration and environment?

A deadline bounds the caller and requests cancellation. It does not prove that
a producer stopped. If the acknowledgement is lost, read the same operation
identity before making another request. An operation key prevents duplicate
admission only when the deployment enforces that contract. Resource names and
labels locate resources; observed UID bindings govern effects.

Recovery first establishes that the previous writer stopped and checks the
sealed journal. It can continue export and materialize verified original bytes
for assessment. It must not create native measurement workers or replay an
unknown command. An ambiguous writer or missing evidence remains incomplete.
One owner controls native cancellation and cleanup; a campaign or MCP client
requests those operations and reports their retained outcome.

## Verify, reassess and view an archive

Use the published [qualification tools](../packages/contracts/docs/qualification.md)
to validate the explicit subject inventory and document relationships. Authenticate
the retained statement using the external verifier and operator trust policy.
A digest match or schema-valid statement alone does not authenticate a signer.
Keep exact original subjects, receipt dependencies and signature evidence.

For the result produced by the [first-result example](first-result.md), these
existing commands validate and explain the result without executing a workload:

```bash
robotics-contracts validate results/acceptance-result.json
robotics-acceptance why results/acceptance-result.json --format markdown
```

`why` can succeed while explaining an incomplete or failed verdict. Harness
verdict-producing commands return 0 for passed, 1 for a completed non-passing
verdict and 2 for a handled input/observation/execution exception. An exception
diagnostic differs from a retained result whose domain status is error.
The contracts CLI has its own documented exit-code contract. Neither a successful
MCP invocation nor a green workflow node replaces the domain result.

To select a different archive method, use the existing
[assessment controls and original-result options](../packages/harness/docs/archive-assessment.md)
of `robotics-acceptance evaluate`. Keep the original run/evidence arguments,
choose separate output and retain the new result ID. Method, environment,
calibration, original result digest and covered assertions determine whether two
assessments can be compared. Changing an assessment does not change the original
measurement. Active playback requires a newly admitted execution.

The isolated evaluator integration executes an admitted OCI digest as a finite
process with verified read-only inputs and bounded output. Operator trust admits
the code; the harness validates namespace, evidence digests, calibration and
coverage and produces the final verdict. The
[evaluator trust reference](../packages/harness/docs/evaluator-trust.md)
separates the Python wheel interface from the optional OCI archive path in a
matching source workspace. The latter uses the existing `evaluate` command with
versioned assessment controls and an external operator profile; it is not a
capability of the published read-only MCP tools.

Use JUnit in the CI viewer and open compatible original recordings with
[Rerun or PlotJuggler](viewing-results.md). A campaign UI links to the retained
result and recording identities. It does not replace them with its own log
serialization. OTLP can correlate operational traces with run/attempt IDs;
native evidence retains its declared clock and exact integer timestamps.
A trace timestamp does not establish a cross-clock relation.

## Server operations through MCP

Use Dagu's existing MCP run operations and run handles for local campaign
effects. Use Argo's stock API and CLI for Kubernetes campaigns. The six-tool
domain adapter remains offline and read-only. These profiles require neither a
separate effectful domain MCP server nor a Tasks implementation.

Use the selected server's documented authentication and distinguish read,
author/change, execute, cancel and recovery permissions. Retain the acting
principal, operation identity and admitted input identities. The standard
[HTTP authorization contract](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
applies where the chosen remote MCP service supports it. The local stdio adapter
keeps credentials and process permissions with its operator.

If a selected existing server supports the optional
[MCP Tasks extension](https://modelcontextprotocol.io/extensions/tasks/overview),
a long-running operation can use that server's durable task handle. Client and
server must negotiate support. The server creates the task before returning its
handle; clients retain its ID and poll with `tasks/get`. Input requests use
`tasks/update`; `tasks/cancel` is cooperative and does not prove native
termination. Keep the task ID, admitted operation ID and domain attempt ID
distinct and linked. A reconnect resumes observation of the same operation.
This adds no second queue, retry or cleanup owner. The Dagu 2.24.0 reference
profile uses its ordinary run IDs; Tasks support is not assumed or required.

[Elicitation](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)
collects input through the client. It does not itself authorize robot execution
or become an admission record. Keep credentials in the appropriate secure
authorization flow; form elicitation must not request secrets. If the client
does not support Tasks or elicitation, the deployment's ordinary operation
handle and operator interface remain the integration route.

Use the chosen service's documented REST API or official client for CI where
appropriate, and its MCP interface for a compatible assistant. An API description
does not grant access to every operation or turn arbitrary argv into a domain
tool. Reuse the existing contract catalog and evidence inventory across these
interfaces rather than creating another schema registry or agent framework.
