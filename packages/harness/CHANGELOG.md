# Changelog

## 0.20.0 (unreleased)

Development candidate; not a published release. Publication requires
`contracts-v0.18.0` and the contracts 0.18 series (`>=0.18,<0.19`).

- Publish public evaluator SDK types and digest-based access to verified local
  evidence. Readers receive a seekable, read-only snapshot; large recordings
  spill to temporary disk and subsequent source-file changes cannot affect it.
- Reuse the existing artifact hash, size and stable-read checks when producing
  snapshots. Report unknown or unavailable local digests as typed input errors.
- Bind scenario robot-description digests to runtime workload metadata before
  observation. Carry pinned extension schemas through execution, evidence,
  receipt, transport and campaign readers and the diagnostic commands.
- Include a product evaluator template and installed-wheel `doctor` verification.
