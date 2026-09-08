# Qualification validation

Use the public `robotics_runtime_contracts.qualification` module for file-based
qualification and for inspection of supplied artifact descriptors.

```python
from robotics_runtime_contracts.qualification import inspect_qualification_artifacts

report = inspect_qualification_artifacts(specifications, extension_schemas=extensions)
for diagnostic in report.diagnostics:
    print(diagnostic.check, diagnostic.subject_name, diagnostic.error_id, diagnostic.message)
print(report.blocked_checks)
metadata = report.metadata()  # raises QualificationError if the report is not valid
```

`specifications` is a sequence of `KIND:SUBJECT=PATH` strings. Paths may be absolute
or relative to the working directory and `~` is expanded. `extension_schemas` is
an optional mapping from schema URI to UTF-8 schema bytes, used for scenario
extensions. Qualification never downloads an extension or a retained artifact.

Each file is opened once. Contract documents are parsed under the document size
limit; raw recordings, packages, and other retained bytes are hashed in 1 MiB
chunks without that limit. SHA-256 and size describe the exact bytes read. A
recording's embedded format checks remain the recording producer's responsibility;
qualification checks its links, retained size, and digest.

`validate_qualification_artifacts` is the raising convenience API returning the
same run ID, aggregate timestamp and sorted artifact metadata as `report.metadata()`.
Qualification statement production uses this file-based API. It does not hash a
reserialized document or infer a successful verdict from missing evidence.

## Subjects and domains

Subject labels are portable logical names, independent of filesystem basenames.

| Artifact kind | Subject | Binding |
| --- | --- | --- |
| scenario | `scenario.json` | Exactly one scenario |
| acceptance_run | `acceptance-run.json` | Exactly one run |
| acceptance_aggregate | `acceptance-aggregate.json` | Exactly one aggregate |
| runtime_manifest | `runtime-manifests/<domain_id>.json` | Run domain, not the numeric ROS domain ID |
| domain_result | `results/<domain_id>.json` | Same run domain and the document's `domain_id` |
| evidence_index | `evidence-indexes/<domain_id>.json` | Evidence for the same result domain |
| recording_summary | `recording-summaries/<label>.json` | Linked by digest from evidence; label need not be a domain |

Runtime, result and evidence-index subject sets must each equal the run's domain
set. Subjects must be globally unique, use the canonical lowercase path syntax,
and contain neither `..` nor `//`. `ARTIFACT_ROLES` and `RAW_ARTIFACT_KINDS` expose
the supported kinds as read-only collections. Additional artifacts depend on
scenario bindings, transport, authorization and retained evidence; the five
principal documents alone are not generally a complete set.

## Diagnostic boundaries

`QualificationReport` contains typed artifacts and diagnostics, the run ID and
aggregate timestamp when available, and named `blocked_checks`. `valid` is true
only if identity is available, diagnostics are empty, and no check is blocked.

Inspection collects failures from every independently loaded document. If any
load or document validation fails, link checks are blocked. With valid documents,
it collects independent run, domain and binding failures. Each individual document
validator or binding family stops at its first dependent failure. A missing domain
set blocks checks that index those domains; aggregate bindings and available
evidence identities can still be checked. This report is not a list of every
possible consequence of malformed input.

`QualificationError` retains the first error's message, identifier and optional
path, with all diagnostics and blocked checks attached. CLI `--format json`
returns them in `error.diagnostics` and `error.blocked_checks`; text output prints
the additional diagnostics too. Invalid arguments retain exit code 2; invalid
documents and links return 1. Validation metadata outputs cannot replace artifact
or extension-schema inputs.

`QualificationArtifact` can also be supplied to `inspect_qualification_documents`
or `validate_qualification_documents`. Those functions revalidate descriptors and
documents before checking links. They have no file paths and cannot verify that a
supplied digest describes a file. Use file-based qualification for statement
production or when claiming that metadata binds retained bytes.
