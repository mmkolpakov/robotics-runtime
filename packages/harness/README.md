# Robotics Acceptance Harness

[![CI](https://github.com/mmkolpakov/robotics-runtime/actions/workflows/ci.yml/badge.svg)](https://github.com/mmkolpakov/robotics-runtime/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Read-only acceptance evaluation for existing robotics executions and archives.

The harness validates an execution bundle, observes declared ROS/OpenTelemetry
facts or captured native observations, verifies retained evidence, and writes
contract-valid JSON/JUnit results. The live ROS observer is attach-only. The
harness does not launch workloads, control simulators, change node lifecycle
states or publish commands to equipment.

Current source supports native v2 software/simulation assessment, explicit
method controls and qualification-bundle.v2 archive comparison. Selected
evaluator admission uses an operator-pinned stock signature verifier and executes
captured authenticated source through the existing import guard. Physical
execution authorization retains the external permit/verification workflow.
The [archive guide](docs/archive-assessment.md), [trust guide](docs/evaluator-trust.md)
and [compatibility reference](docs/compatibility.md) define these source APIs;
they are absent from published harness 0.21.0/contracts 0.20.0.

See [local evidence and timestamps](docs/evidence-files.md) for filesystem
containment, finalized-file reads and the distinction between Unix and monotonic time.

## Architecture

```text
product workload -> runtime infrastructure -> running ROS 2 graph
                                                   |
runtime contracts -> acceptance harness -----------+
                          |
                          +-> result JSON + JUnit + evidence links
```

- [robotics-runtime-contracts](https://github.com/mmkolpakov/robotics-runtime/tree/main/packages/contracts)
  owns document structure and verdict semantics.
- This package owns observation and evaluation.
- [robotics-runtime-infra](https://github.com/mmkolpakov/robotics-runtime-infra)
  owns runtime, simulator, middleware, recorder, and hardware provider adapters.
- Product repositories own scenes, robots, models, behavior, and business
  evaluators.

The harness consumes provider-neutral runtime facts. Adding a simulator,
middleware, recorder, or accelerator does not require a new scenario or result
version.

## Requirements

| Component | Baseline |
| --- | --- |
| Python | 3.12 through 3.14 |
| Contracts source | `robotics-runtime-contracts>=0.21,<0.22` |
| ROS observation | ROS 2 Jazzy packages in the observer environment |
| Metrics | OTLP JSON Lines exported by OpenTelemetry Collector |

Each role retains one canonical default. Datasets use v2 for one complete bag;
source scenario/runtime/observation/result/qualification roles additionally
support explicit v2 selection. The published pair uses the existing v1 execution
formats.
The dataset transition is an explicit pre-1.0 breaking release. Checks for
unrelated published schemas and historical byte identities remain strict.

## Install

The published v1 pair is
[harness 0.21.0](https://pypi.org/project/robotics-acceptance-harness/0.21.0/) with
[contracts 0.20.0](https://pypi.org/project/robotics-runtime-contracts/0.20.0/):

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install robotics-acceptance-harness==0.21.0 robotics-runtime-contracts==0.20.0
```

Development uses both packages and the dependency graph in the root `uv.lock`:

```bash
git clone https://github.com/mmkolpakov/robotics-runtime.git
cd robotics-runtime
uv sync --locked --all-packages --all-groups
uv run robotics-acceptance --version
cd packages/harness
```

Release consumers should install the published wheel together with the locked
contracts wheel and verify release provenance as described in
[`docs/supply-chain.md`](docs/supply-chain.md).
[Preserved run and release records](../../docs/run-history.md) retain each
archive's original versions, identities, scope and outcome. Installing these Python
packages does not qualify an infra image, simulator, accelerator or physical target.

## Quick Start

Follow [the published first-result path](../../docs/first-result.md) to install the
exact pair, obtain all inputs, validate documents, evaluate synthetic evidence and
read the resulting JSON/JUnit. Offline evaluation exits `1` with `incomplete`
because live graph, clock and shutdown coverage is absent.

A scenario comes from its author, a runtime manifest from the selected runtime
producer, a run context from `create-run` or a public document writer, and evidence
from the workload's recorder and telemetry collector. The guide names each exact
example file and producer. `tests/fixtures` is source-development data and is not
installed by pip. `doctor` is not required for contracts-only validation; `why`
takes an existing result.

Create the immutable context shared by every domain in a new real run:

```bash
robotics-acceptance create-run \
  --scenario scenario.yaml \
  --output acceptance-run.json \
  --domain primary=observer \
  --time-authority sim_clock \
  --time-source simulation-clock
```

Run `robotics-acceptance COMMAND --help` for the complete option set.

`verify`, `evaluate`, `transport-evaluate`, `timing-check` and `otel-summary`
accept `--max-raw-evidence-bytes BYTES`, a positive integer limit for each raw
OTLP file. Their library entry points accept the optional
`max_raw_evidence_bytes` keyword (`None` or a positive non-bool integer).
Omission preserves unlimited raw-file size;
an explicit limit rejects oversized or growing inputs before parsing a prefix.
This bounds raw materialization per file, not aggregate evidence or process memory.

## Commands

| Command | Purpose | Controls the workload |
| --- | --- | --- |
| `create-run` | Create an immutable run context | No |
| `explain` | Validate and explain an execution bundle | No |
| `verify` | Observe a live ROS 2 execution | No |
| `evaluate` | Re-evaluate finalized evidence offline | No |
| `aggregate` | Fold all declared domain results | No |
| `transport-evaluate` | Qualify cross-domain delivery and causal traces | No |
| `campaign` | Aggregate repeated run verdicts | No |
| `doctor` | Report observer and extension metadata | No |
| `why` | Explain a result verdict | No |
| `timing-check` | Check verified clock metrics against scenario policy | No |
| `otel-summary` | Summarize normalized OTLP metric points | No |

Verdict-producing commands return `0` for `passed` and `1` for a completed
non-passing verdict, including `failed`, `incomplete`, or `error`. An input,
observation, or execution exception handled by the CLI returns `2` with a
diagnostic. A result whose status is `error` is distinct from such an exception.

A v1 domain result takes the most severe outcome of its assertions and of the
forbidden-graph, hardware-clock and time-authority observations. Skipped
assertions and declared `unevaluated` paths make an otherwise passing result
`incomplete`; they appear in JUnit as skipped cases, not failures.

V1 `clock_observation.real_time_factor` and `deadline_miss_ratio` are measured only
in `simulation_realtime`; other time modes report `0`.

`campaign` reports `incomplete` when fewer runs passed than the required
minimum and no failed or error runs were observed. Tolerated failed or error
runs still allow `passed` when every threshold is met.

Modeled library failures inherit from the public `HarnessError` base, with an
explicit `error_id` and `exit_code` (normally `2`). Existing exception classes
retain their identifiers and their `ValueError`, `RuntimeError`, or `TimeoutError`
compatibility. Invalid values supplied to the harness raise `HarnessInputError`
with `input.invalid`.

The command boundary translates dependency failures before the CLI handles
`HarnessError`: contract errors retain their identifier, I/O errors use
`input.io_error`, invalid dependency values use `input.invalid`, and unexpected
exceptions use `internal.error`. Diagnostics retain the original exception type,
message, and any JSON paths; exception chaining preserves the original cause.
Readiness, bundle, and evidence errors expose structured `(json_path, message)`
pairs through `diagnostic_issues`. `KeyboardInterrupt` and `SystemExit` propagate.

## Live Observation

Runtime infrastructure starts the workload, recorder, and telemetry collector.
The harness joins the existing ROS domain:

```bash
robotics-acceptance verify \
  --scenario scenario.yaml \
  --runtime runtime-manifest.json \
  --run-id run-7dd792f2-4f75-4f4d-81b0-48c8c2a8f76c \
  --domain-id primary \
  --run-context acceptance-run.json \
  --evidence-index evidence-index.json \
  --otel-metrics metrics.otlp.jsonl \
  --measurement-complete measurement-complete \
  --output results
```

The output directory contains `acceptance-result.json` and `junit.xml`. The
observer inherits standard ROS variables such as `ROS_DOMAIN_ID`,
`RMW_IMPLEMENTATION`, and the SROS2 environment. It has no private fallback for
document paths or execution identity.

An expected topic's `qos_profile` selects the observer subscription's QoS.
The compatibility check compares discovered publishers with that subscription;
it does not compare every application publisher/subscriber pair. The harness
excludes its own subscriptions from the observed subscriber count. When the
scenario does not declare `/clock`, its observation subscription uses depth 1,
best-effort reliability, and volatile durability.
The explicit `transient_local` profile uses reliable delivery, transient-local
durability and keep-last history with depth 10. It can receive retained samples
when the publisher offers compatible durability and retains them. It does not
make a cached sample fresh or establish ongoing production; consumers choose
this profile explicitly for retained topics. Existing profiles are unchanged.

## Offline Evaluation

`evaluate` runs the same metric, evidence, and product evaluators without
joining ROS. Live graph, clock, safety-boundary, and shutdown observations are
marked `unevaluated`, so an offline result cannot silently claim complete live
acceptance.

If every available offline check passes, the result is still `incomplete` and
`evaluate` exits `1`. JUnit marks the missing live coverage as skipped. Evidence
of a failure or error can raise the result's severity; malformed input or an
execution exception exits `2`. A successful offline invocation therefore does
not establish the `passed` verdict required for exit `0`.

Local evidence is verified by URI, path, size, and SHA-256. Retained evidence
also requires a receipt, its typed external-verification record, and the
referenced statement, trust policy, and verification evidence:

```bash
robotics-acceptance evaluate \
  --scenario scenario.yaml --runtime runtime-manifest.json \
  --run-id "$RUN_ID" --domain-id primary --run-context acceptance-run.json \
  --evidence-index evidence-index.json \
  --artifact-receipt artifact-receipt.json \
  --artifact-verification artifact-verification.json \
  --receipt-dependency statement.json \
  --receipt-dependency trust-policy.json \
  --receipt-dependency verification.bundle \
  --otel-metrics metrics.otlp.jsonl \
  --window-start-ns 1786000000000000000 \
  --window-end-ns 1786000030000000000 \
  --output results
```

The external verification binds the full artifact descriptor: URI, immutable
revision, media type, size, and SHA-256. The harness needs no storage
credentials. Upload, signing, and retention lifecycle remain infrastructure
responsibilities. OTLP file-exporter streams use `application/x-ndjson`.

For recordings whose receipts appear after observation starts, pass
`--receipt-inventory /evidence/receipt-inventory.json` to `verify`, `evaluate`,
or `timing-check`. Use `--receipt-inventory DOMAIN=PATH` with
`transport-evaluate`. The inventory contains exactly these three file lists:

```json
{
  "receipts": ["receipts/recording-0.json"],
  "verifications": ["provenance/recording-0/artifact-verification.json"],
  "dependencies": [
    "provenance/recording-0/statement.json",
    "provenance/recording-0/trust-policy.pem",
    "provenance/recording-0/verification-evidence.sigstore.json"
  ]
}
```

Publish the inventory atomically before publishing the finalized evidence index.
The live observer reads it during its existing evidence wait, after measurement;
it need not exist when the observer starts. Missing or invalid files retain the
same evidence timeout and diagnostic behavior. Paths use canonical relative
POSIX notation below the inventory's directory. Absolute paths, traversal,
directory links escaping that root, duplicate paths and unused provenance are
rejected. The inventory uses the contract parser's document size limit and a
maximum of 4,096 files. A shared dependency occurs once in the list. Every
referenced receipt, verification and dependency still passes the same role and
byte-digest checks. Inventory and explicit receipt inputs cannot be mixed for
the same domain.

Python callers can pass `ReceiptInventory(path)` as `receipt_paths` to
`load_evidence_index`, or as `artifact_receipt_paths` to `run_verification`
and `evaluate_from_evidence`. Existing sequences of explicit file paths remain
supported. The inventory is a CLI input list, not a new contract document.

## Histogram windows

Explicit-bucket histogram counts and recorded sums are aggregated over their
actual contribution intervals. Cumulative evidence needs a baseline at the
window boundary. An earlier baseline is usable only when an unchanged point
after the boundary proves that the intervening interval contained no events.
Otherwise event timestamps cannot be recovered and the window is unevaluated.
A changed start timestamp delimits a reset; a decreasing count without a new
start timestamp leaves the reset boundary unknown.
A cumulative point whose start equals its observation timestamp is an
[unknown-start marker](https://opentelemetry.io/docs/specs/otel/metrics/data-model/#cumulative-streams-handling-unknown-start-time).
Its existing population is subtracted before counting subsequent window events.

After baseline subtraction, lifetime minima and maxima are discarded unless
the baseline was empty. Quantiles use the inverse empirical CDF (integer rank
`ceil(p * count)`) and report conservative bucket intervals. A threshold passes
or fails only when the entire interval proves that outcome. A straddling or
unbounded interval produces a skipped assertion and an incomplete result.
Delta histograms can also lack recorded extrema; the same bound rules apply.

Time-authority results keep the measured event count when only latency bounds
are uncertain. Their required numeric fields contain finite bound endpoints;
the `time-authority-evidence` assertion records the full intervals and outcome.
Missing statistics use explicit unevaluated markers and diagnostic placeholders,
never proof of a measured zero or a threshold breach. JUnit preserves these
skipped outcomes. Artifact digests and existing result schema fields are unchanged.

## Realtime timing windows

Live verification evaluates the complete measurement interval and overlapping
windows of at least one second. Clock callbacks bound source-clock progress;
the recorded `real_time_factor` is a conservative lower bound. A lower bound
below the policy threshold alone does not prove a violation. If the upper bound
also lies below the threshold, the time-policy assertion fails. When the bounds
straddle the threshold or clock coverage is missing, it is skipped and the
corresponding clock fields are listed as unevaluated, producing `incomplete`
unless another observation proves a failure.

Deadline ratios are independent evidence: the greatest observed value is checked
even when clock callbacks or other deadline samples are missing. A known deadline
exceedance or a clock stall proved by recorded endpoints remains a failure.
`why` preserves the distinction between unobserved and violated clock properties.

## Contract Inputs

| Input | Contract role |
| --- | --- |
| Scenario | `acceptance-scenario.v1` |
| Runtime facts | `runtime-manifest.v1` |
| Run context | `acceptance-run.v1` |
| Evidence and provenance | `evidence-index.v1`, `artifact-receipt.v1`, `artifact-verification.v1` |
| Model and dataset provenance | `model-artifact-manifest.v1`, `dataset-manifest.v2` |
| Physical authorization | `execution-permit.v1`, `execution-verification.v1` |
| Transport inputs | `transport-channel.v1`, `clock-relation.v1`, `causal-chain.v1` |
| Outputs | `acceptance-result.v1`, `acceptance-aggregate.v1`, `campaign-summary.v1` |

Dataset manifests use one complete rosbag2 MCAP set for one or multiple segments.
Native metadata and every recording/summary have exact retained byte references;
qualification checks the entire declared set. The current SDK uses v2 only.
Historical v1 artifacts retain their original version and are checked with the
matching archived package, rather than converted inside the current evaluator.

Scenario extensions are explicit and digest-pinned. Pass the same
`--extension-schema URI=PATH` mapping to every command that reads the scenario.
Harness 0.21.0 does not forward that registry to additional bundle documents
(runtime, model, dataset, permit or verification); the fix in development source
is separate from this published wheel. See
[published extension limits](../../docs/first-result.md#published-boundaries).
Extensions cannot replace common safety, timing, transport, or evidence rules.

## Product Evaluators

Product packages register standard PyPA entry points:

```toml
[project.entry-points."robotics_acceptance.evaluators"]
"org.example.sorting" = "sorting_acceptance:evaluate"
```

The scenario and runtime must declare the same namespace, target, distribution,
version, wheel SHA-256, and receipt SHA-256. Before importing a declared target,
the source harness requires actual wheel
authentication using an external operator profile, binds installed files and
original entry-point metadata to that wheel, and compiles captured source
through its verified import guard. Receipt JSON alone cannot allow execution.
Derived bytecode caches are ignored; source-less/native/extra namespace code is
refused. Use ordinary pip on the authenticated captured wheel copy.

See [evaluator authentication and operator profile](docs/evaluator-trust.md).
These APIs and the CLI trust-profile option are absent from published harness
0.21.0; current source integration does not qualify a published composition.

The harness compiles captured authenticated Python source bytes using an
explicit source loader, without reading or writing bytecode caches. This covers
the evaluator's parent packages and imports within the distribution's module
namespaces, including imports deferred until evaluation. Regular packages,
self-contained namespace packages, relative imports, and dotted entry-point
attributes are supported. Cross-distribution shared namespaces are outside the
current authenticated profile. Evaluator-owned modules require hashed Python source; native and
sourceless evaluator modules are rejected. Dependencies outside those namespaces
use Python's normal import machinery and remain part of the execution image's
trust boundary. This loading check is not a sandbox for malicious Python code,
and a locally editable `RECORD` does not authenticate the released wheel.

An evaluator receives an immutable `EvaluationContext` and returns
`AssertionEvaluation` objects in its own namespace. Every product assertion
must reference at least one digest from verified evidence. Duplicate assertion
IDs, undeclared packages, foreign namespaces, and unknown evidence fail closed.

`doctor --scenario scenario.yaml` checks the required evaluator metadata,
receipt chain, and installed `RECORD` without importing evaluator code.

## Pytest Integration

```bash
uv run pytest \
  -p robotics_acceptance_harness.plugin \
  --robotics-scenario scenario.yaml \
  --robotics-runtime runtime-manifest.json
```

Use `robotics_bundle` for the validated immutable bundle and
`robotics_scenario` for the scenario mapping. The plugin is not activated by
package installation and refuses physical targets.

## Development

Run from the workspace root; the package test suites run in separate processes:

```bash
uv sync --locked --all-packages --all-groups
uv run pre-commit run --all-files
uv run --directory packages/harness coverage run --branch -m pytest
uv run --directory packages/harness coverage report --fail-under=80
uv build --package robotics-acceptance-harness --no-sources
```

See [compatibility](docs/compatibility.md), [architecture decisions](docs/decisions/README.md),
[supply-chain assurance](docs/supply-chain.md), and the
[REP-2004 quality declaration](QUALITY_DECLARATION.md). Security reports follow
[SECURITY.md](SECURITY.md).

### Optional SignalFlag emissions import

The explicit `robotics_acceptance_harness.signalflag_emissions` module reads the
JSONL format emitted by SignalFlag SDK 1.8.0. It does not require that SDK at
runtime. The caller retains the original file through its existing evidence
path and supplies the original bytes:

```python
from robotics_acceptance_harness.signalflag_emissions import MetricBinding, read_emissions

samples = read_emissions(
    raw_emissions,
    bindings={("motion", "speed"): MetricBinding("org.example.speed", "m/s")},
    timestamp_basis="unix_ns",
)
```

Only explicitly bound numeric fields become native scalar gauge samples.
Selected records require an exact nonnegative integer timestamp, and the caller
must establish that it represents Unix nanoseconds. Simulation timestamps and
records without a known clock cannot be guessed or converted. Missing timestamps
are allowed on unselected records, which can still be retained as opaque bytes.

The reader reuses the contracts parser for bounded, duplicate-free, finite JSON.
Total input bytes and line, binding, and sample counts use its existing document
limits. Booleans and nonnumeric selected values are rejected. Integer values
must be exactly representable as float gauges; this allows larger representable
powers while refusing silent rounding. Units come from the binding without
conversion, and existing metric assertion evaluation remains responsible for
matching the declared metric unit and threshold.

Samples carry only scoped SignalFlag topic, field, line, source SHA-256, and
optional event provenance. That digest records byte identity, not filesystem
integrity or an attestation. Import does not create ROS graph facts, run or domain
identity, execution status, or a qualification verdict. The SDK endpoint facade
and server compatibility remain separate planned work.

The default tests also read a frozen fixture produced by the actual SDK 1.8.0
Emitter. Its SHA-256 is
`b3d92727949e534172f45a0a79abb654952bf35a93c0c046017d3275043b7ee4`.
Optional producer tests use an installed, pinned `signalflag==1.8.0` package and
verify that real scalar, series, event, and untimed output matches those bytes.
They skip when that optional test dependency is absent; the normal harness has
no SDK dependency. The official wheel used for producer qualification has
SHA-256 `5431d8dd8f6332b2f2c8a873f3e45568bffb39b87a8342069be52594918487d4`.
