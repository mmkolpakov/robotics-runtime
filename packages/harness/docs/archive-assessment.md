# Archive assessment

This release assesses captured native v2 software or simulation inputs through
the SDK and CLI without starting a workload. Use the matching contracts 0.21.0/
harness 0.22.0 cohort and an admitted execution composition.
[Compatibility](compatibility.md) defines its package and profile boundaries.

The original scenario, pre-run runtime, run context, observation and evidence
index remain immutable. A new acceptance-result.v2 has its own existing
`result_id`, method configuration, software inventory and UTC assessment time.
`original_execution.original_result_sha256` binds the exact baseline result;
the baseline outcome is never replaced by the new outcome.

## Selected method

`evaluate --assessment-controls PATH --original-result PATH` selects captured
method controls and a baseline result. Keep the existing scenario/runtime/run/
evidence arguments and any captured clock-qualified window used by the method. Include
`--otel-metrics` when the selected method declares metrics. The CLI writes the
normal JSON/JUnit outputs to a separate output directory. A baseline requires
explicit controls; initial evaluation may use controls without a baseline.

Controls contain `metric_definitions`, `assertions`,
`evaluator_requirements`, `evidence_policy` and explicit `calibration`.
They are method configuration, not an additional document role.
`validate_assessment_controls` is the contracts SDK validator;
`load_assessment_controls` captures immutable bytes and declared inputs once.
Each input and the total controls/input capture are limited to 8 MiB; declared
sizes are checked before input reads. Calibration selects ArtifactRefs, or
declares `not_applicable`/`unobserved` with a reason. Historical absence remains
unknown and cannot establish a matched comparison.

The core metric method executes the selected assertions, so a changed threshold
changes actual evaluation. It has no calibration implementation and refuses
selected calibration. A product method may consume captured inputs through
`context.assessment_controls.read_input(reference)`; it must bind both original
raw evidence and calibration digests. Reference retention checks consistency,
not that arbitrary code applied a calibration.

Selected evaluator requirements are independent of the original runtime's
evaluator bindings. The [operator trust profile](evaluator-trust.md) authenticates
the selected installed code outside evidence/controls before execution. SDK
`assess_archive(context, run_context, output, ...)` uses the same native evaluator
and public writers; the context holds captured controls and `original_result`.
`load_original_result` validates and hashes the same bounded bytes it captures.

## Qualification and comparison

Use the full retained artifact inventory described by the
[qualification guide](../../contracts/docs/qualification.md). Include one original
and one new result per domain, their separate acceptance-aggregate.v1 documents,
and both method/environment contexts plus actual calibration/evaluator artifacts.
V2 is explicitly selected:

```sh
robotics-contracts qualification statement \
  --schema-version qualification-bundle.v2 \
  --comparison-rule exact_assertion_outcome \
  --artifact KIND:SUBJECT=PATH --output statement.json
```

The artifact option above is an inventory placeholder, not a complete set.
`validate-qualification` without a statement accepts the same explicit version/
rule. With `--statement`, it derives both from the validated predicate and
rejects separate version/rule flags. Matching preserves subject bytes and checks
the actual captured metadata; signature authentication remains the caller's
responsibility.

The in-toto Statement v1 wrapper and subjects are retained, with product
predicateType `https://robotics-runtime-contracts.dev/attestations/qualification-bundle/v2`.
This is not an in-toto Test Result or SLSA VSA predicate. Its archive fields bind
the original outcome, new assessment and actual covered criteria.

`exact_assertion_outcome` compares only a nonempty covered intersection with
the same declared method/configuration, environment, known calibration and
captured-window presence/value. A data-only method does not invent a window.
It compares source, namespace, status, typed observed
value, unit and evidence digests. Changed method/environment/calibration or
unknown coverage produces `not_comparable`; it does not compare whole verdicts.
Missing original required facts remain incomplete.

## Scope

The authenticated [author example](../consumer-examples/evidence-byte-check/README.md)
reads raw counter 7 and a captured offset. Offset 7 produces corrected 0/passed;
offset 6 produces 1/failed; unobserved calibration is incomplete and invalid offset
is error. Its installed fixture retains the original failed result and verifies
bundle2 statement matching. It checks actual write refusal and unchanged bytes
after a byte-preserving copy is mounted read-only at the recorded URI path.

Use explicit read-only bind mounts at recorded paths when moving an archive.
The reader does not rewrite ArtifactRefs or normalize historical ROS documents.
Output belongs in a separate writable directory. UTC provenance and native
measurement clocks remain distinct; no clock relation is inferred.

Physical v2 archive qualification is refused: this path does not establish that
a physical permit was valid at an original trial. Active playback is a new run
with new admission. Sensor calibration accuracy, production SDK/image/BOM
admission and native-operation qualification remain separate product gates.
