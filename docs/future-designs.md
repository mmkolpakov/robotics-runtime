# Design boundaries beyond the current guide

These directions are separate from implemented interfaces and published artifacts.
They do not add commands to the first-result path or qualify a runtime profile.

The optional offline MCP adapter exists as source and provides six read tools.
A published MCP artifact, HTTP/OAuth service, live run catalog, admitted start/cancel
operations and a Web UI are outside its current surface. Effectful tools would
need real consumer/controller admission and the existing capture, drain, export
and verified cleanup lifecycle.

Additional autopilot or simulator integrations need their own pinned native SDK
composition, supported operations and execution evidence. General provider
bindings and a connection to middleware do not establish those capabilities.

Native v2 scenario/runtime/observation/result formats cover the documented
software and recorded-observation path. Runtime inputs precede execution;
assessment context and captured measurement windows are separate from the
original run. V1 formats retain their ROS-oriented fields and semantics.
The [compatibility reference](../packages/harness/docs/compatibility.md) defines
this support boundary.

The source [evaluator trust SDK](../packages/harness/docs/evaluator-trust.md)
authenticates wheel provenance and binds installed source bytes to the
authenticated wheel. The source CLI requires an external operator profile and
executes captured authenticated source through the retained import guard.
The limited author fixture exercises the installed CLI with read-only inputs
in Docker and rootless Podman. These interfaces are absent from published harness
0.21.0. Production SDK/image/BOM composition admission, package publication and
native evaluator-method qualification remain separate gates.

Independent archive re-evaluation, distributed recovery and new deployment
profiles remain outside the current implementation. Physical v2 qualification
and cross-clock conversion are outside the native archive path. No future design
described here changes the meaning of historical signed documents or recorded
run outcomes.

For implemented interfaces, use the [current guide](../README.md),
[architecture reference](architecture.md) and
[compatibility reference](../packages/harness/docs/compatibility.md).
