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

Neutral scenario/runtime/result formats, authenticated installed evaluator bytes,
independent archive re-evaluation, distributed recovery and new deployment
profiles require their own implementation and acceptance. Current v1 interfaces
retain their existing ROS-oriented semantics. No future design described here
changes the meaning of historical signed documents or recorded run outcomes.

For implemented interfaces, use the [current guide](../README.md),
[architecture reference](architecture.md) and
[compatibility reference](../packages/harness/docs/compatibility.md).
