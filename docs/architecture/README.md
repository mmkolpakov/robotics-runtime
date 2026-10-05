# Architecture diagrams

The model covers the joint platform implemented by `robotics-runtime` and
`robotics-runtime-infra`. The separately published Python packages are libraries
and CLI applications, not additional software systems.

[workspace.dsl](workspace.dsl) is the C4 source. Context shows users and external
systems. [Container](generated/Container.svg) shows the owned process composition
and retained data; [ContainerDetail](generated/ContainerDetail.svg) keeps the
complete consumer, controller, simulator and media interface graph. A C4 container
is not a package or a Docker image. Deployment maps these
applications onto the source WSL CPU topology. Dashed candidate elements
have not passed the full released consumer gates. Box and arrow labels are kept
short for README display; [the architecture reference](../architecture.md) and
[host reference](../../host/README.md) describe native endpoints, producer
verification, frame ownership, release scope and infra-supplied environments.
Native Windows standalone
diagnostics are separate from this route: they do not establish Compose control
or evidence transport between WSL and a Windows worker. An AWS/EKS target requires
its own deployment implementation and qualification. This view does not qualify
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

Use Context and Container in repository READMEs. Add Sequence when ordering
changes behavior, State when recovery matters, and Deployment when a supported
environment has a material constraint. Backend-specific native calls belong
in provider documentation. Component and class diagrams are not required for
every module.

Render with the pinned upstream tools in [render.sh](render.sh). SVG files in
`generated/` are review assets; edit the source instead. Structurizr exports
Mermaid views for text review, but the C4 model remains authoritative.
The official Structurizr CLI and Mermaid CLI require no running diagram server.

On Linux, run `docs/architecture/render.sh` from any directory. On the declared
rootless Podman environment, set `CONTAINER_ENGINE=podman`. The script uses
pinned image digests and produces review assets without installing host tools.
