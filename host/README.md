# Robotics runtime host

The host composes finite workers with upstream Cordis 4.0.0-rc.10, Loader 1.0.0-rc.7 and Include
1.1.0. Node 24.21.0, npm 11.19.0 and TypeScript 7.0.2 are pinned. Python packages remain in their
existing uv workspace. Simulator libraries belong to selected worker environments.

Run `npm ci --ignore-scripts`, `npm test` and `npm run check:boundary` from this directory. The
strict compiler checks upstream declarations without `skipLibCheck`, overrides or vendor patches.
Sources compile to ESM with `.js` imports.

The native command is `cordis` in a directory containing `cordis.yml`. The native Include file is an
array of entries with `id`, `name` and `config`. Include supports executable `!!js` expressions:
deployment profiles and their complete module closure must be trusted and immutable. Context
isolation is dependency scoping.

`createHost({ baseDirectory })` supplies the upstream Context and Loader. Awaiting a Fiber or Loader
task proves task completion; a missing import can leave no Fiber and a required injection can remain
PENDING. Required Fiber ACTIVE, binding existence and backend readiness are independent admission
facts.

The host uses native Cordis logging and the console exporter. js-yaml 4.3.2 satisfies Include's
upstream `^4.1.0` range and includes the published YAML CPU denial-of-service fixes.
Native Include/CLI tests exercise this package.

Jobs is a Cordis service that invokes Execa 10.0.1 with literal argv, bounded wall timeout and
output buffers, cancellation, exit status and retained diagnostics. Each owner cancels and reaps its
own outstanding subprocesses. No shell command string is accepted. The environment can pin the
selected execution endpoint explicitly.

Documents and Evaluation provide paths and CLI arguments to the installed `robotics-contracts` and
`robotics-acceptance` commands. `WorkerCommand.prefixArgs` can select a finite worker launcher; no
second evaluator, document serializer or frame bus is introduced. Evaluation windows accept decimal
strings or bigint, preserving integers beyond JavaScript's safe range. Inputs and signed documents
remain files; Node never reads and writes a parsed subject document.

For integration, install the existing Python workspace with `uv sync --locked --all-packages`, then
run `npm run test:workers`. Optional `RR_CONTRACTS_COMMAND`, `RR_ACCEPTANCE_COMMAND` and
`RR_PYTHON_COMMAND` name installed commands. Tests exercise real CLI errors, Python's exact writer,
unchanged input hashes, JSON/JUnit results and raw-evidence diagnostics. The empty-metric fixture
deliberately produces a non-PASS result; it does not qualify simulation behavior.

Subprocesses default to an explicit environment (`extendEnv: false`); profiles supply needed
PATH/endpoint variables. Execa's native `killDescendants: true` handles cancellation of the child
process group. Tests observe a real descendant PID and confirm its termination.

Admission selects an ID from trusted bootstrap configuration. The selected Include profile and its
declared complete module closure must have pinned SHA-256 hashes, regular canonical paths and no
writable permission bits. The configuration is copied and frozen; an untrusted operator cannot pass
a module path or configuration DTO to Include. This admission policy assumes a trusted deployment
owner and immutable package/image storage; Cordis scoping does not sandbox executable profiles.

RunOwner creates an isolated native Fiber tree with distinct service symbols. Required imports must
have a Fiber, required Fibers must be ACTIVE, bindings must exist and each backend must return
observed readiness evidence. A pending dependency, failed import, callback error or bounded probe
timeout yields RunStartupError with a failure report and its OwnedRun. Run IDs are reserved before
asynchronous admission.

An OwnedRun starts in preload, becomes ready, and enters measurement only through
beginMeasurement(). finish(hooks) awaits measurement close, last-state capture, recorder drain and
evidence export before disposing its Fiber. Failed export returns incomplete, retains resources and
keeps the owner ID reserved. Providers register only their own resources through
ctx.runResources.track(). After dispose, independent resource probes return released state and
retained evidence references. Physical cleanup errors and native errors caught by Cordis remain in
the completion report. Completion has passed, error or incomplete status; a run without a
measurement or cleanup proof cannot pass. Call finish before disposing the enclosing host. A
retained run permits explicit retryExport(exportEvidence); earlier failure diagnostics remain in the
completed report. A deadline requests cancellation and bounds the caller; it does not prove that a
producer has stopped. An unsettled readiness, close, capture, drain or export callback keeps the run
retained and its owner reserved. Export and destructive cleanup wait for observed callback settlement.
Each callback must settle only after its own writes and observations have stopped; detached work is
not covered by that promise. A retry while the producer is active remains incomplete. After
settlement, explicit retryExport continues unattempted completion stages and exports evidence without
replaying an already attempted callback. RunStartupError.run supports the same diagnostic recovery;
the original startup report remains a snapshot. Do not dispose the enclosing host before this recovery.
If enclosing disposal still occurs, RunResources refuses destructive cleanup while a managed producer
is active or retained evidence export has not succeeded, and retains the cleanup error.
Cordis may nevertheless dispose its context and other effects;
this guard does not promise cancellation of detached work or reversibility of external effects.
That consumed teardown has no cleanup-retry API, and reservations are process-local; neither limitation
provides crash or distributed recovery.

referenceFile(path, {maxBytes}) streams retained bytes through one opened file handle and checks
file identity, size and modification metadata before and after capture. maxBytes is optional;
omitting it keeps the existing unlimited byte budget. Existing file aliases remain supported,
but retargeting an alias during capture is rejected. Producers must close or seal the file before
capture and keep it stable afterward. A byte reference does not qualify native export or verify
the evidence contract; those checks remain with the provider and public Python tools.

The single host-owned schema is schemas/host-composition.v1.schema.json, namespace
org.robotics.runtime.host, URI urn:robotics:host:composition:v1. It records observed bindings,
package/config identity, declared and effective capabilities, native endpoints, time
authority/domain/epoch, native units/precision, coordinates and retained lifecycle/cleanup
references. Effective capabilities require qualification evidence; declarations alone do not qualify
behavior. No simulator step/control API is added.

producers/attach_composition.py is a finite adapter to the existing public Python extension API and
writer. It verifies retained local file references, adds the pinned extension declaration to an
unsigned template and validates the existing generic role. It never rewrites a signed input. Native
seconds and integer timestamps remain in their original evidence files; host metadata records their
representation instead of inventing exact nanoseconds.

Documents and Evaluation require WorkerCommand configuration with a nonempty executable; no Python
command is inferred. Use an absolute executable or provide an explicit env.PATH for a named tool.

Lifecycle deadlines are checked during admission before any provider Fiber starts. Owner IDs remain
reserved until disposal and independent resource verification finish. Runtime JavaScript numbers and
coercible objects are rejected by the nanos API before any worker is launched.

MAVSDK uses grpc-js 1.14.5 and proto-loader 0.8.1 with official proto inputs pinned to commit
5c81ecfeb6110cf74ba75ae50b78a1b265c05670. The official type generator emits ESM .js imports; runtime
loader flags match generation and decoded int64 values remain strings. Mavsdk exposes native
generated Core/Action/Telemetry clients. waitForReady proves transport; Core connection state,
native health and operation result remain separate observations. No flight controller or simulator
API is introduced.

Native streams use cancellation and finite deadlines, and owner disposal closes their native
channels. The selected native channel pool is local to the owner and ambient HTTP proxy selection is
disabled. An initial TCP connection to a blackholed endpoint can outlive grpc-js logical channel
shutdown in this upstream version; only configured local owned endpoints are qualified here.
Unreachable remote TCP cleanup is not accepted by the current qualification.

MediaEndpoint invokes producers/media_worker.py through the existing finite Jobs route. The separate
GI worker calls Gst.parse_launch, set_state/get_state and native GstBus EOS/ERROR. Native frames
stay inside the configured pipeline and sink. The worker emits native state, error, exact int64
position and NULL cleanup facts. A ready marker supports cancellation after actual PLAYING
observation. Output files are admitted exclusively before execution so retained inputs cannot be
overwritten.

Run npm run generate:mavsdk to verify official proto identities and regenerate types. The verified
MAVSDK server installer uses tools/mavsdk-server.v4.0.3.json and stores the binary only in .tools.
Native source-profile tests additionally require the infra C12 GI image
localhost/rr-c-media:c12-locked, its
recorded APT closure, project Tini and the hash-locked pymavlink fixture environment. Run npm run
test:native after preparing those inputs. These native tests are separate from test:workers so the
Node/Python CI job does not pretend that a GI media image is installed.

The observed server is MAVSDK 4.0.3, SHA-256
7cd0a2995460983e82fe2cf0ef187aba852bb849168ce972a139680f3611c0d8. Its gRPC endpoint starts after
discovery. The heartbeat fixture uses pymavlink 2.4.50 and records the generated codec source hash;
it proves discovery only. Native GStreamer 1.24.2 emitted a 27648-byte synthetic RGB payload, EOS,
missing-input ERROR, bounded timeout and canceled-state NULL cleanup. Vehicle health, flight action
effects, real cameras, RTSP and GPU rendering are outside these C12 observations.

For local profile preparation, provide uv at /usr/local/bin/uv and the pinned infra media image,
then run npm
run prepare:native and npm run fetch:mavsdk-server before npm run test:native. The setup installs
only a project test environment inside the worker container. Native output facts and synthetic
payloads are retained in artifacts/host/c12 for independent review.
