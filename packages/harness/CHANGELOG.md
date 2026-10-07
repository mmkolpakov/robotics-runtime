# Changelog

## 0.20.0

Requires contracts 0.19 (`>=0.19,<0.20`), with release prerequisite
[contracts-v0.19.0](https://github.com/mmkolpakov/robotics-runtime/releases/tag/contracts-v0.19.0).

- Load the canonical `dataset-manifest.v2` bag model for one or more finalized
  MCAP members. Reject v1 dataset documents in the current execution bundle;
  historical v1 inputs remain associated with the previously published package
  pair.
- Validate the captured dataset document against its recorded digest before
  execution. Preserve immutable metadata and member declarations when the source
  document changes after loading.

## 0.19.2

Requires contracts 0.18 (`>=0.18,<0.19`), with release prerequisite
[contracts-v0.18.3](https://github.com/mmkolpakov/robotics-runtime/releases/tag/contracts-v0.18.3).

- Keep timing evaluation outcomes separate from invalid-input errors. Preserve
  unavailable observations and proven violations through typed results, then
  fold them into acceptance through the existing public status order.
- Add regressions for missing timing samples, invalid timing metadata and the
  distinction between completed timing failures and validation errors.

## 0.19.1

Requires contracts 0.18 (`>=0.18,<0.19`), with release prerequisite
[contracts-v0.18.2](https://github.com/mmkolpakov/robotics-runtime/releases/tag/contracts-v0.18.2).

- Reject missing or mismatched scenario/runtime robot-description bindings when
  loading an execution bundle, before explanation or live observation. Preserve
  optional bindings and leave filesystem/XML admission with the consumer.
- Add optional per-file raw-evidence byte limits to acceptance, aggregation,
  OTLP and trace processing. Preserve existing behavior when no limit is supplied.

## 0.19.0

The first harness release from the `robotics-runtime` workspace requires
contracts 0.18 (`>=0.18,<0.19`). Its release prerequisite is
[contracts-v0.18.1](https://github.com/mmkolpakov/robotics-runtime/releases/tag/contracts-v0.18.1).
The wheel and source distribution remain independently installable.

- Evaluate causal message pairs and connected trace paths, attributing channel
  spans by their declared topic. Fold acceptance and campaign verdicts through
  the canonical status order.
- Recheck expected graph and lifecycle conditions during measurement. Expire
  cached lifecycle state when a GetState request stops answering.
- Evaluate realtime factor in sliding windows, cumulative histogram baselines
  and resets, and interior gaps in delta coverage. Retain proven violations
  when other observations are unavailable.
- Read finalized evidence through bounded, contained file descriptors and retry
  partial or missing inputs to the deadline. Write UTC result timestamps and
  preserve an existing run context when create-run is repeated.
- Accept finalized receipt inventories and digest-pinned extension schemas.
  Verify evaluator sources against receipt and RECORD data and reject external
  bytecode caches.
- Expose HarnessError and HarnessInputError with stable identifiers and exit
  codes. Preserve dependency causes and structured issue paths in diagnostics.
- Ship type information, support Python 3.12–3.14 and relax supported runtime
  dependency ranges.
