# Evidence byte-check evaluator

This is a minimal standalone evaluator author example. It declares a standard
PyPA entry point and imports only public SDK modules. Its method checks that one
indexed JSON artifact named `native-state` has nonempty verified bytes. An explicit
assessment can additionally check a captured integer offset against the raw counter.
Neither method is a robotics, performance, physics or safety qualification.

The execution profile supplies the matching SDK, including the public
`VerifiedEvidence.read_local` capture API. Published harness 0.21.0 does not supply
that API or the wheel-authentication module. It cannot execute this author path.
Package publication and profile qualification must identify an SDK artifact that
implements both interfaces.

Build with the normal project backend:

```bash
uv build --wheel
```

The wheel contains no startup hook, native module, console wrapper or `.data`
transformation. Before installation, the trusted integrator obtains the released
wheel, signed bundle and externally approved publisher/tool/root policy; calls
`authenticate_wheel` and `validate_evaluator_wheel`; and installs a private copy
of the captured wheel bytes with ordinary pip. It then calls
`verify_installed_wheel` and retains the captured source/entry-point bindings for
the existing verified-source loader. See
[the SDK trust reference](../../docs/evaluator-trust.md).

The original scenario/runtime or selected assessment controls bind namespace
`org.example.evidence-bytes`, target
`evidence_byte_check:evaluate`, distribution `example-evidence-byte-check`,
version `0.1.0`, and the exact released wheel/receipt digests. Synthetic or
locally invented verification JSON is not publisher evidence.

The author profile mounts the original indexed `native-state` JSON input read-only and limits
capture to 1 MiB. The evaluator calls `read_local` once and uses the resulting
immutable bytes. Each assertion references the digest of that verified artifact.
Unknown paths, tampering or over-limit inputs fail through the public reader.

Run third-party code in the reviewed limited process/image profile. This example
does not install a sandbox, launch a workload, mutate evidence, import private
SDK helpers or modify the runtime core. Its source and byte-count result are
separate from a published, qualified execution composition.

For the offset method, explicit assessment controls declare calibration as
`selected` with one local JSON ArtifactRef containing an integer `offset`.
The method reads that input through `AssessmentControls.read_input`, reads the
registered original `native-state` bytes through `VerifiedEvidence.read_local`,
and tests `counter - offset == 0`. Its assertion binds both actual byte digests.
It never reopens the calibration URI. A selected reference alone does not prove
that a method applied a calibration.

The limited installed-CLI fixture records counter 7 and a failed original core
assessment. Captured offset 7 gives a new passed numerical assertion with value
0; offset 6 gives failed/value 1; explicitly unobserved calibration gives
incomplete/skipped; a non-integer offset gives error. These are distinct
assessment result IDs, with the original result SHA retained. Original trial,
controls, calibration and baseline result files are mounted read-only at their
recorded paths. The fixture checks write refusal and unchanged bytes.

The core metric method has no calibration implementation and rejects selected
calibration. This example does not establish sensor calibration accuracy, native
hardware timing or physical acceptance. Its SDK/control APIs belong to the
selected source composition and are absent from published harness 0.21.0.
