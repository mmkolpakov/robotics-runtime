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
The gate extracts those exact Git sources, contracts fixtures and consumer
examples into a temporary directory. Workspace releases also provide the
harness's regular and live fixtures. It does not install an editable baseline or modify the
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

The reviewed JSON corpus is stored under
`tests/schema_compatibility/fixtures/contracts-v0.18.2/`, bound to published
source `dc02c62897372514537cf241f06dc71b9f960c44`. Its 139-file inventory
classifies every contracts fixture, consumer example, harness fixture and live
fixture. There are 92 public role documents, including 12 expected refusals,
and three composition descriptor contexts. Raw qualification, product,
observation, time-authority and golden assets keep their own classifications
and original byte digests.

Both selected APIs receive the same frozen JSON documents, artifact
descriptors, extension schema bytes and contexts. Neither semantic probe
parses YAML or silently drops an invalid fixture. The 288 current cases cover
document/role validation, all 26 public roles, pinned and legacy extension
behavior, qualification links with 16 contradiction cases, and matching,
missing, mismatched and unpinned robot-description workload bindings. Outcomes
retain acceptance/refusal, exception class, error identifier, JSON path and
message, plus qualification diagnostics and blocked checks.

A separately retained 67-case legacy corpus records values and complete raw
inventory from `contracts-legacy/v0.16.0`. Its old decoder's identity remains
data in the provenance; the decoder is not imported or executed. Alias values
can therefore remain valid semantic witnesses while the current public loader
continues to reject alias syntax. The exact campaign shortfall from commit
`ae89248d2fb7d842766a0c70eeb6380619801974` and the historical alias regression
retain their original byte provenance. The campaign algorithm is not copied
into the checker.

Twenty additional raw/syntax witnesses call each selected package's public
loader and dumper with identical bytes. They cover accepted JSON/YAML scalar
values and typed roundtrips, duplicate keys, aliases, non-core tags,
non-string keys, malformed syntax and non-finite values. Current restrictions
are not retroactive legacy loader requirements. The current workspace gate
reports 375 cases; a legacy-only baseline replays 67 historical semantic cases.

The validators run in separate `python -I -B` processes with the selected source
prepended explicitly and the import origin checked. Input mutation and
unexpected programming/infrastructure exceptions fail the probe; only native
contract errors are expected refusals. Dependencies come from the current
locked development environment. The corpus's stored file hashes and typed
JSON-value hashes are checked before probing. Released raw asset bytes are
checked against their inventory; missing, added or reclassified files require
review. Documentation has no semantic or artifact binding here, so capture
records its observed source bytes separately. The original frozen corpus is
never regenerated by a test or capture command.

`tests/test_schema_compatibility.py` includes old-valid/new-invalid structural
witnesses and mutations that change public semantic behavior while retaining
schema bytes. It also proves that a negative fixture cannot become accepted,
a workload binding refusal cannot disappear, raw fixture changes are detected,
and the historical JSON corpus preserves all 105 original inventory entries.
These finite cases do not prove all Python semantics compatible.

## Source-bound release corpus

The release workflow runs the existing compatibility gate, builds and checks
the archives, then captures the reviewed corpus outside the distribution
directory:

```bash
"$RELEASE_PYTHON" -m scripts.schema_compatibility.snapshot \
  --plan artifacts/release/plan.json --output artifacts/release/corpus
```

The output contains `semantic-inventory.json`, `semantic-documents.json`,
`semantic-contexts.json`, `raw-syntax.json` and `semantic-provenance.json`.
Provenance binds their exact SHA-256 digests and sizes to the release plan's
candidate, commit, tree and contracts source. Capture checks the actual
commit/tree and requires a clean checkout before writing. The local `.codegraph/`
search index is the sole path excluded from that check; untracked importable
files outside it are rejected. The observed
inventory records that candidate source identity and
retains the frozen baseline provenance plus the 105-file historical inventory.
The semantic files contain all 355 current and historical contexts. Historical
release witness identifiers use a separate `historical/` namespace to preserve
distinct cases without collisions; document values and raw digests stay exact.
The 20 raw/syntax witnesses remain separate.

The workflow hands these exact files to the GitHub release job, attests and
verifies them with the distribution assets, and leaves the PyPI package
directory restricted to wheels and sdists. Capture refuses to overwrite an
existing output directory.

This snapshot records JSON semantics and link outcomes with separate syntax
witnesses. Raw artifact integrity and signature verification remain independent
checks; semantic JSON is never substituted for signed or digest-bound bytes.

The digest snapshot remains an independent accidental-change tripwire. An
intentional digest update requires this gate, relevant consumer tests and release
notes, or a new schema major and migration notes for a breaking change. Editing
the snapshot cannot change the released Git baseline. The bundler retains its
historical byte reproduction test; forward checks use D10 compatibility instead
of insisting on exact equality that would prohibit allowed additive changes.
