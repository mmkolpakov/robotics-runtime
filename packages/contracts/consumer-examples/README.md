# Consumer Examples

These documents form a neutral, single-domain simulation exchange. They show
how a consumer can declare a scenario, describe the observed runtime, establish
one run context, report one domain result, index evidence, and aggregate the
result.

Every YAML document declares its own `schema_version`. CI validates these
documents with the public Python API from the current editable checkout:

```bash
uv run pytest tests/test_consumer_examples.py
```

These are 0.16-generation examples. They do not establish compatibility with
infra's audited contracts 0.15.4 / harness 0.17.1 pair, and the fixture is not
a live ROS execution test. Review the
[migration guide](../docs/migrations/0.15-to-0.16.md) before adopting them.

Consumers should copy only the document types they produce or consume.
Identifiers, image references, timestamps, and ROS graph observations are
examples and must be replaced with observed data. The SHA-256 fields that link
files in `minimal-simulation/` are the actual digests of those files, and CI
recomputes the complete acyclic chain. A successful result contains evaluated
assertions and evidence; observation digests identify the corresponding item in
both the result and the evidence index.

## New product artifact examples

`execution-trust-policy/trust-policy.json` matches the allowlist consumed by
infrastructure's execution policy. Its target hash covers the exact bytes of
`execution-trust-policy/target-identity.txt`, including the final LF. The identity
is synthetic; this example is not a physical-execution permit or authorization.

`robot-description/` is a portable product root with `cad/`, `ros/`, and `sim/`.
`sim/robot-description.json` records a ready URDF and
`sim/robot-description-sdf.json` records the alternative SDF for the same neutral
1 kg, 0.1 m cube. Both bind actual CAD source and description file bytes; the
URDF also binds its external mesh. The SDF uses analytic box geometry.
The mesh is expressed in metres, while the OpenSCAD source is in millimetres.
The ROS package contains static description assets, not a CAD exporter or launch
integration. These example artifacts are authored to agree; no CAD tool was run
as part of contract validation.

From this directory, validate the examples with the existing CLI:

```bash
robotics-contracts validate execution-trust-policy/trust-policy.json \
  robot-description/sim/robot-description.json \
  robot-description/sim/robot-description-sdf.json
```

See [product artifact roles](../docs/product-artifact-roles.md) for locator rules,
units, producer-reported checks, and the boundary with later consumer integration.

The [flight controller profile](flight-controller/README.md) adds six interface
requirements using the existing extensible `flight_controller` provider kind.
Controller selection and live conformance belong to the infrastructure stages.
