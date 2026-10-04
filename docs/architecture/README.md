# Architecture diagrams

The model covers the joint platform implemented by `robotics-runtime` and
`robotics-runtime-infra`. The separately published Python packages are libraries
and CLI applications, not additional software systems.

[workspace.dsl](workspace.dsl) is the C4 source. Context shows users and external
systems. Container shows executable applications and the retained data store;
a C4 container is not a package or a Docker image. Deployment maps these
applications onto the existing home environment. Dashed candidate elements
have not passed the full released consumer gates.

[run-sequence.mmd](run-sequence.mmd) describes the source `RunOwner` API and
consumer-supplied completion callbacks. The consumer starts its workload and
recorder; `beginMeasurement()` only changes the lifecycle phase. It also invokes
the Python evaluator after receiving the lifecycle outcome. These two outcomes
are distinct.

[run-state.mmd](run-state.mmd) shows export retention and cleanup states.
A callback must persist and verify its payloads before returning references.
The host checks that export returns references; it does not validate every
referenced file itself. Contracts and qualification checks validate the
retained documents and bytes.

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
