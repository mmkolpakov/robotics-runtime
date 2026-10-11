# Architecture

## Repository boundaries

`robotics-runtime` owns contracts, evidence evaluation and the composition host.
`robotics-runtime-infra` owns worker environments, simulator providers, deployment
and qualification. Product repositories supply their own robots, scenes,
controllers, cameras and vision models.

The two Python packages keep independent public versions. A host release and an
infra release have their own identities. A package install, source integration
test and published consumer run establish different claims.

## Composition and native data

### Composition framework

The host uses upstream [Cordis](https://github.com/cordiverse/cordis) `Context`,
`Service`, plugins and `Fiber` lifecycle. Providers register services within
run-owned contexts; the host reuses upstream plugin loading and managed effects.
Pinned versions and the lifecycle API are documented in the [host reference](../host/README.md).
Cluster scheduling belongs to the deployment backend.

Local context and effect management does not qualify simulator behavior,
stable retained payloads or physical cleanup. Those require provider-specific
observation and qualification. Run reservations are process-local; this lifecycle
does not provide crash or distributed recovery.

### Native data

Application services connect bounded jobs to the existing contracts/harness APIs.
They do not implement another document validator, wire protocol or simulator SDK.

Native data stays in its native path:

- control clients use generated MAVSDK Core/Action/Telemetry interfaces;
- camera consumers use the declared media endpoint, such as RTSP/GStreamer;
- simulator workers use their engine's controller, stepping and sensor APIs;
- evaluators consume retained files and exact references.

The common host and Python document workers install without ROS. The v1
scenario, runtime, observation and result formats retain required ROS graph,
lifecycle and timing fields. Their semantics remain unchanged.

The opt-in v2 formats describe native software and recorded observations through
explicit profile bindings and retained ArtifactRef bytes. Runtime configuration
is a pre-run input; completed observations are separate evidence. Results bind
the original execution separately from the assessment method, environment and
time. Explicit assessment controls select a method without replacing the original
scenario or runtime. Qualification-bundle.v2 retains the original outcome and the
new assessment, with an explicit covered-assertion comparison rule. A measured
zero, inapplicability, an absent observation and an invalid
measurement have distinct states. Missing required coverage is incomplete.

Native command acceptance, final state and postcondition observations remain
separate profile facts. The core evaluator does not add SDK control operations.
V2 physical qualification and v1 transport evaluation with v2 profiles are
unsupported. Each native SDK integration needs its own accepted operations and
profile; a middleware connection alone establishes no autopilot control path.
The ROS observer remains attach-only; the provider/controller owns simulation changes.

## External API compatibility

The optional [external Test API](external-test-api.md) supports a limited
MIT [SignalFlag SDK 1.8.0 recipe](https://github.com/resim-ai/open-core/tree/sdk-v1.8.0/signalflag/sdk).
The client supplies an endpoint, JWT and existing project/branch. Six REST
operations accept batches, tests, emissions and opaque uploads; the configuration
mutation stores bounded immutable snapshots through Mercurius/GraphQL.js.
Batch creation pins the branch snapshot. The SDK provides no snapshot ID between
sync and batch creation, so concurrent callers cannot bind their own last upload.

Fastify verifies JWTs with jose. PostgreSQL enforces tenant/project RLS; versioned
S3 retains exact upload bytes. Existing public Jobs invoke custody CLIs to verify,
sign and write receipts, preserving checkpoints across retries. Producer-reported
results remain metadata: this service neither launches a native run nor evaluates
metrics or produces a qualification verdict. Liquid templates are not executed.

The [API reference](external-test-api.md) defines supported operations, limits and
failure behavior. This source service has no published API image. It does not
implement the vendor's closed backend, full SDK parity, an SLA or certification.
Core installation and offline evaluation need no vendor account.

## Agent access

The optional [offline MCP source package](../mcp/README.md) exposes six read
tools through the maintained SDK's stdio transport. Trusted local bootstrap
registers immutable artifact IDs and installed public workers. Public host
`Jobs`, `Documents` and `Evaluation` services delegate to the published
contracts/harness CLIs; payload JSON stays text. The adapter has no published
MCP artifact and does not launch observations or evaluators.

Stdio uses local operator trust. HTTP/OAuth, a live run catalog and start/cancel
tools are not implemented. Future effects must request real admitted consumer
operations and preserve capture, drain, export and verified cleanup. Disposing
a Fiber is not a generic cancellation API.
A Web UI is outside the current product surface.

## Simulator providers

Each provider declares its source/runtime/assets, supported environment, native
endpoints and qualification scope. The common lifecycle manages acquisition and
release; it does not add common `setPose`, `step` or flight-control RPCs.

- Gazebo ROS profiles use a supported ROS/Gazebo pair and upstream
  [simulation_interfaces](https://github.com/ros-simulation/simulation_interfaces).
  A ROS-free Gazebo/PX4 profile keeps native Gz Transport and MAVSDK.
- Webots uses its native external controller and `Robot/Supervisor` API.
  Controller camera capture does not imply RTSP or a PX4 bridge.
- Isaac uses native application, physics, rendering and camera-streaming APIs.
  Its GPU/runtime requirements and NVIDIA asset licenses remain local to its
  provider. Isaac Sim and Isaac Lab are separate products.

Native SDF, WBT/PROTO and USD scenes retain their own identities and parameters.
URDF import and OpenUSD assets do not provide a portable physics/controller
contract. There is no automatic scene translator or promise of pixel/trajectory
equivalence.

## Readiness and time

Importing a plugin, resolving its services, connecting a transport, connecting a
device and observing an operation are separate checks. Required pending services
and missing runtime facts cannot be replaced with declaration defaults.

Feature discovery describes advertised support. Qualification checks the actual
operation for the pinned version and environment. A simulator's frame update is
not assumed to be one physics step.

Runs declare time authority; each selected profile records the clock facts it
actually uses. Wall deadlines, physics time, render time and capture time remain
distinct. Reset begins a new simulation epoch. Floating-point seconds are not
reported as exact integer nanoseconds.

V2 UTC provenance timestamps use exact RFC3339 nanosecond parsing. Measurement
windows carry captured integer bounds, a clock declaration and timestamp encoding;
assessment windows must use that same clock and lie within the source window.
The built-in OTLP metric method uses unix_ns. A selected SDK/product assessment
may use native_ns; it does not acquire an invented UTC relation. UTC provenance
start/finish dates do not define a simulation or device measurement epoch.

Coordinate conventions are explicit. ROS profiles follow REP-103/105; native
stage units, world axes and camera axes are retained with their evidence.

## Ownership and retained evidence

One run owns its plugin bindings and acquired workers, subscriptions and
connections. Trusted immutable configuration supplies executable plugins.
Scope isolation is not a security sandbox and disposal cannot reverse physical
actions.

![Run API and consumer callbacks](architecture/generated/run-sequence.svg)

[State and recovery source](architecture/run-state.mmd), and the
[C4 model and deployment view](architecture/README.md).

Export precedes destructive reset/stop. A standard `STOPPED` state may reset
simulation state; it is not synonymous with process disposal. Cleanup is verified
from real process/container/stream outcomes, independently of a resolved plugin
disposer. Failed export retains resources for explicit recovery. A cleanup failure remains
visible even when disposal returns. The consumer invokes the evaluator separately
after receiving the lifecycle report; a lifecycle outcome is not a qualification
verdict.

## Qualification boundaries

Package integrity, external installation and native execution are separate
checks. Qualification belongs to an exact provider, asset set and environment;
a diagram or successful package install does not establish it.

Qualification separates physics-only execution, offscreen sensor rendering and
visual review of real frames. Desktop GUI is an additional deployment capability.
A headless camera stream does not qualify a desktop GUI.

A consumer can select Webots or Isaac bindings without installing Gazebo or ROS
in the common host/evaluator. That composition choice does not establish a full
public native verdict. The provider's documented profile must supply the actual
observations and qualified source/runtime/assets. Unsupported capabilities,
wrong assets, cancellation, missing facts and foreign-resource isolation are
explicit failures.

The [native archive example](../packages/contracts/consumer-examples/minimal-native-archive/README.md)
covers a software counter and a discrete counter simulation through installed
public CLIs. It preserves original bytes and checks JSON/JUnit, aggregation and
qualification links. This scope does not qualify physical execution, a simulator
SDK or camera rendering. The source [archive assessment path](../packages/harness/docs/archive-assessment.md)
adds a distinct method and bundle2 comparison. Its authenticated author fixture
checks captured counter/offset arithmetic through public CLIs with read-only
inputs; it does not qualify physical calibration.

The initial flight reference is stock PX4/Gazebo. General Webots/Isaac provider
support does not qualify drone dynamics, a vision model, physical actuation,
GPU/NPU inference or HIL.
