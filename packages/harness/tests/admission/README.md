# Authenticated evaluator integration fixture

This fixture uses the installed public CLI and the standalone
[evidence-byte author example](../../consumer-examples/evidence-byte-check/README.md).
It verifies source integration, not a released SDK or robot performance.

The `evaluator-admission` job in [CI](../../../../.github/workflows/ci.yml) builds
the candidate SDK wheels and author wheel, then attests only the author wheel
using the existing pinned official action. The reviewed fixture supplies the
exact workflow identity, source ref/commit, signer commit and subject digest;
the attestation never chooses its own trust policy.

`prepare.py` calls the public authentication/validation API and public receipt
writer. The receipt describes the successful official verification and its
captured audit bytes. Executable admission repeats actual verification; JSON
audit records alone cannot allow imports. The native producer receives an
optional evaluator binding before creating/finalizing its input documents.
Those records and the byte-count method are synthetic method inputs.

The Dockerfile installs the approved candidate SDK, authenticates and validates
the author wheel before pip installation, and installs a private captured copy
with ordinary pip. It rejects unsupported startup/installation transforms.
The runner supplies read-only original evidence, an external read-only operator
profile and a separate assessment output mount. It uses stock Docker/Podman
resource, filesystem and privilege controls; no sandbox implementation is added
to the SDK.

The fixture pins gh 2.102.0 archive and executable hashes. The root file is the
official `gh attestation trusted-root` snapshot captured on 2026-10-10, SHA-256
`65ca537f6ed8a47fd0e560c421baa1f6c1efb8b25fc200d8c5c02c0e92eb2b9c`.
Changing either pin requires review of the operator composition. These files
are outside the evidence root. The Python 3.12.13 Linux image is pinned by OCI
digest; that pin alone does not establish its publisher or a full image BOM.

After the job prepares its artifacts, the stock container witness runs with:

```bash
docker build -f packages/harness/tests/admission/Dockerfile -t evaluator-admission:ci .
bash packages/harness/tests/admission/run.sh artifacts/evaluator-admission
```

For rootless Podman, set `CONTAINER_RUNTIME=podman`. The fixture uses a 512 MiB
memory bound, one CPU, 32 PIDs, a 256 MiB temporary filesystem and an outer
180-second deadline. It checks read-only input/profile failures, an authenticated
byte assertion, refusal without cryptographic admission or with a wrong
publisher, and exact unchanged input bytes. Results and captured audit records
are retained as CI artifacts.

Actual author authentication requires the matching genuine signed bundle.
Unit tests mock the crypto call only for independent binder/loader regressions;
they never claim those probe wheels prove publisher identity.
