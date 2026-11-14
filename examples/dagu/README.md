# Offline first-result Dagu recipe

A stock [Dagu](https://github.com/dagucloud/dagu) workflow that runs the published
contracts and harness CLIs through the first-result journey: produce synthetic
documents, validate, explain, evaluate, then explain the verdict. It is the
runnable companion to [first-result.md](../../docs/first-result.md).

Tested with Dagu **v2.25.8** and the published cohort
`robotics-runtime-contracts==0.22.0`, `robotics-acceptance-harness==0.24.0`,
`mcap==1.4.0`.

## Setup

Install Dagu v2.25.8 and a published Python environment:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python \
  "robotics-runtime-contracts[mcap]==0.22.0" \
  robotics-acceptance-harness==0.24.0 mcap==1.4.0
```

## Run

From the checkout root, point the parameters at your environment. `OUT` collects
the inputs, results and diagnostics.

```bash
dagu dry examples/dagu/first-result.yaml -- \
  PYTHON="$PWD/.venv/bin/python" \
  CONTRACTS="$PWD/.venv/bin/robotics-contracts" \
  HARNESS="$PWD/.venv/bin/robotics-acceptance" OUT="$PWD/dagu-out"

dagu start examples/dagu/first-result.yaml -- \
  PYTHON="$PWD/.venv/bin/python" \
  CONTRACTS="$PWD/.venv/bin/robotics-contracts" \
  HARNESS="$PWD/.venv/bin/robotics-acceptance" OUT="$PWD/dagu-out"
```

The synthetic inputs yield an **incomplete** verdict: `evaluate` exits 1, the
workflow ends `Failed`, and `results/acceptance-result.json` plus `junit.xml` are
retained. A failure handler runs `why` to explain the verdict.

Add `TAMPER=1` to append a byte to the indexed metrics. `evaluate` then exits 2
and writes `evaluation-diagnostic.json` instead of a result; the workflow ends
`Failed` and the handler exits without calling `why` because no result exists.

## Agent path

Start and inspect runs through Dagu's MCP tools (`dagu_execute`, `dagu_read`);
the six-tool domain MCP adapter stays read-only for document inspection. Keep the
Dagu dag-run ID, the domain run ID and the result ID distinct.
Read `acceptance-result.json` for the verdict.

## Parameters

| Parameter | Default | Purpose |
| --- | --- | --- |
| `PYTHON` / `CONTRACTS` / `HARNESS` | `python3` / `robotics-contracts` / `robotics-acceptance` | installed published environment |
| `OUT` | `dagu-out` | output directory |
| `TAMPER` | `0` | `1` demonstrates the exit-2 refusal |

The producer path, run ID and measurement window are the published-cli fixture's
fixed literals, not parameters.
