# Published schema compatibility gate

Run from the workspace root after synchronizing its locked development environment:

```bash
uv run --no-sync python scripts/check_schema_compatibility.py
uv run --no-sync pytest tests/test_schema_compatibility.py
```

CI runs this gate explicitly and the local `schema-compatibility` pre-commit hook
runs it on every commit, including changes to Python semantics alone. Failure is
reported as `review_required` with the affected schema/path or fixture. There is
no override flag. A passing gate establishes the rules below and the recorded
regression cases, not general JSON Schema implication or universal behavioral
compatibility. New unsupported cases need an explicit policy/code review and a
proof with regression tests, or the new-schema-major migration path.

## Published baseline and history

The baseline comes from Git blobs, never `docs/schema-digests.json` or the bundled
refactor snapshot. Fetch full history and tags before running the gate:

```bash
# For a shallow clone only:
git fetch --unshallow origin
git fetch origin --tags
git fetch --no-tags https://github.com/mmkolpakov/robotics-runtime-contracts.git \
  refs/tags/v0.16.0:refs/tags/contracts-legacy/v0.16.0
```

The highest numeric stable `contracts-vMAJOR.MINOR.PATCH` tag is selected;
prereleases do not replace the stable baseline. Tag and package metadata must
agree. Before the first workspace release, the fallback is the actual published
[`v0.16.0`](https://github.com/mmkolpakov/robotics-runtime-contracts/tree/v0.16.0)
under `contracts-legacy/v0.16.0`, peeled commit
`0c2c0f4d37ef97fc6818ac61c66cdcef0bec3940`. A moved legacy tag, missing objects or
shallow history fails. The gate does not fetch automatically; an offline clone
cannot detect tags absent from its local namespace, so refreshing tags is an
explicit developer prerequisite. CI uses checkout depth zero and fetches the
legacy tag separately. Tag protection and release provenance remain release
workflow/repository responsibilities.

Legacy source is read from `src/`; workspace releases use `packages/contracts/src/`.
The gate extracts those exact Git sources and released `tests/fixtures` into a
temporary directory. It does not install an editable baseline or modify the
checkout, package versions, schemas, fixtures or digests.

## Automated D10 domain

All roots must declare Draft 2020-12 and pass its metaschema. An offline
`referencing.Registry` owns URI/pointer resolution. Every resolved object must
occupy a schema location identified by the Draft 2020-12 specification; instance
data dictionaries are not importable schemas. Boolean targets are supported.
Unknown keywords, anchors, dynamic references, nested IDs/dialect declarations,
unresolved references and cycles (also in unused definitions) fail closed.
Expansion depth is limited to 128 schema nodes; each comparison token is limited
to four million characters. Exceeding these limits requires review.

Existing catalog roles and their mappings, resource filenames, root `$id` values,
internal resource inventory and `contract_set` are retained. New validated roles
and resources are allowed. Static aliases in `$defs` can be reorganized when all
reachable resolved constraints are preserved. Internal definition names are not
compared as independent public roles; unused definitions are checked for the
supported schema domain, not for assertion equivalence. Digest review still
covers every byte, including unused definitions.

The comparison keeps reference siblings adjacent, rather than converting them
to `allOf`. The distinction matters for
[`unevaluatedProperties` and adjacent annotations](https://json-schema.org/draft/2020-12/json-schema-core#section-11.3).
Literal instance data in `const`/`enum` retains every key and JSON scalar type;
Python equality must not conflate `true` and `1`.

| Change | Automated result |
| --- | --- |
| `description`, `title`, `examples` at schema locations | Allowed |
| Optional property in a locally closed object, without pattern/evaluation ambiguity | Allowed in a positive context |
| Input enum superset retaining each old typed value | Allowed in a positive context |
| New role/resource with the supported schema domain | Allowed |
| Removed/renamed role or property, changed type/const/ID, new required or conditional, narrowed bounds/pattern/enum, newly closed object | Rejected |
| Output enum additions | Rejected |
| Other changes, including unsupported keywords or ambiguous widening | Explicit review required |

Input roles are `acceptance_scenario`, `qualification_profile`, `runtime_manifest`,
`dataset_manifest` and `model_artifact_manifest`; scenario/runtime internal cores
inherit that direction. Other roles are conservative output/unknown contexts.
A shared enum used by an output role remains frozen even when also used by an
input role.

An optional property is not automatically safe in an open object: an old object
can already contain that key with a value rejected by the new property schema.
`not`, `if`, `contains` and other nonmonotone contexts freeze assertion changes.
`oneOf` is also frozen unless every branch is an object requiring the same
discriminator property with a distinct string `const`, before and after the
change. This proves branches cannot overlap. Each branch must still pass the
ordinary D10 comparison, which rejects changing the discriminator or adding a
required property. Negative enclosing contexts remain frozen.
Changes at an annotation-dependent `unevaluatedProperties` or
`unevaluatedItems` node also require review. Even mathematically plausible
widenings outside the explicit table are not guessed by this tool. The finite
keyword domain and these conservative rules are intentional, not a general
schema solver.

## Semantic regressions and byte tripwires

The released public loader parses every JSON/YAML file directly under a released
fixture `valid/` directory. The released public `validate_document` must accept
each document before the current public API receives the same parsed JSON value.
This exercises schema validation, Python semantic checks and extension checks;
no invalid baseline case is silently discarded. The validators run in separate
`python -I -B` processes with the selected source prepended explicitly and the
import origin checked. Input mutation fails the probe. Dependencies come from
the current locked development environment; incompatible historical runtime
dependencies fail explicitly and need review, rather than substituting the
current validator for the old one.

The initial corpus contains 15 published valid fixtures plus the exact legacy
campaign shortfall regression from commit
`ae89248d2fb7d842766a0c70eeb6380619801974`. Its frozen copy and byte provenance live
under `tests/schema_compatibility/fixtures/`. It asserts that the previously
valid `failed` verdict with two passed runs and a minimum of three remains valid.
The campaign algorithm is not copied into this checker. Future semantic fixes
should add historical valid witnesses here when not already covered by released
fixtures. This finite corpus cannot prove all Python semantics compatible.

`tests/test_schema_compatibility.py` includes old-valid/new-invalid witnesses for
required fields, removed properties, types, typed enums/constants, patterns,
ranges, closed objects, conditionals and evaluated annotations. A separate
mutation changes only the public semantic dispatch while retaining all schema
bytes; the public API probe must fail on the campaign witness.

The digest snapshot remains an independent accidental-change tripwire. An
intentional digest update requires this gate, relevant consumer tests and release
notes, or a new schema major and migration notes for a breaking change. Editing
the snapshot cannot change the released Git baseline. The bundler retains its
historical byte reproduction test; forward checks use D10 compatibility instead
of insisting on exact equality that would prohibit allowed additive changes.
