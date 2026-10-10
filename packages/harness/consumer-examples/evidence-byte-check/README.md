# Evidence byte-check evaluator

This is a minimal standalone evaluator author example. It declares a standard
PyPA entry point and imports only public SDK modules. Its method checks that one
indexed JSON artifact named `native-state` has nonempty verified bytes; it is not a robotics,
performance, physics or safety qualification.

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

The scenario and runtime bind namespace `org.example.evidence-bytes`, target
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
