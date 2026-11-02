# Assessment controls and archive result versions

An archive reassessment produces a new result from retained execution evidence.
Keep the original scenario, runtime manifest, observation and result as v2
documents with their original bytes, digests and signatures. Do not relabel them
as v3 or rewrite them to describe the later evaluator.

`acceptance-result.v3` describes the new assessment. It reuses the v2 execution,
profile, observation and method bindings and adds explicit OCI evaluator
declarations. `assessment.v1` is an internal schema resource for those declarations
and controls, not a new public document role or execution-schema family.
The existing catalog retains its canonical defaults and lists result v3 as an
additional supported version.

## Select the controls format explicitly

The public Python API is
[`validate_assessment_controls(controls)`](../src/robotics_runtime_contracts/assessments.py).
It validates the supplied mapping offline without executing an evaluator.

Controls with `schema_version: assessment-controls.v1` use the
`urn:robotics-runtime-contracts:v1:internal:assessment#/$defs/assessmentControls`
schema fragment. Their evaluator requirements contain OCI declarations.
Controls without `schema_version` retain the legacy format and wheel declarations.
An unknown, empty or null marker is rejected.

An archive assessment using result v3 requires marked controls; a result v2
requires legacy controls. Crossed versions are rejected even when their
evaluator declaration lists are empty. The selected
`evaluation.method.configuration` artifact reference binds the exact controls
bytes by SHA-256 and size. Preserve those bytes; a reserialized mapping is not
the same retained artifact. Mapping validation alone does not verify that binding.

## Preserve assertion ownership and missing outcomes

Each OCI declaration specifies its namespace, image execution subject and
nonempty `expected_assertion_ids`. Every expected ID belongs to exactly one
declared evaluator. Each product result must use that exact owner's namespace;
a shared namespace prefix is insufficient. Core and OCI assertion IDs are disjoint.

Coverage accounts for every expected assertion as covered or uncovered.
A covered assertion requires an observed product outcome and retained evidence.
A missing outcome must stay uncovered and unevaluated. It prevents a `passed`
result. Omitting it from coverage is a validation error.

## Validation and qualification boundaries

Individual result validation checks data and cross-field invariants. It does not
admit an image or prove evaluator execution. The high-level harness CLI refuses
marked controls. OCI evaluator execution and qualification are unsupported;
neither an image digest nor a valid declaration supplies that authority.

A `qualification-bundle.v1` cannot admit result v3. The explicit archive
`qualification-bundle.v2` path pairs original v2 results with new v3 assessments,
preserving original-result digest links and controls-version checks. This
data-model pairing does not bypass the OCI qualification refusal. See the
[qualification reference](qualification.md) for retained-artifact validation.
