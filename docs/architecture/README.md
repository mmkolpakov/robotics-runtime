# Architecture diagrams

The model covers the joint platform implemented by `robotics-runtime` and
`robotics-runtime-infra`. The separately published Python packages are libraries
and CLI applications, not additional software systems.

[workspace.dsl](workspace.dsl) is the C4 source. Context shows users and external
systems. [Container](generated/Container.svg) shows the owned process composition
and retained data. [NativeInterfaces](generated/NativeInterfaces.svg) isolates
SDK, simulator and media dependencies;
[ConsumerInterfaces](generated/ConsumerInterfaces.svg) shows product and
document/evaluation ownership. [ContainerDetail](generated/ContainerDetail.svg)
keeps the complete graph for reference. A C4 container
is not a package or a Docker image. The
[local execution view](generated/ExecutionDeployment.svg) shows the selected
native-worker path, admitted read-only inputs and owned Engine/Compose jobs.
The [home deployment view](generated/HomeDeployment.svg) maps the broader source
composition onto WSL. Candidate wording and role colors distinguish source
components from the published Python packages; neither is a passed verdict.
Box and arrow labels are kept
short for README display; [the architecture reference](../architecture.md) and
[host reference](../../host/README.md) describe native endpoints, producer
verification, frame ownership, release scope and infra-supplied environments.
Native Windows standalone
diagnostics are separate from this route: they do not establish Compose control
or evidence transport between WSL and a Windows worker. Product Ansible and
Terraform provisioning sources live in infra; real AWS/EKS execution and
application qualification remain separate gates. This view does not qualify
the complete composition: installed Webots CPU lifecycle and byte-retention
checks, ROS evaluation, media fixtures and real camera/GPU paths have separate
acceptance evidence. Generic boxes do not imply that every combination passed.

[run-sequence.mmd](run-sequence.mmd) describes the source `RunOwner` API and
consumer-supplied completion callbacks. The consumer starts its workload and
recorder; `beginMeasurement()` only changes the lifecycle phase. It also invokes
the Python evaluator after receiving the lifecycle outcome. These two outcomes
are distinct.

[run-state.mmd](run-state.mmd) shows export retention and cleanup states.
A callback must persist and verify its payloads before returning references.
The host checks that export returns references; it does not validate every
referenced file itself. Contracts and qualification checks validate the
retained documents and bytes. Failed or empty export, including an explicit
startup recovery attempt, keeps the run retained. A deadline bounds the caller
and requests cancellation; an unsettled managed producer blocks later stages,
export and tracked resource cleanup. After settlement, explicit recovery
continues unattempted stages. Destructive cleanup requires a successful export
with nonempty descriptors. Enclosing context disposal can still consume Cordis
teardown; terminal cleanup retry and crash recovery are not supported.

The sequence keeps lifecycle completion separate from public qualification.
The existing [post-cleanup coordinator](https://github.com/mmkolpakov/robotics-runtime-infra/blob/main/host/workers/legacy-finalization/README.md)
packages and signs retained evidence,
then independent portable verification checks it. An ephemeral fixture key
proves integrity; trusted producer identity requires an independently accepted
publisher and signing policy. Storage itself neither signs nor verifies data.

The runtime README starts with Container and keeps Context under disclosure.
The infra README starts with local execution and links to the shared C4 views.
Add Sequence when ordering
changes behavior, State when recovery matters, and Deployment when a supported
environment has a material constraint. Backend-specific native calls belong
in provider documentation. Component and class diagrams are not required for
every module.

Render with the pinned upstream tools in [render.sh](render.sh). Structurizr
exports the authoritative C4 model to Mermaid; the pinned Mermaid CLI renders
SVG files with the shared [theme](mermaid-config.json). The same generated
Container and Context definitions are embedded into README by
[publish_readme.py](publish_readme.py). GitHub renders these blocks with its
standard diagram controls. No geometry or graph-layout renderer is maintained
here. Generated views are derived assets; edit the source instead.

Colors identify roles, not accepted execution scopes: composition, published
Python tools, native candidates, media and retained files. Short labels keep
the entry views readable; native endpoints and scope limits remain in the
reference pages and the full interface graph.

After rendering, check README synchronization with:

```bash
python3 docs/architecture/publish_readme.py --check
```

On Linux, run `docs/architecture/render.sh` from any directory. On the declared
rootless Podman environment, set `CONTAINER_ENGINE=podman`. The script uses
pinned image digests and produces review assets without installing host tools.
