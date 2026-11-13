# First result with the published Python tools

Create a validated input set, evaluate it with the published Python tools, then
read the verdict and the evidence behind it. The result is intentionally
`incomplete`: the example supplies synthetic data but not the live observations
needed for a passed qualification. You will also change an evidence file and
see the integrity check refuse it.

It uses Python 3.12–3.14, pip and an ordinary POSIX shell. It requires neither
ROS nor Node.

## Install and obtain the inputs

Create an empty working directory and an isolated environment:

```bash
mkdir robotics-first-result
cd robotics-first-result
python3 -m venv .venv
. .venv/bin/activate
python -m pip install "robotics-runtime-contracts[mcap]==0.22.0" \
  robotics-acceptance-harness==0.23.1 mcap==1.4.0
robotics-contracts --help
robotics-acceptance --version
```

This recipe selects a stable harness release. Use its source archive to keep the
example producer and templates tied to that release rather than to a later
documentation build:

```bash
EXAMPLE_TAG="harness-v$(python -c 'from importlib.metadata import version; print(version("robotics-acceptance-harness"))')"
curl -fL "https://github.com/mmkolpakov/robotics-runtime/archive/refs/tags/$EXAMPLE_TAG.zip" \
  -o example-source.zip
python -m zipfile -e example-source.zip example-source
python "example-source/robotics-runtime-$EXAMPLE_TAG/packages/contracts/consumer-examples/published-cli/produce.py" \
  --output inputs
```

Retain `example-source.zip` and the selected tag with the result. The producer
imports the installed Python packages, not modules from the source archive.
The [source example](../packages/contracts/consumer-examples/published-cli/README.md)
contains `produce.py`, `scenario-input.json`, `runtime-template.json` and its
README. Package installation does not install these files or `tests/fixtures`.

The reader also provides a smaller `consumer-inputs.zip` for its current build.
That archive's manifest identifies its source revision and file digests. It is a
separate source snapshot, not a replacement for the release archive selected by
this recipe; matching file hashes alone do not establish package compatibility.

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

The command exits `1` with `status: incomplete` and writes
`results/acceptance-result.json` and `results/junit.xml`. This is the expected
first-run outcome: the available synthetic metric and evidence checks pass, and
the result names the coverage a live `passed` verdict still needs. JUnit reports
the absent coverage as skipped.

## From incomplete to passed

Each `unevaluated` path identifies evidence the selected live profile still
needs:

- `$.observed_ros_graph` and `$.forbidden_graph_observation`: the running ROS 2
  graph and its forbidden-graph check, observed by the attach-only harness
  observer;
- `$.clock_observation`: live clock and time-authority evidence from the
  selected runtime;
- `$.shutdown`: observed lifecycle shutdown coverage.

A live `passed` verdict requires the selected ROS environment, an externally
started workload, finalized evidence and the applicable qualification inputs,
evaluated through live `verify`. The
[harness reference](../packages/harness/README.md) and
[compatibility boundaries](../packages/harness/docs/compatibility.md) name the
supported profiles.

Use `why` to read the stored verdict and its causes:

```bash
robotics-contracts validate results/acceptance-result.json
robotics-acceptance why results/acceptance-result.json --format markdown
```

Both commands exit `0`; explaining an incomplete result leaves its verdict
incomplete. Result IDs vary per evaluation. The declared synthetic input time
window and input file digests retain their original meanings.

## Refusal and exit codes

Harness verdict commands exit `0` for `passed` and `1` for completed
`failed`, `incomplete` or `error` verdicts. A handled input or execution
exception exits `2` and emits a diagnostic instead of a result; it is different
from a result with status `error`.

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

## Boundaries of this example

The example is synthetic: its scenario policy, runtime declarations, metric
points and single UInt64 recording are authored sample data. The producer binds
real file bytes and the harness checks them. The v1 profile includes
ROS-specific fields; the sample declarations are not observations of the machine
running this tutorial. This exercise qualifies no simulator, robot, image or
native operation.

The MCAP extra is required by this example's recording producer; ordinary
document validation does not require that extra. The installation command pins
MCAP for this example producer, independently of native runtime compositions.

This recipe uses canonical v1 execution documents and no custom extensions.
The published loader forwards an explicitly supplied pinned extension registry
to every loaded bundle document. Custom namespaces cannot override common
contract rules.

`doctor` reports observer/evaluator metadata where needed. It is not a
prerequisite for contracts-only validation and it does not prove native
readiness.
