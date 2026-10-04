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
upstream `^4.1.0` range and replaces the initially proposed 4.1.1 pin to address the published YAML
CPU denial-of-service advisories. Native Include/CLI tests exercise the patched package.

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
timeout yields RunStartupError with the complete cleanup report. Run IDs are reserved before
asynchronous admission.

An OwnedRun starts in preload, becomes ready, and enters measurement only through
beginMeasurement(). finish(hooks) awaits measurement close, last-state capture, recorder drain and
evidence export before disposing its Fiber. Providers register only their own resources through
ctx.runResources.track(). After dispose, independent resource probes return released state and
retained evidence references. Physical cleanup errors and native errors caught by Cordis remain in
the completion report. Completion has passed, error or incomplete status; a run without a
measurement or cleanup proof cannot pass. Call finish before disposing the enclosing host.

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
