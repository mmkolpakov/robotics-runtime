# First result with the published Python tools

This path installs contracts 0.20.0 and harness 0.21.0 from PyPI, creates explicit
inputs, and evaluates them offline. It uses Python 3.12–3.14, pip and an ordinary
POSIX shell. It requires neither ROS nor Node. The MCAP extra is required by this example's
recording producer; ordinary document validation does not require that extra. MCAP 1.4.0 is pinned
for this example producer, independently of native runtime release compositions.

The example is synthetic. Its scenario policy, runtime declarations, metric points
and single UInt64 recording are authored sample data. The producer binds real file
bytes and the harness checks them, but no simulator, robot, image or native operation
is qualified by this exercise. The v1 profile still carries ROS-specific fields;
those sample declarations are not observations of the machine running this tutorial.

## Install and obtain the inputs

Create an empty working directory and an isolated environment:

```bash
mkdir robotics-first-result
cd robotics-first-result
python3 -m venv .venv
. .venv/bin/activate
python -m pip install "robotics-runtime-contracts[mcap]==0.20.0" \
  robotics-acceptance-harness==0.21.0 mcap==1.4.0
robotics-contracts --help
robotics-acceptance --version
```

Download the consumer inputs archive exported by this documentation build. Save it
as `consumer-inputs.zip` in the working directory. The published reader serves the same download here:

```bash
curl -fL https://mmkolpakov.github.io/robotics-runtime/consumer-inputs.zip \
  -o consumer-inputs.zip
python -m zipfile -e consumer-inputs.zip example
python example/produce.py --output inputs
```

The archive contains `produce.py`, `scenario-input.json`,
`runtime-template.json`, `README.md` and `manifest.json`. Its manifest records
the source revision and SHA-256 of each example file. Retain the downloaded
archive and manifest with your result. It is an example distribution from the
reader, separate from the two PyPI wheels. Package installation does not install
these files or `tests/fixtures`.

For development from a checkout, the identical inputs are in
[consumer examples](../packages/contracts/consumer-examples/published-cli/README.md).
Run its producer with the installed Python interpreter. No checkout imports or
test support modules are used.

## What produces each input

- `scenario-input.json`: the sample scenario author's declared policy. The producer
  validates and writes it as `inputs/scenario.json` with `write_document`.
- `runtime-template.json`: synthetic runtime facts supplied to
  `create_runtime_manifest`, then `write_document`. Output:
  `inputs/runtime-manifest.json`. A real integration supplies facts from its
  selected runtime producer rather than filling them with defaults.
- `inputs/acceptance-run.json`: the producer supplies an explicit run ID, timestamp,
  time authority and primary domain; `write_document` writes the run and binds its
  scenario SHA-256 to the exact emitted bytes. For a new real run, the public
  `robotics-acceptance create-run` command creates this context.
- `inputs/metrics.otlp.jsonl`: this example producer writes one synthetic OTLP
  JSON-lines envelope, attributed to the declared run and domain. In a real run,
  the workload and configured OpenTelemetry collector produce the metrics.
- `inputs/recording.mcap`: the upstream MCAP writer writes one synthetic
  `std_msgs/msg/UInt64` sample on `/example/counter`. The public
  `recording_summary_from_mcap` producer derives
  `inputs/recording-summary.json` from those finalized bytes.
- `inputs/evidence-index.json`: `create_evidence_index`,
  `add_evidence_artifact`, `finalize_evidence_index` and `write_document` bind
  both source files and the summary. `inputs/evidence-draft.json` is intermediate
  writer state, not a document consumers may use as finalized evidence.

The evidence writer computes file size, digest, local path and URI. Run the
producer in the final input directory: copying the generated documents alone to
another location leaves their absolute evidence references pointing at the old
files. Transfer the originals through your evidence retention process and rebuild
the local references where appropriate; preserve signed original bytes.

## Validate, then evaluate

Document validation is independent of harness readiness. It does not need
`robotics-acceptance doctor`:

```bash
robotics-contracts validate inputs/scenario.json inputs/runtime-manifest.json \
  inputs/acceptance-run.json inputs/recording-summary.json inputs/evidence-index.json
robotics-acceptance explain --scenario inputs/scenario.json \
  --runtime inputs/runtime-manifest.json
```

Both commands exit `0`. `explain` cross-checks the bundle and reports its declared
policy; it does not execute the workload or establish an acceptance verdict.
Now produce the first result:

```bash
robotics-acceptance evaluate \
  --scenario inputs/scenario.json --runtime inputs/runtime-manifest.json \
  --run-id run-01234567-89ab-4def-8123-456789abcdef --domain-id primary \
  --run-context inputs/acceptance-run.json --evidence-index inputs/evidence-index.json \
  --otel-metrics inputs/metrics.otlp.jsonl \
  --window-start-ns 1785067200000000000 --window-end-ns 1785067201000000000 \
  --output results --diagnostic-output evaluation-diagnostic.json
```

This command deliberately exits `1`, with `status: incomplete`. It creates
`results/acceptance-result.json` and `results/junit.xml`. The available synthetic
metric and evidence checks pass, while graph, live clock, forbidden graph and
shutdown coverage remain in `unevaluated`. JUnit reports the absent coverage as
skipped. A completed offline evaluation cannot establish the live `passed`
verdict.

Use `why` only after a result exists:

```bash
robotics-contracts validate results/acceptance-result.json
robotics-acceptance why results/acceptance-result.json --format markdown
```

Both commands exit `0`; explaining an incomplete result leaves its verdict
incomplete. Result IDs vary per evaluation. The declared synthetic input time
window and input file digests retain their original meanings.

## Refusal and non-passing outcomes

Harness verdict commands exit `0` for `passed` and `1` for completed
`failed`, `incomplete` or `error` verdicts. A handled input or execution
exception exits `2` and emits a diagnostic; it is different from a result with
status `error`. Do not treat all nonzero codes as a missing output.

To see a refusal after retaining the first result, append one blank line to the
indexed metrics without rebuilding the index:

```bash
python -c 'from pathlib import Path; p = Path("inputs/metrics.otlp.jsonl"); p.write_bytes(p.read_bytes() + b"\n")'
```

Repeat `evaluate` with `--output rejected-results` and
`--diagnostic-output rejected-diagnostic.json`. It exits `2` because the source
bytes no longer match the index. It writes a diagnostic rather than a new result
or JUnit report. The earlier `results/` remains the record of the first evaluation.
Start a new producer output directory to obtain an unmodified example again.

## Published boundaries

This recipe uses no custom extensions. In harness 0.21.0 the bundle loader passes
`--extension-schema` to the scenario but does not forward that registry to
runtime, model, dataset, permit or verification documents. The development source
contains a fix; installing the 0.21.0 wheel does not include it. Do not assume this
published wheel supports the same extension-bearing bundle paths as current
source. Contracts 0.20.0 can validate such individual documents when supplied the
matching schema bytes.

`doctor` reports observer/evaluator metadata where needed. It is not a prerequisite
for contracts-only validation and it does not prove native readiness. Live
`verify` requires the selected ROS environment, externally started workload,
finalized evidence and applicable qualification inputs. See the
[harness reference](../packages/harness/README.md) and
[compatibility boundaries](../packages/harness/docs/compatibility.md).
