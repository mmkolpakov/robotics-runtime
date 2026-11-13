# Evaluator authentication

The wheel profile provides `authenticate_wheel`, `authenticate_wheel_with_cosign_key`,
`validate_evaluator_wheel` and
`verify_installed_wheel` in `robotics_acceptance_harness.evaluator_trust`.
These APIs verify artifact origin and installed bytes. The loader and CLI require these
captured bindings before importing a declared evaluator, and retain the existing
verified-source import guard.

## Bounded file capture

`robotics_acceptance_harness.evaluator_trust.read_once` captures bytes once
from a caller-supplied trusted path:

```python
def read_once(path: Path, limit: int, *, forbid_group_other_write: bool = False) -> bytes: ...
```

Pass a `pathlib.Path` and a positive integer byte limit. The returned bytes
are not parsed or normalized. The helper expands the home path, checks for
symlinks by resolving the absolute path, and opens one read-only descriptor
with POSIX no-follow and nonblocking flags. It rejects non-regular files,
inputs over the limit and changes to device, inode, mode, size, modification
time or change time observed on that descriptor during capture. It reads at
most the limit plus one byte and closes the descriptor on success or failure.

`forbid_group_other_write=True` also refuses group- or other-writable mode
bits. It does not check ownership or authenticate the content. Profile refusals
raise `EvaluatorTrustError`, a `HarnessError` and `ValueError` with
`error_id = "evaluator_trust.invalid"`. Filesystem errors may propagate as
`OSError`. The helper requires the POSIX flags; it does not promise a timeout
or general validation of unsupported argument types.

The returned bytes are the snapshot to hash and validate. A later path reopen
is a different read. The pre-open path resolution is not a directory-descriptor
traversal sandbox: the caller must provide stable trusted ancestors and a sealed
or private read-only input root for the required lifetime. Capture does not
prove producer settlement, provenance, signatures or qualification.

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

The [integration fixture](../tests/admission/README.md) records the independently
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
Verifier stdout and stderr have live byte limits. A successful capture requires
both streams to reach EOF and the direct child to exit within the command deadline.
Cosign attestation reports also share the combined report limit. Overflow or a
deadline closes the local pipes and starts bounded termination and reaping of
the direct verifier child. This does not settle descendants or an Engine-managed
evaluator; the execution profile supplies process resource bounds.
Standard ZIP/CSV readers perform the decoding; duplicate paths, traversal and
unsupported members are refused.

## CLI and SDK execution admission

The CLI accepts `--evaluator-trust-profile PATH` on `evaluate`, `verify`
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
exactly to the active scenario or selected assessment-control requirement; its
wheel digest must match that requirement. Original runtime bindings remain
unchanged when an archive assessment selects another evaluator.
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

## Local OCI archive assessment

The [published harness installation](../../../docs/first-result.md#install-and-obtain-the-inputs)
includes this optional path. An OCI assessment additionally requires an operator
trust profile, Engine and Cosign executables, and the exact admitted evaluator
image. On `evaluate`, select `--assessment-controls`, `--original-result` and
`--evaluator-trust-profile`. Controls marked `assessment-controls.v1` declare
each OCI namespace, image subject and exact expected assertion IDs. The original
scenario, runtime, observation and result retain their v2 schemas; the original
run and evidence index retain v1. The new assessment is `acceptance-result.v3`.
The version 1 wheel profile and its public Python
authentication APIs keep their existing behavior. Version 2 belongs to this
archive `evaluate` path; version 1 also serves `verify` and `doctor`.

Version 2 is a closed operator file with exactly `profile_version`, `verifier`,
`engine`, `limits` and `evaluators`. It belongs outside the evidence root.
Relative file paths resolve from the operator file's directory.

- `verifier`: `kind="cosign_blob_key_no_tlog"`, `executable`,
  `executable_sha256`, exact `version`, `public_key`, `public_key_sha256`,
  `trusted_root` and `trusted_root_sha256`. Use an independently approved stable
  Cosign composition at least 3.1.4; the observed version must match exactly.
- `engine`: `backend="podman_local"`, pinned `executable` and
  `executable_sha256`, `version="4.9.3"`, `environment`, `containers_conf`,
  `storage_conf`, `store` and `hooks_dir`. Each configuration file has exactly
  `path` and `sha256`.
- `environment`: explicit `HOME`, absolute-entry `PATH`, `XDG_RUNTIME_DIR` and
  one owned local `DBUS_SESSION_BUS_ADDRESS` socket. `store` has `graph_root`,
  `run_root`, `tmpdir` and `driver`.
- Each evaluator has exactly `namespace`, fully qualified immutable `image_ref`,
  `manifest`, `config`, `bundle`, `manifest_sha256`, `platform` and
  `invocation="evaluator_json_v1"`. Platform has `os`, `architecture` and an
  optional `variant`. Bind every declared namespace once.

The operator preloads the image and initializes a dedicated rootless context.
Pin `storage.graphroot` and `storage.rootless_storage_path` to the selected graph
directory; select `run_root` and `storage.runroot` as
`<XDG_RUNTIME_DIR>/containers`. In `containers.conf`, select `lock_type="file"`,
the exact project `tmp_dir` on tmpfs, `static_dir=<graph_root>/libpod` and
`volume_path=<graph_root>/volumes`. Keep a separate project runtime/pause directory,
an empty hooks directory and the existing local user bus. The caller must have
normal systemd delegation for CPU, memory and PIDs. The harness checks declared
paths and observed Engine facts; the operator owns store initialization.

`limits` contains positive integers: `attempt_timeout_sec`,
`command_timeout_sec`, `cleanup_timeout_sec`, `stdout_bytes`, `stderr_bytes`,
`memory_bytes`, `input_bytes`, `pids`, `cpus` and `tmpfs_bytes`.
Timeouts cannot exceed 86400 seconds; command timeout cannot exceed attempt
timeout. Stdout is capped at 1 MiB and stderr at 32 MiB. `input_bytes` limits
unique staged bytes, including the request, in addition to existing evidence
file limits; it is separate from container memory.

After input preparation, one attempt deadline covers raw-manifest authentication
and Engine commands. Stock Cosign verifies the exact manifest with the selected
external public key. The harness checks the OCI or Docker Schema2 manifest/config
pair, raw digests, config size and platform. The selected manifest digest remains
the signed transport identity. Execution binds its config SHA
([OCI ImageID](https://github.com/opencontainers/image-spec/blob/v1.1.1/config.md#imageid)),
the exact ordered `rootfs.diff_ids`, and the container's image ID, immutable image
name, full CID and attempt label. The container's canonical `ImageDigest` is
recorded transport metadata. An index or manifest list is not a platform manifest.
The signature is not build provenance or evidence that a container ran.

The image keeps its declared exec-array ENTRYPOINT and receives the fixed
`--request /run/robotics-evaluator/request.json` arguments. Only private captured
inputs are mounted read-only. The worker has no network, TTY or inherited stdin,
a read-only root and declared resource limits. Stdout and stderr are captured as
separate bounded byte streams. The parent retains completed stdout as
`response.bin` before removing the container, confirms its exit and absence,
then decodes the response with the authoritative request hash, namespace,
expected IDs and evidence digests. The harness computes coverage and final status.

The output's `oci-attempt-*` directory keeps files written before a failure.
The owner creates `journal.json` after checking the prepared inputs; successful
authentication adds manifest/config bytes and signature audit. A completed stdout
capture adds `response.bin` before removal. Early refusals may precede these files.
Uncertain termination or cleanup refuses the assessment and retains the attempt.
Recovery does not replay creation/start or remove an unconfirmed container. A separate cleanup
deadline bounds the attempt to stop its exact owned CID. Local CLI termination
alone does not prove all descendants or the Engine container stopped.

If `execution_subject.provenance_receipt_sha256` is declared, the existing
receipt/verification/dependency inputs must bind that receipt to the captured
manifest SHA and size before execution. The supplied receipt set must match the
declared set exactly. This documentary check is separate from live signature and
CID checks. Retained environment bytes describe stable assessment composition;
per-attempt CID facts stay in the journal. Portable qualification checks retained
bytes and contract relationships, not independent historical execution authenticity.

## Evidence and third-party execution

A Python wheel evaluator receives the public `EvaluationContext` and produces namespaced
`AssertionEvaluation` records with verified evidence digests. In that wheel, read an admitted
local evidence path once through the matching SDK public API
`context.evidence.read_local(path, max_raw_evidence_bytes=...)`; process the returned
immutable bytes rather than
reopening a mutable path. Without an explicit byte budget, this API limits each
capture to 8 MiB; a positive explicit budget sets the limit for that raw capture.
Structured documents retain their separate 8 MiB limit. Evidence inputs must be
read-only in the author profile.

The wheel import guard authenticates Python source; process isolation belongs to
its selected execution composition. For the optional OCI archive path, the harness
owns admission, captured inputs, the finite Engine invocation and response decoding.
The Engine enforces the read-only mounts, network and resource policy. Built-in
evaluation and offline document inspection do not require an Engine.

The installed-byte result covers this wheel's files. A complete qualification also
needs the agreed interpreter, dependencies, verifier/root provenance and execution
composition, plus evaluator-method evidence. Package publication, composition
verification and a native profile's acceptance remain separate records.

[The standalone author example](../consumer-examples/evidence-byte-check/README.md)
shows public imports, a PyPA entry point and one captured-evidence assertion.
Its README identifies the matching SDK and execution-profile requirements.

## Installed integration witness

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

This installed witness establishes the documented author-method path. It does
not establish infra image admission, dependency publisher proof or native
hardware qualification. Full composition provenance remains a separate gate.

The local-key witness additionally creates a temporary local publisher with the
admitted stock tool, retains only public verification material, installs the
authenticated captured wheel and runs the same read-only bounded CLI worker.
Genuine wrong-key, altered DSSE/subject/predicate, fake-report and unissued-token
controls are distinct from JSON consistency checks. Private key bytes are never
tracked or included in artifacts.
