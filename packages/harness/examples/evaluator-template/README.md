# Recording evaluator template

This standalone, typed wheel supplies the `org.example.recording` product evaluator.
It reads verified `application/mcap` evidence through the public harness SDK and
checks that each recording contains at least one message. Rename the distribution,
Python package and reverse-domain namespace before using it for your product.

The declared SDK dependency is `robotics-acceptance-harness>=0.20.0,<0.21`.
The host harness requires contracts 0.18 or newer. An older harness cannot satisfy
this template's dependency, even if a development checkout contains `sdk.py`.
Harness `0.20.0` is currently an unreleased development candidate; install its local
wheel together with the template and matching contracts wheel as described below.

Build from a copy outside any uv workspace:

```sh
scratch=$(mktemp -d)
cp -R packages/harness/examples/evaluator-template "$scratch/template"
uv build --wheel --out-dir "$scratch/wheels" "$scratch/template"
uv venv "$scratch/venv" --python 3.12
uv pip install --python "$scratch/venv/bin/python" "$scratch"/wheels/*.whl
uv pip check --python "$scratch/venv/bin/python"
PYTHONDONTWRITEBYTECODE=1 "$scratch/venv/bin/robotics-acceptance" doctor
```

On Windows use the venv's `Scripts/python.exe` and `Scripts/robotics-acceptance.exe`.
`uv pip install` must run without bytecode compilation; also unset
`PYTHONPYCACHEPREFIX` and start the harness in a fresh interpreter. Development
candidates that are not published require the matching harness and contracts
wheels in the same install command. Do not lower the SDK floor or use `--no-deps`.

An unqualified `doctor` checks discovery only. Running the evaluator also requires
matching scenario/runtime bindings and the wheel receipt chain; see
[the SDK guide](../../docs/evaluator-sdk.md). The installed `RECORD` check and the
released wheel's identity are separate requirements.

`proof/typing_probe.py` is a consumer of the installed typed API. The harness test
`tests/test_evaluator_template.py` builds real wheels in a temporary directory,
installs into a clean environment, checks this consumer with mypy, and exercises
qualified discovery and evaluation. It records wheel hashes and command logs in
an external proof directory; the SDK guide gives the exact invocation.
