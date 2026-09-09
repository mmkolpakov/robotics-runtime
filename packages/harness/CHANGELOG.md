# Changelog

## 0.19.0 (unreleased)

Candidate for the first harness release from the shared `robotics-runtime`
workspace. It uses the published `contracts-v0.17.0` release and requires the
contracts 0.17 series (`>=0.17,<0.18`).
The distribution remains independently installable outside the workspace.

- Use an explicit ROS clock QoS and exercise live observation against ROS 2
  Jazzy. Re-evaluate expected graph and lifecycle conditions during measurement.
- Separate unavailable timing conclusions from proven policy violations. Bound
  realtime factor over the measurement interval and sliding windows; preserve
  known deadline exceedances when other samples are missing.
- Evaluate cumulative histogram windows from recorded baselines and resets,
  retaining conservative quantile bounds and measured event counts. Count
  interior gaps in delta coverage instead of treating them as observations.
- Fold acceptance and campaign verdicts consistently with contracts. Preserve
  skipped checks in JUnit and document why offline evaluation is incomplete.
- Reject malformed OTLP objects with command diagnostics and distinct input-error
  exit codes. Keep original failure causes when writing diagnostics also fails.
- Retry finalized evidence reads to their deadline, use UTC result timestamps
  alongside monotonic durations, and retain artifact digests over original bytes.
- Verify installed evaluator sources against qualified receipt and RECORD data;
  reject external bytecode caches. Allow qualified wheels to share a namespace
  and restore import state when evaluator iteration is interrupted.
- Ship `py.typed`, support Python 3.12–3.14, relax supported runtime dependency
  ranges, and use standard-library and protobuf helpers with equivalence checks.

Release publication remains conditional on the required reviews, hosted checks,
clean installation of wheel and sdist, and the signed release workflow.
