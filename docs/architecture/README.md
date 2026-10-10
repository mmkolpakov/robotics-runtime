# Architecture diagrams

[workspace.dsl](workspace.dsl) models consumer-owned usage examples. It does not
treat repositories or SDK libraries as standalone deployed systems. A C4
container is an application or data store, not a Python package or Docker image.

- [Published document workflow](generated/Container.svg): terminal/CI, the
  published Python tools and retained files. This is the README starting view.
- [Context](generated/Context.svg): the consumer-owned verification application
  and the systems it can use.
- [Native consumer application](generated/NativeInterfaces.svg): a consumer
  embeds the host library and selects native SDK, simulator and media processes.
- [Embedded host and public tools](generated/ConsumerInterfaces.svg): callbacks,
  the Python tools and retained evidence.
- [External Test API](generated/ExternalTestAPI.svg): optional identity,
  metadata, uploads and custody. The SDK runs inside its client application.
- [Complete graph](generated/ContainerDetail.svg): the declared usage paths.
- [Local execution](generated/ExecutionDeployment.svg): mounted inputs,
  consumer-owned Engine/Compose jobs and retained files.
- [Development example](generated/DevelopmentDeployment.svg): one Linux/WSL
  CPU topology; it does not qualify native GPU or sensor rendering.

The document workflow needs neither a host service nor the optional API/MCP.
Native recipes have their own dependencies. Python evaluation reads supplied local
files; remote retention is represented by references and verified receipts.
The PX4 control edge names the MAVSDK server peer, not a gRPC server in firmware.
The host is a library inside the
consumer coordinator; it is not a separate daemon. Its callbacks also write
observations. Process, GPU-memory and IPC boundaries follow the selected SDK
profile rather than a universal process-per-module rule.

Colors identify responsibilities. Deployment diagrams show instances and
resources. Provisioning with Ansible, Terraform and Helm is described separately
in the [infra architecture](https://github.com/mmkolpakov/robotics-runtime-infra/blob/main/docs/architecture.md).
An execution diagram does not establish qualification for every provider
combination or safe physical-device behavior.

[Sequence](run-sequence.mmd) shows `RunOwner`, consumer callbacks and the separate
evaluator. `beginMeasurement()` changes phase; the consumer starts its workload
and recorder. [State](run-state.mmd) shows retained export and cleanup behavior.
A deadline requests cancellation; an active callback blocks dependent work and
tracked cleanup until it settles. Explicit recovery resumes unattempted stages
and preserves earlier errors. Reservations are process-local; terminal cleanup
retry and crash recovery are not supported.

Cancellation requests, native-operation completion, resource cleanup and
physical stopping are distinct. The current host observes its callbacks and
owned resources; it does not turn a process exit into a robot-stop guarantee.
Callbacks must persist and verify payloads before returning references. The
host checks returned descriptors; public contracts and qualification checks
validate the referenced documents and bytes. Storage does not sign or verify
evidence. A fixture signature proves integrity, not trusted publisher identity
or safety certification. See the [architecture reference](../architecture.md)
and [host API](../../host/README.md).

## Rendering

Edit DSL/Mermaid sources, not generated SVGs. [render.sh](render.sh) uses pinned
Structurizr and Mermaid CLI images, with the shared [theme](mermaid-config.json).
No custom graph-layout renderer or SVG postprocessor is maintained.

```bash
CONTAINER_ENGINE=podman docs/architecture/render.sh
python3 docs/architecture/publish_readme.py --check
```

The default engine is Docker. Rendering embeds the document workflow and Context
views into README and checks source synchronization. Review changed views for
readable labels, arrow directions and agreement with the actual interfaces.
