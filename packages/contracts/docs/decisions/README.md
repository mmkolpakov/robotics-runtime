# Architecture Decisions

Accepted decisions use the
[MADR](https://adr.github.io/madr/) structure and are kept beside the package
they govern.
The Ruff budget decision also governs the shared workspace gate.

| ADR | Decision |
| --- | --- |
| [0001](0001-version-contracts-independently.md) | Keep one canonical contract set before 1.0 (superseded by 0007) |
| [0002](0002-validate-domain-extensions-offline.md) | Validate domain extensions offline from caller-supplied bytes |
| [0003](0003-separate-structural-and-semantic-validation.md) | Separate structural and semantic validation ownership |
| [0004](0004-separate-device-and-workload-identities.md) | Keep device and workload identities distinct |
| [0005](0005-keep-the-package-domain-neutral.md) | Keep the package domain neutral |
| [0006](0006-separate-transport-qualification.md) | Separate transport qualification from acceptance aggregation |
| [0007](0007-preserve-published-schema-compatibility.md) | Preserve published schema compatibility |
| [0008](0008-test-supported-python-versions.md) | Test the declared Python support range |
| [0009](0009-preserve-deterministic-json-and-exact-byte-bindings.md) | T02: preserve deterministic JSON and exact byte bindings |
| [0010](0010-keep-a-narrow-jsonschema-resolver-adapter.md) | T08: keep a narrow jsonschema resolver adapter |
| [0011](0011-retain-the-pinned-ruff-budget-parser.md) | T09: retain the pinned Ruff budget parser |
