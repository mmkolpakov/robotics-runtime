# Evaluator wheel authentication

The source SDK provides `authenticate_wheel`, `authenticate_wheel_with_cosign_key`,
`validate_evaluator_wheel` and
`verify_installed_wheel` in `robotics_acceptance_harness.evaluator_trust`.
These APIs are not part of the published harness 0.21.0 wheel. They verify
artifact origin and installed bytes. The source loader and CLI require these
captured bindings before importing a declared evaluator, and retain the existing
verified-source import guard.

## Operator profile and publisher policy

The GitHub and local-key profiles are explicit alternatives. There is no automatic
fallback between them, and saved verifier JSON cannot select a weaker policy.

The integrator supplies a reviewed execution composition with the Python
interpreter, SDK, dependencies, an approved `gh` executable and trusted roots.
`GitHubVerifierProfile` requires the executable's exact SHA-256, exact version
(at least 2.102.0), and the trusted-root file's exact SHA-256. Those pins come
from the approved profile/BOM, outside the evidence directory. A checksum
calculated from an arbitrary executable is not an independent approval of it.
This SDK does not download or install a verifier.

`GitHubWheelPolicy` supplies the expected repository, exact certificate identity,
OIDC issuer, predicate type and wheel SHA-256. Optional source ref, source digest
and signer digest further constrain the build. The default policy rejects
self-hosted runners. The certificate identity includes the selected workflow and
ref; `gh` treats `--cert-identity` and `--signer-workflow` as mutually exclusive.

The helper captures wheel, bundle, executable and root bytes once. It checks their
limits and profile hashes, then invokes the copied official executable on private
wheel/bundle/root snapshots. It passes the publisher and subject policy to
[GitHub attestation verification](https://cli.github.com/manual/gh_attestation_verify).
The returned report is audit output from that invocation. A caller-supplied
verification JSON, an artifact receipt, or a saved report cannot establish this
admission.

Sigstore's [verification API](https://sigstore.github.io/sigstore-python/api/verify/verifier/)
distinguishes authenticated DSSE payload bytes from artifact verification.
Cryptographic authenticity and expected publisher identity do not prove an
evaluator's method, a physical model, or a claimed result is correct.

## Private local-key signing

Closed evaluator code can stay on the owner's node. The explicit
`cosign_key_no_tlog` profile uses stock Cosign blob attestation and an independently
approved local public key. It proves a signature by the holder of that key,
the expected raw wheel SHA-256 and exact predicate URI. It does not prove OIDC
identity, transparency-log inclusion, an authenticated signing timestamp or build
provenance. Operator approval of the key and tool is outside evidence.

`CosignKeyVerifierProfile` pins the executable SHA-256, exact reported version,
public-key bytes/SHA-256 and explicit trusted-root bytes/SHA-256. It requires a
stable Cosign version at least 3.1.3; version alone is not tool approval.
`CosignKeyWheelPolicy` requires the expected wheel SHA-256, predicate URI,
public-key SHA-256 and explicit `trust_mode="key_only_no_tlog"`.
The signature bundle's embedded key information is never a trust anchor.

The [source fixture](../tests/admission/README.md) records the independently
admitted vendor tool/index/architecture/SBOM pins and exact reported build version.
Tool provenance and execution composition admission remain separate records.

The existing private publisher mechanism uses ready
[Cosign blob attestation](https://github.com/sigstore/cosign/blob/v3.1.3/doc/cosign_attest-blob.md):

```bash
cosign signing-config create --out offline-signing.json
cosign trusted-root create --out offline-root.json
cosign attest-blob --yes --key publisher.key \
  --signing-config offline-signing.json --trusted-root offline-root.json \
  --predicate evaluator-method.json --type urn:example:evaluator-method:v1 \
  --bundle evaluator.sigstore.json example_evaluator-1.0-py3-none-any.whl
```

The no-service signing configuration and explicit root keep this key-only path
local. The owner protects the private key; it is not supplied to the verification
SDK, evidence, worker image or report. The API captures wheel, bundle, tool,
public key and root once, then calls stock `verify-blob-attestation` with
`--check-claims=true`, the expected predicate and captured external key.
`--insecure-ignore-tlog` is the explicitly selected no-log policy; it is never an
automatic downgrade from the GitHub certificate policy.

A key-only operator profile uses the same top-level version 1 shape, with
`verifier.kind="cosign_key_no_tlog"`, `public_key` and
`public_key_sha256` in addition to the common tool/root fields. Its publisher
binding has exactly `wheel_sha256`, `predicate_type`, `public_key_sha256` and
`trust_mode="key_only_no_tlog"`. The GitHub profile explicitly uses
`verifier.kind="github"`; an omitted or unknown kind is refused.
Evidence document schema versions are unaffected by this operator configuration.

Both factories return the same issued in-memory wheel admission and reuse the
original wheel/installation/entry-point/source guards and limits. Local signing
does not require uploading the evaluator wheel to GitHub, and this profile does
not add a key registry, PKI service, custom cryptography or installer.

## Authenticate before installation

An operator-owned Python application constructs the profile and policy from its
reviewed configuration, then calls:

```python
from pathlib import Path
from robotics_acceptance_harness.evaluator_trust import (
    authenticate_wheel,
    validate_evaluator_wheel,
)

wheel = authenticate_wheel(
    Path("example_evaluator-1.0-py3-none-any.whl"),
    Path("evaluator.bundle.jsonl"),
    policy=publisher_policy,
    profile=verifier_profile,
)
validate_evaluator_wheel(wheel)
```

The helper validates the original PyPA wheel filename. Install a private copy of
`wheel.wheel_bytes`, retaining `wheel.filename`, with ordinary pip. Installing
the original mutable input path after verification would introduce another read
of bytes that were not captured for the installation. No `--no-compile` flag is
required by the authenticated-source profile.

The supported evaluator profile is a self-contained purelib wheel with
Wheel-Version 1.0. It rejects native/source-less code, `.data` installation
transforms, generated console/GUI wrappers and Python startup hooks such as root
`.pth`, `sitecustomize.py` and `usercustomize.py`. Check this profile before pip
installation. A helper imported after interpreter startup cannot undo previously
executed startup code; the starting interpreter and environment belong to the
approved execution composition.

## Bind installed code to the original wheel

```python
from importlib.metadata import distribution
from robotics_acceptance_harness.evaluator_trust import verify_installed_wheel

installed = verify_installed_wheel(wheel, distribution("example-evaluator"))
```

The binder uses the [PyPA wheel format](https://packaging.python.org/en/latest/specifications/binary-distribution-format/)
and [installed-file metadata](https://packaging.python.org/en/latest/specifications/recording-installed-packages/).
It checks the original wheel RECORD and compares each installed member with its
authenticated original bytes. Rewriting installed code and its local RECORD
together still fails. Installer metadata and the rewritten installed RECORD are
not authentication roots.

The supplied distribution's METADATA, WHEEL and entry-point metadata must match
the authenticated wheel metadata. `installed.entry_points` retains original
`(group, name, value)` bindings for the caller's admission checks. A loader must
compare its selected entry point with these captured bindings, not rely on a
later mutable metadata read.

The returned `paths`, `files` and `sources` hold immutable captured bytes.
Use them with the existing verified-source loader; ordinary Python import is not
a replacement for that guard. The guard remains necessary for namespace/origin,
prior-import, native and source-less restrictions. Dependencies outside the
wheel remain part of the approved interpreter/image/BOM boundary.

Extra files in the admitted namespace are rejected, including sources or native
code omitted from installed RECORD. Ordinary PEP 3147/488 caches may be ignored
only when they map to an existing authenticated Python source. Their bytes are
not read, admitted or added to the proof: the verified-source loader compiles the
captured source instead. Source-less/top-level bytecode and cache symlinks fail.
Cross-distribution shared namespaces are outside this initial profile.

The input profile requires POSIX nonblocking/no-follow regular-file opens.
Platforms without those flags are refused rather than claiming equivalent
pre-open protection.

Wheel member count, per-member and aggregate expansion, raw inputs, verifier
deadline and installed namespace/cache entry counts have explicit limits.
Verifier reports and diagnostics are checked against capture limits after exit;
the execution profile supplies live filesystem quotas and process resource bounds.
Standard ZIP/CSV readers perform the decoding; duplicate paths, traversal and
unsupported members are refused.

## CLI and SDK execution admission

The source CLI accepts `--evaluator-trust-profile PATH` on `evaluate`, `verify`
and `doctor`. The JSON file belongs to the operator, outside the indexed evidence
root, and must not be group/other writable. Relative paths resolve from its
directory. An explicit verifier kind is required. Version 1 has exactly `profile_version`,
`verifier` and `evaluators`:

```json
{
  "profile_version": 1,
  "verifier": {
    "kind": "github",
    "executable": "tools/gh",
    "executable_sha256": "<approved gh SHA-256>",
    "version": "2.102.0",
    "trusted_root": "policy/trusted-root.jsonl",
    "trusted_root_sha256": "<approved root SHA-256>"
  },
  "evaluators": [{
    "namespace": "org.example.evidence-bytes",
    "wheel": "wheels/example_evidence_byte_check-0.1.0-py3-none-any.whl",
    "bundle": "publisher.bundle.json",
    "publisher": {
      "repository": "example/evaluators",
      "certificate_identity": "https://github.com/example/evaluators/.github/workflows/release.yml@refs/tags/v0.1.0",
      "wheel_sha256": "<expected wheel SHA-256>",
      "source_ref": "refs/tags/v0.1.0",
      "source_digest": "<expected full source commit>",
      "signer_digest": "<expected full signer commit>"
    }
  }]
}
```

These placeholders require reviewed values. Every namespace must correspond
exactly to a scenario requirement; its wheel digest must match that requirement.
The operator profile is external policy, so a verification JSON in the archive
cannot choose the verifier, trust roots or expected signer. Audit receipt and
dependency inputs remain required for document consistency. They cannot issue
executable admission by themselves.

The loader matches the selected entry point to the captured original
`(group, name, value)` tuple and wheel subject/distribution/version. It compiles
captured authenticated source through the existing guard, without rereading
installed RECORD or bytecode. Both authentication result types require a
factory-issued in-memory marker; constructing, copying or deserializing a result
does not recreate admission. This protects accidental API misuse, not a Python
caller already controlling the process.

SDK callers pass `evaluator_authentications={namespace: installed}` to
`evaluate_acceptance`, `evaluate_from_evidence` or `run_verification`.
Explicit `evaluators=` injection remains a trusted application-caller path and
does not claim publisher authentication. Reading or explaining v1 documents
remains possible; executing a receipt-only evaluator now fails closed.
`doctor` with requirements reports authenticated metadata without importing the
target; discovery without requirements grants no execution admission.

## Evidence and third-party execution

An evaluator receives the public `EvaluationContext` and produces namespaced
`AssertionEvaluation` records with verified evidence digests. Read an admitted
local evidence path once through the matching SDK public API
`context.evidence.read_local(path, max_raw_evidence_bytes=...)`; process the returned
immutable bytes rather than
reopening a mutable path. Evidence inputs must be read-only in the author profile.

Run third-party evaluators in the selected limited process/image profile with
read-only evidence mounts and declared resource/deadline limits. The infrastructure
owns that boundary; this SDK is not a sandbox or a process supervisor. The
existing import guard is retained until any replacement establishes equivalent
protection.

The installed-byte result covers this wheel's files. A complete qualification also
needs the agreed interpreter, dependencies, verifier/root provenance and execution
composition, plus evaluator-method evidence. Package publication, composition
verification and a native profile's acceptance remain separate records.

[The standalone author example](../consumer-examples/evidence-byte-check/README.md)
shows public imports, a PyPA entry point and one captured-evidence assertion.
Its README identifies the matching SDK and execution-profile requirements.

## Source integration witness

The `evaluator-admission` CI job builds the minimal author wheel, attests it with
the pinned official `actions/attest`, and supplies exact workflow SAN, source
ref/commit, signer commit and wheel digest expectations from the CI composition.
It uses pinned gh 2.102.0 binary and root bytes without ambient verifier
credentials. Before ordinary pip installation, it authenticates and validates a
private captured wheel copy.

The installed CLI then runs in a non-root OCI process using the existing
Docker/Podman fixture mechanism: read-only root and original evidence mounts,
no network or capabilities, no new privileges, 512 MiB memory, one CPU, 32 PIDs,
a 256 MiB temporary filesystem and a 180-second outer deadline. The temporary
filesystem permits execution of the pinned verifier snapshot and sets nosuid/nodev. Assessment
outputs use a separate writable mount. The witness checks the author byte
assertion, refused evidence/profile writes, receipt-only and wrong-publisher
failures, and unchanged original input bytes. Its input counter records are
synthetic method inputs; the byte count is not observed robot performance.

This source/CI witness is not a published SDK, infra image admission, dependency
publisher proof or native hardware qualification. Full composition provenance
and subsequent package publication have separate gates.

The local-key witness additionally creates a temporary local publisher with the
admitted stock tool, retains only public verification material, installs the
authenticated captured wheel and runs the same read-only bounded CLI worker.
Genuine wrong-key, altered DSSE/subject/predicate, fake-report and unissued-token
controls are distinct from JSON consistency checks. Private key bytes are never
tracked or included in artifacts.
