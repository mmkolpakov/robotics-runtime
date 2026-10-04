# Published schema compatibility

`scripts/check_schema_compatibility.py` compares current contracts with the
latest stable `contracts-v*` tag. It verifies tag metadata, extracts published
schemas and fixture bytes from Git objects, and applies the bounded D10
structural rules. See the package's
[gate policy](../packages/contracts/docs/schema-compatibility.md) for the
supported changes and history prerequisites.

Semantic probes receive the same reviewed JSON values and contexts. They do
not decode semantic YAML, select only valid fixtures, or substitute the
candidate's loader for the baseline. The frozen corpus in
`tests/schema_compatibility/fixtures/contracts-v0.18.2/` records source
`dc02c62897372514537cf241f06dc71b9f960c44`. Its 139-file inventory covers
contracts fixtures, consumer examples, harness fixtures and live fixtures;
every file has an explicit classification and original byte digest. It contains
92 role documents, including 12 expected refusals, and three composition
descriptors. Raw product assets, qualification inputs and observation evidence
retain their separate classifications and byte identities.

There are 288 current contexts: document and role validation, digest-pinned
extensions and their refusals, qualification links and contradictions, and
robot-description workload bindings. Another 67 frozen historical value cases
retain the legacy `v0.16.0` corpus, including alias values. Its former decoder
is identified by provenance but is no longer executed or a direct dependency.
The campaign shortfall and alias witnesses retain their original provenance.

A separate 20-case raw/syntax corpus calls the selected package's public loader
and dumper. It preserves expected JSON/YAML acceptance, refusal, JSON scalar
types and roundtrips. These bytes are identical for both probes; current syntax
restrictions are not applied retroactively to legacy YAML. The full workspace
comparison currently reports 375 cases. The legacy-only fallback reports its
67 semantic cases.

Baseline and candidate run in separate `python -I -B` processes with explicit
source selection and checked import origins. Unexpected exceptions, changed
inputs, changed outcomes, missing inventory entries and altered retained asset
bytes require review. Outcomes include error identifiers, paths, messages and
qualification diagnostics with blocked checks. Integers retain their Python
JSON precision; comparison distinguishes booleans, integers and floats.

Release builds save a source-bound inventory, JSON documents, contexts, raw
witnesses and provenance as five JSON assets beside the distributions. They
are attested and verified release assets, outside PyPI wheels and sdists.
Documentation bytes are recorded from that source separately because they have
no semantic or artifact binding in the corpus. Original fixture and evidence
bytes are never rewritten. This finite API comparison complements raw artifact
and signature verification; it does not establish universal compatibility.
