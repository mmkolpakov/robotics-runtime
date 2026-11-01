# Architecture diagrams

The [architecture](../architecture.md) defines the target model. The views in
[workspace.dsl](workspace.dsl), [run sequence](run-sequence.mmd) and
[run state](run-state.mmd) describe its responsibilities, not a release or
qualification claim. For available commands and SDK interfaces use the
[package references](../../README.md#start-with-the-part-you-need) and
[host reference](../../host/README.md).

- [Context](generated/Context.svg) shows users, the platform and native systems.
- [Composition](generated/Container.svg) shows campaign orchestration, a finite
  attempt, document evaluation, offline MCP and retained evidence.
- [Native interfaces](generated/NativeInterfaces.svg) separates SDK control and
  media from the document path.
- [Consumer interfaces](generated/ConsumerInterfaces.svg) shows the external
  attempt boundary and independent evidence evaluation.
- [External Test API](generated/ExternalTestAPI.svg) shows producer metadata and
  custody; it does not own native execution.
- [Complete graph](generated/ContainerDetail.svg) includes the modeled paths.
- [Local execution](generated/ExecutionDeployment.svg) and
  [Kubernetes execution](generated/DevelopmentDeployment.svg) illustrate
  deployments. The local and Kubernetes campaign profiles are alternatives.
- [Sequence](generated/run-sequence.svg) and [state](generated/run-state.svg)
  show evidence-before-cleanup and independent evaluation.

A C4 container is an application or data store, not a Python package or an OCI
image. Native process, GPU-memory and IPC boundaries depend on the selected
profile. Provisioning is described in the
[infra architecture](https://github.com/mmkolpakov/robotics-runtime-infra/blob/main/docs/architecture.md).

## Rendering

Edit DSL and Mermaid sources, not generated SVGs. [render.sh](render.sh) uses
pinned Structurizr and Mermaid CLI images with the shared
[theme](mermaid-config.json). From the repository root:

```bash
CONTAINER_ENGINE=podman docs/architecture/render.sh
python3 docs/architecture/publish_readme.py --check
```

Review generated views for readable labels, arrow directions and consistency
with the architecture.
