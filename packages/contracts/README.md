# Robotics Runtime Contracts

[![CI](https://github.com/mmkolpakov/robotics-runtime-contracts/actions/workflows/ci.yml/badge.svg)](https://github.com/mmkolpakov/robotics-runtime-contracts/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Canonical, machine-verifiable contracts for portable robotics executions.

This package defines the boundary shared by product repositories, runtime
infrastructure, and acceptance tooling. It validates requested scenarios,
observed runtimes, evidence, qualification inputs, and verdicts. It does not
launch ROS 2, choose a simulator, collect telemetry, or contain product logic.

## Architecture

```mermaid
flowchart LR
    product["Product repository"] --> infra["Runtime infrastructure"]
    infra --> execution["ROS 2 execution"]
    execution --> harness["Acceptance harness"]
    harness --> evidence["Evidence and verdict"]
    contracts["Runtime contracts"] -. validates .-> product
    contracts -. validates .-> infra
    contracts -. validates .-> harness
```

The contracts are independent of a particular robot or product. They describe
ROS 2 execution, security and timing concepts, including implementation-specific
constraints. Provider identities are recorded as data or namespaced extensions;
they do not select a schema.

## Install

Python 3.12 through 3.14 is supported. Install a wheel from a tagged
[GitHub Release](https://github.com/mmkolpakov/robotics-runtime-contracts/releases),
or create a development environment:

```bash
uv sync --locked --all-groups
```

Release assets include build-provenance attestations. See
[SUPPLY_CHAIN.md](SUPPLY_CHAIN.md).

## CLI

Validate JSON or YAML using its declared `schema_version`:

```bash
robotics-contracts validate scenario.yaml
```

Resolve reviewed RFC 7396 overlays and retain their origin trace:

```bash
robotics-contracts scenario resolve base.yaml \
  --overlay camera.yaml \
  --overlay limits.yaml \
  --output resolved.yaml \
  --trace-output resolution-trace.json
```

Validate a complete, digest-linked qualification set:

```bash
robotics-contracts validate-qualification \
  --artifact scenario:scenario.json=scenario.json \
  --artifact acceptance_run:acceptance-run.json=run.json \
  --artifact runtime_manifest:runtime-manifests/main.json=runtime.json \
  --artifact domain_result:results/main.json=result.json \
  --artifact acceptance_aggregate:acceptance-aggregate.json=aggregate.json
```

Use `--quiet` for gates and `--format json` for stable machine-readable
diagnostics. `describe` reports a schema identifier and digest, `diff` emits an
RFC 7396 merge patch, and `permit init --subject-digest ...` creates an unsigned
physical-execution permit for an external signing workflow.

## Python API

```python
from robotics_runtime_contracts import (
    schema_for_role,
    schema_registry,
    validate_document,
    validate_role,
)

validate_document(document)
validate_role(document, "acceptance_scenario")
print(schema_for_role("runtime_manifest"))
registry = schema_registry()
```

Validation is offline, does not mutate inputs, and rejects non-finite numbers.
It reports the first failure; structural and semantic document errors normally
include a JSON path, while qualification-link and some input errors do not.
The package exports `worst_status()` for consumers to share status-folding
rules; this does not mean every consumer already uses it.

## Contract Set

Release 0.16 publishes one catalogued `v1` contract set. These identifiers are
not compatible with every historical `v1` document. The
machine-readable source of truth is
[`catalog.v1.json`](src/robotics_runtime_contracts/schemas/catalog.v1.json).

| Area | Public roles |
| --- | --- |
| Execution | scenario, run, observation, result, aggregate, campaign |
| Runtime | runtime manifest, model manifest, dataset manifest |
| Evidence | evidence index, recording summary, artifact receipt |
| Qualification | profile, conformance result, bundle, policy |
| Physical safety | execution permit and verification |
| Cross-domain transport | channel, observation, clock relation, causal chain, qualification result |

Every public document uses JSON Schema Draft 2020-12, declares a
`schema_version` ending in `.v1`, rejects unknown root fields, and has an ID in
the `urn:robotics-runtime-contracts:v1:*` namespace. Internal schema resources
exist only to remove duplication and are not document roles.

## Extensions

Scenario extensions can use digest-pinned schemas without changing the common
contract. This validation currently applies only to acceptance scenarios;
`extensions` in other document roles do not receive the same schema checks.
Extension schemas are interpreted as Draft 2020-12. Extension keys use
reverse-domain namespaces such as
`org.example.sorting`; schema bytes are supplied by the caller and are never
fetched from the network.

```python
validate_document(
    scenario,
    extension_schemas={
        "https://schemas.example.org/sorting.v1.schema.json": schema_bytes,
    },
)
```

Promote an extension into the common catalog only after it has reusable
semantics and evidence from more than one domain.

## JSON and YAML input

Documents are UTF-8 mappings with string keys and finite JSON values. Files
ending in `.json` are parsed strictly as JSON, without a YAML fallback;
`.yaml`/`.yml` select YAML. For unnamed input, standard input, and other suffixes,
a leading `{` or `[` selects strict JSON and other input selects YAML. Pass a
YAML `source_name` to `loads_mapping` when using YAML flow syntax such as
`{key: value}`. Duplicate keys are rejected in both formats, including nested
objects and escaped spellings of the same JSON key. Digest-pinned extension
schemas use the same strict JSON parser.

The YAML loader uses the [YAML 1.2 core scalar rules](https://yaml.org/spec/1.2.2/#1032-tag-resolution):
dates and timestamps stay strings; `yes`, `no`, `on`, `off`, `1:30`, `0b10` and
`1_000` stay strings; only the core `true`/`false` spellings become booleans.
`010` is decimal 10; `0o10` is octal 8 and `0x10` is hexadecimal 16. `1.10` and
`1e2` are numbers; quote them when they represent textual versions or IDs.
Non-finite numbers, non-string keys, non-core tags, aliases (including recursive
and merge aliases), and multiple YAML documents are rejected. `<<` has no merge
semantics. YAML output quotes strings using the same scalar rules and emits no
aliases, so reading a written document preserves its JSON values.

Each contract document or extension schema is limited to 8 MiB of UTF-8 input,
64 node levels (root at level 1), and 100,000 nodes, counting mapping keys and
values. File and stdin reads stop at the byte limit plus one sentinel byte.
These bounds apply to document loaders, not retained raw evidence files.
Limit failures use `input.limit_exceeded`, duplicates use `input.duplicate_key`
with the member path, and aliases use `input.yaml_alias`. Other malformed input
uses `input.parse_failed`; non-finite values use `input.non_finite_number`.

## Errors and resource paths

Expected validation and document-operation failures inherit from the public
`ContractError`, which remains a `ValueError`. Existing specialized exception
classes and their constructor signatures remain available. Every contract
error has an `error_id` and a `json_path` (`None` when no document location
applies). The CLI keeps its JSON diagnostic envelope
`{"error": {"error_id": "...", "message": "...", "path": "..."}}`; `path` is
omitted when unavailable. Schema diagnostics use jsonschema's `best_match`,
including nested `anyOf`/`oneOf` errors, so the chosen message can change. See
[jsonschema's selection rules](https://python-jsonschema.readthedocs.io/en/stable/errors/#best-match-and-relevance).

CLI exit codes are 0 for success, 1 for invalid input, I/O failures or internal
errors, and 2 for invalid arguments (including conflicting paths and malformed
artifact/extension options). I/O errors use `input.io_error`; unexpected
exceptions use `internal.error` without a traceback. Python I/O APIs retain
their normal `OSError` behavior. Library programming errors are not converted
to validation failures. `--help` and process interrupts retain normal behavior.
All CLI file inputs and outputs expand `~` before accessing the filesystem.

Error families include `schema.validation_failed`, `schema.unknown`,
`schema.role_unknown`, `schema.reference_invalid`, `semantic.validation_failed`,
`extension.validation_failed`, `qualification.invalid`,
`qualification.unknown_domain`, `qualification.unknown_channel`,
`provider.requirements_unsatisfied`, `receipt.validation_failed`,
`clock.evidence_invalid`, `status.invalid`, `input.parse_failed`,
`input.non_finite_number`, `input.invalid_timestamp`, `input.invalid`,
and `cli.arguments_invalid`. Extension references resolve offline; dangling or
non-terminating references encountered during validation are extension errors.
Timestamp comparisons share one offset-aware parser; timestamp format
validation remains the responsibility of the contract schema.

`schema_dir()` and `schema_path()` still return `pathlib.Path` objects. For
zip imports, `importlib.resources.as_file` extracts the schema directory once
and its context stays open until process exit; an `atexit` handler removes the
temporary directory, following the
[resource context lifetime](https://docs.python.org/3/library/importlib.resources.html#importlib.resources.as_file).
Callers can retain these paths within the process without
adopting a context-manager API. Paths must not be persisted for another process.

## Version Policy

Known consumers include the acceptance harness and runtime infra. They use
different contract generations; see the dated consumer table in
[COMPATIBILITY.md](COMPATIBILITY.md) and the
[0.15 to 0.16 migration guide](docs/migrations/0.15-to-0.16.md).
Published schema names now permit only additive changes; breaking changes
require a new schema major and migration notes. The structural compatibility
gate is planned, so published schema changes remain deferred. Released tags
and artifacts remain immutable. See [CHANGELOG.md](CHANGELOG.md).

HIL and real-target contracts are observation-only. A valid document is not an
authorization to actuate hardware and is not proof that a device or accelerator
has been qualified.

## Development

```bash
uv sync --locked --all-groups
uv run pre-commit run --all-files --show-diff-on-failure
uv run pytest
uv build --no-sources
```

Consumer examples live in [`consumer-examples/`](consumer-examples/).
Contributions must follow [CONTRIBUTING.md](CONTRIBUTING.md), and security
reports must follow [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
