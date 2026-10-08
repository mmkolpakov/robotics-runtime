# Architecture diagrams

[workspace.dsl](workspace.dsl) is the shared C4 model for `robotics-runtime` and
`robotics-runtime-infra`. A C4 container is a running application or data store,
not a Python package or Docker image.

- [Context](generated/Context.svg): users, product ownership and external systems.
- [Container](generated/Container.svg): execution, retained evidence and the optional Test API.
- [Native interfaces](generated/NativeInterfaces.svg): selected SDK, simulator and media paths.
- [Consumer interfaces](generated/ConsumerInterfaces.svg): host, documents and evaluation.
- [External Test API](generated/ExternalTestAPI.svg): identity, metadata, uploads and custody.
- [Complete graph](generated/ContainerDetail.svg): all declared interfaces.
- [Local execution](generated/ExecutionDeployment.svg): admitted files and owned Engine/Compose jobs.
- [Development example](generated/DevelopmentDeployment.svg): one Linux/WSL CPU deployment.

The README starts with Container; detailed views are linked separately. Colors
identify responsibilities, not qualification verdicts. Deployment examples do not
establish every provider combination or GPU capability. Ansible, Terraform and
Kubernetes responsibilities are defined in the
[infra architecture](https://github.com/mmkolpakov/robotics-runtime-infra/blob/main/docs/architecture.md).
A Windows diagnostic does not establish a Compose-controlled Windows worker.

[Sequence](run-sequence.mmd) shows `RunOwner`, consumer callbacks and the separate
evaluator. `beginMeasurement()` changes phase; the consumer starts its workload
and recorder. [State](run-state.mmd) shows retained export and cleanup behavior.
A deadline requests cancellation; an active callback blocks dependent work and
tracked cleanup until it settles. Explicit recovery resumes unattempted stages
and preserves earlier errors. Reservations are process-local; terminal cleanup
retry and crash recovery are not supported.

Callbacks must persist and verify payloads before returning references. The host
checks returned descriptors; public contracts and qualification checks validate
the referenced documents and bytes. Storage does not sign or verify evidence.
An ephemeral fixture signature proves integrity, not trusted publisher identity
or safety certification. See the [architecture reference](../architecture.md)
and [host API](../../host/README.md) for these boundaries.

## Rendering

Edit DSL/Mermaid sources, not generated SVGs. [render.sh](render.sh) uses pinned
Structurizr and Mermaid CLI images, with the shared [theme](mermaid-config.json).
No custom graph-layout renderer or SVG postprocessor is maintained.

```bash
CONTAINER_ENGINE=podman docs/architecture/render.sh
python3 docs/architecture/publish_readme.py --check
```

The default engine is Docker. Rendering embeds the generated Container and
Context views into README and checks source synchronization. Review each changed
view for readable labels, arrow directions and qualification boundaries.
