# Product artifact roles

These two additive roles are registered in the working `v1` catalog for the next
release. Existing roles retain their schemas. They use the usual offline
`validate_document`, `validate_role`, `schema_path`, `schema_registry`, and CLI
`validate`/`describe` interfaces; no separate CLI writer is required.

## Execution trust policy

Role `execution_trust_policy` selects `execution-trust-policy.v1`. Its fields
match infrastructure's `policy/execution.rego`,
`config/authorization/trust-policy.example.json`, and the `trust_policy` input in
`test/policy/execution/valid.json`:

| Field | Contract |
| --- | --- |
| `policy_id` | Common contract identifier. |
| `max_permit_lifetime_seconds` | Integer from 1 through 1800, inclusive. |
| `principals[]` | `{role, identity, issuer}`; role is `operator` or `approver`, identity uses the common principal primitive, issuer is an absolute HTTPS URI. At least one principal of each role is required; `(role, identity)` pairs must be unique. |
| `targets[]` | `{target_id, identity_kind, identity_sha256, environments}`; a nonempty allowlist. |
| `targets[].identity_kind` | The existing permit identity kinds: `udev_serial`, `pci_device`, `mavlink_system_component`, `x509_spki`, `tpm_ek`, `vendor_soc`. |
| `targets[].identity_sha256` | Common lowercase, unprefixed, 64-character SHA-256 of the target identity evidence bytes. |
| `targets[].environments` | Nonempty, unique subset of `hil` and `real_robot`. |

Unknown fields and exact duplicate principal/target entries are rejected.
Public `validate_document`, `validate_role`, and CLI validation also reject
repeated `(role, identity)` pairs with different issuers. Infrastructure selects
exactly one issuer by that pair; listing both old and new issuers during a
migration would prevent that principal from executing. This key uniqueness is
a semantic check: JSON Schema's `uniqueItems` only detects whole-object duplicates.
The diagnostic is `semantic.validation_failed` at `$.principals`.
Multiple operators, approvers, and target records are allowed; distinct records
may authorize different identities or environments for a target. An identity may
appear once in each role, with the same or different issuers. Role/issuer
and target-kind/environment constraints reference the existing verification and
permit schemas, while shared identifiers and digests belong to `common.v1`.

The schema requires both roles; public validation ensures each role/identity pair
selects one issuer. Infrastructure's authorization
step remains responsible for two distinct verified signers, current time,
permit lifetime, target and environment matching, and the observed runtime,
scenario, and subject digests. A valid policy alone authorizes no execution.
There is no policy self-digest, hardware scope, permit, or signature bundle in
this document. The permit/verification's `trust_policy_sha256` binds the **whole
policy file's exact bytes**. Do not substitute a canonicalized JSON digest.

The infrastructure example is retained as a shape-compatibility fixture. Its
repeated example target hash is not proof of a physical identity. The separate
[consumer example](../consumer-examples/execution-trust-policy/trust-policy.json)
uses the actual SHA-256 of its checked-in synthetic identity evidence file.
Deployment must replace example identities with reviewed, measured identities.

## Robot description

Role `robot_description` selects `robot-description.v1`. It describes an artifact
exported by CAD, rather than embedding or validating URDF/SDF contents. The
product root is the directory containing `sim/` and `ros/`; a manifest normally
lives at `sim/robot-description.json`. **All `path` fields are relative to that
product root, not to the manifest or description package.**

| Field | Contract |
| --- | --- |
| `robot_id` | Common identifier, independent of robot hardware or product family. |
| `source` | Exactly one of `path` (local CAD source artifact) or `uri` (absolute source artifact URI), plus required `sha256`. Optional `revision` is a full 40-character Git revision. The revision never replaces the file hash. |
| `package` | `{name, path}`: lowercase ROS package name and the directory containing `package.xml`. |
| `description` | `{format, path, sha256}`; format is `urdf` or `sdf`, identifying the ready-to-load XML file. Expand Xacro and hash the resulting URDF first. |
| `meshes[]` | `{path, sha256}` for each external mesh artifact. Empty is allowed for analytic geometry. Coordinates are in metres; convert CAD units when exporting. |
| `mass_kg` | Positive finite total robot mass in kilograms. |
| `center_of_mass_m` | Three finite numbers `[x, y, z]` in metres, in the description's root-link/model frame. |
| `inertia_check` | `{status, detail?}`, where status is `passed`, `failed`, or `not_checked`; detail is a nonempty explanation when supplied. This records the producer's check outcome. |
| `spawn` | `{frame, pose}`; frame is a relative frame name, optionally slash-separated. Pose is six finite numbers `[x, y, z, roll, pitch, yaw]`, metres and fixed-axis RPY radians, relative to that frame. |

Paths use forward-slash-separated ASCII letters, digits, underscores, hyphens,
and dots. Empty, absolute, drive-qualified, URI, dot/parent-segment, and
backslash paths are invalid. `source.uri` is an absolute URI, not a path or a
relative URI reference; `file:`, HTTPS, and other artifact URI schemes are
permitted. Validation never fetches a URI or reads a referenced file. Consumers
resolve paths within their chosen product root, enforce containment after
symlink resolution, and compare SHA-256 against **unmodified file bytes**.

The schema checks structure, scalar types, and finite geometry values. It does
not parse XML, execute CAD/Xacro, verify meshes, recompute mass/inertia, or
establish safe spawning. A `failed` or `not_checked` producer check remains a
valid record, not an approval to run. Consumer admission must establish its own
requirements. No extra semantic validator is needed for this artifact boundary.

The checked-in [product example](../consumer-examples/robot-description) contains
a neutral 0.1 m cube, CAD source, a metre-scaled OBJ, and ready URDF/SDF manifests.
Tests check its file hashes, XML formats, package name, and URDF mass/inertia.
The `source`, `package`, and `inertia_check` subfields and pose representation
above make SPEC §2.5's artifact interface concrete; there is no existing CAD
robot-manifest producer being silently reinterpreted.

Runtime/scenario workload bindings, robot-description digest fields in those
existing roles, flight-controller enums, and infrastructure spawning are later
integration steps. They are not introduced by this role addition.
