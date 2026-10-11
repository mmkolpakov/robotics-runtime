# Native archive example

This example records a software counter transition, then evaluates its retained
observations through the installed public CLIs. Use this release's contracts
0.21.1 / harness 0.22.0 cohort with explicit native v2 roles. The two Python files
use standard Python and the public command-line
interfaces, with no internal package imports or test fixtures.

The producer creates scenario and pre-run runtime inputs, an immutable run
context, native state bytes, attributed scalar metrics and a separate captured
observation. Model identity is recorded from the exact bytes consumed before
parsing. Command acceptance, native final state and postcondition are separate
observations. The evaluator checks the attributed scalar criteria and retained
source bindings; it does not control an SDK.

With the selected package environment activated:

```bash
python consumer.py --output native-software
python consumer.py --simulation --output native-simulation
```

The consumer invokes validation, evaluation, JSON/JUnit output, aggregation,
qualification validation, statement creation and statement matching. It checks
that original archive files retain their hashes. Output is a JSON report naming
the archive, result, JUnit, aggregate and qualification statement.

The simulation option executes a small discrete counter model. Its measurement
clock is actual system UTC; model steps are separate. This example does not
qualify a robot, an external simulator SDK, rendering or physical operation.
The statement is unsigned; matching it checks the listed bytes and links.

Each assessment writes evaluation-method.json and evaluation-environment.json.
These identify actual configuration and software inventory without random
process IDs, local paths or assessment timestamps. Installed distributions are
reported in a canonical sorted inventory; this is environment context, not
cryptographic interpreter, image or installed-code authentication. Those proofs
belong to the release composition and evaluator trust checks. UTC provenance dates remain
separate from a captured clock-qualified integer measurement window. The built-in
OTLP metric method requires unix_ns. Native-clock product assessments use
native_ns without an invented UTC conversion.

To inspect negative outcomes, run the producer with --omit condition,
--invalid terminal, --error 7, --no-criteria or --all-not-applicable, then pass
its reported inputs to robotics-acceptance evaluate. Missing or invalid required
coverage and absent criteria are incomplete. An accepted and completed command
with a failing postcondition is failed. Measured zero remains a valid value.

V1 canonical role defaults and signed document bytes retain their meanings.
Native v2 scenario/runtime/observation/result versions are explicit opt-ins.
One original run and its assessment chain reuse acceptance-run.v1,
acceptance-aggregate.v1 and qualification-bundle.v1. Independent archive
re-evaluation uses the separate [archive assessment API](../../../harness/docs/archive-assessment.md);
v2 physical qualification remains unsupported.

Nanosecond values in the document files are exact JSON integers on the Python
path. JavaScript consumers preserve the files or payload text and pass window
arguments as decimal strings or bigint. They must not parse and re-emit those
documents through JSON.parse with JavaScript Number: Unix nanoseconds exceed its
safe integer range. The host rejects numeric window arguments; the six read-only
MCP tools forward exact files and return worker payloads as text.
