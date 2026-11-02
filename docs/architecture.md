# Architecture

This document describes the target architecture shared by robotics-runtime and
robotics-runtime-infra. The [package references](../README.md#start-with-the-part-you-need),
[host reference](../host/README.md) and [compatibility reference](../packages/harness/docs/compatibility.md)
describe available interfaces and their scope. The diagrams describe intended
responsibilities; they do not establish that an interface has been released or
that a particular execution profile has been qualified.

## Product and repository boundaries

The platform supports self-hosted, reproducible tests of robotic software.
Product repositories provide the robot, scene, controller and workload. Runtime
infrastructure supplies execution environments and profile-specific producers.
The runtime supplies document contracts, observation and evaluation tools, and
composition facilities. Operators choose deployment, trust roots and retention.

Prefer configuring a maintained tool, then composing its standard CLI or
runtime. Add a small domain adapter for uncovered semantics, contribute reusable
improvements upstream where practical, and own an implementation only for a
specific remaining need. A limitation of a ready tool does not automatically
justify a second subsystem. Avoided future implementation and maintenance count
when comparing the whole cost of a solution.

A consumer can validate documents or inspect a retained archive without starting
a simulator, Node host or container engine. An assessment of a custom method
may require its own execution environment. Validating a stored verdict and its
evidence is distinct from independently recomputing that verdict.

## Attempts and campaigns

A finite attempt has one owner for admission, acquired resources and lifecycle.
The owner binds the request to a unique attempt and a trusted profile, starts
the selected native workload, records observations, closes the measurement
window, captures final state and drains producers. It exports and verifies retained
evidence before destructive cleanup, then reports the observed cleanup separately
from the native operation and the acceptance verdict.

A timeout or lost acknowledgement can leave the native outcome unknown. An
unknown effect does not authorize an automatic replay. Recovery operates on the
stopped or settled attempt and retained data; foreign or ambiguous resources
are not cleaned up by name alone. A finite supervisor applies deadlines and,
where supported, bounded termination and escalation to owned processes. It
preserves closed bytes and partial diagnostics in a durable attempt record when
work cannot settle in time. The attempt may end with recovery left for an
operator; this is not evidence that a physical action stopped. Active dependent
work and foreign resources are not destructively cleaned up.

Cancellation requests, operation completion, resource disposal and physical
stopping are separate facts.

An external campaign system orders attempts and handles campaign history,
scheduling and permitted retries. The local profile uses Dagu; the Kubernetes
profile uses Argo Workflows. They are alternatives at the same boundary, not
layers in one attempt. A campaign retry must not silently repeat a native effect.
The attempt owner retains native admission, capture, export and cleanup
responsibilities. Kubernetes resource identity and retained storage survive
independently of campaign status and workflow garbage collection. Terraform
provisions the selected infrastructure, Helm describes Kubernetes workloads and
retained storage, and Ansible configures enrolled product hosts. The
[infra architecture](https://github.com/mmkolpakov/robotics-runtime-infra/blob/main/docs/architecture.md)
defines those deployment responsibilities.

### Composition framework

A selected implementation can use the existing
[Cordis host](../host/README.md) for in-process bindings, finite jobs and
resource lifecycle. Cordis types are not required at the external consumer
boundary. A local process supervisor bounds the process; it does not by itself
own all containers or prove physical stopping. A different consumer can supply
the same evidence and lifecycle facts without embedding this host.

## Native interfaces

Control, telemetry and media use the selected native SDK and data plane.
Workers may use ROS 2 and Nav2, MAVSDK for PX4, or the native simulator
interfaces for Gazebo, Webots and Isaac. Media consumers use their native
pipeline, such as GStreamer and a declared camera or RTSP source. MCP and
document contracts do not carry control loops, physics steps or video frames.

Native models, assets, transport, coordinate conventions and clocks remain
specific to the profile. The platform does not define a universal simulator
control API or translate scenes between engines. A command acknowledgement,
observed terminal state and independent postcondition are distinct observations.
Connection, readiness and a successful operation are also separate facts.

## Contracts, time and retained evidence

The contracts catalog defines document roles and versions. Scenario and runtime
inputs describe what is admitted before an attempt; observations and evidence
record what happened. Native v2 documents distinguish the original execution
from a later assessment, including its method, environment, time and calibration.
Absent, inapplicable, invalid and measured-zero values remain distinct; missing
required coverage yields an incomplete assessment.

Retained files preserve their original bytes, digests, references and signatures.
A portable package can bind original identities to locations on another machine
without rewriting signed documents. Receipt inventories identify the related
receipt, verification and dependency files; they are not a second role catalog.
The producer seals files before capture and supplies exact references. Strict
evidence custody must preserve its containment and mutation protections.

A run declares its time authority, measurement windows and timestamp encoding.
Wall deadlines, simulation epochs, capture time and assessment time are not
interchangeable. Native seconds are retained in their declared representation;
an unspecified relation to UTC is not invented. Coordinate frames and units
are recorded with the selected profile.

## Evaluation and trust

The harness validates the supplied evidence and runs its built-in methods. It
owns coverage and the final status, including incomplete and error outcomes.
External product methods return assertions tied to verified evidence, not a
replacement verdict. The harness checks assertion namespace, unique identifiers,
evidence references and calibration bindings before combining results.

The target external-method boundary is a finite process in an admitted OCI image.
The operator selects an external trust policy. The harness checks the actual
platform manifest and uses stock Cosign for image admission. It verifies captured
input bytes and owns finite execution and bounded raw-response capture. The
container runtime enforces read-only input mounts, resource limits and isolation
from the network, host devices and engine sockets. A versioned JSON exchange
carries the existing assessment facts and assertions. Original execution identity
and the new assessment remain distinct. Image provenance does not prove that a
method or physics model is correct.

Previously signed wheel-profile inputs and results retain their original
semantics and can be assessed with their pinned published tools. They are not
rewritten to impersonate an OCI method. Built-in assessment and verification of
retained archive bytes remain usable without an OCI runtime; recomputing a custom
OCI method requires its admitted execution environment.

## Agent and API access

The offline MCP adapter exposes read operations over registered artifacts and
the public document tools. It does not turn a tool response into a physical
outcome. Campaign and long-running interfaces address admitted operations and
return handles whose status remains distinct from the final evidence verdict.
Waiting, cancellation and native stopping have separate semantics.

The optional external Test API receives producer metadata and retained uploads;
it is not the owner of a native attempt or a qualification verdict. Its
[reference](external-test-api.md) describes the implemented compatibility
surface. [Agent integration](agent-integration.md) describes user and agent
interactions across these boundaries.

## Qualification

Source integration, published artifacts and native execution establish
different claims. Each execution profile is assessed against its exact
software, assets, environment and observed operations. Physics, offscreen
sensor rendering, media and desktop interaction have separate evidence.
An installed package, a diagram or a connected SDK alone does not establish
the outcome of a native run.

[Architecture diagrams](architecture/README.md) show the context, composition,
deployment and lifecycle described here.
