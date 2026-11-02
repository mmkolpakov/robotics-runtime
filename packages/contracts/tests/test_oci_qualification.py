from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import pytest

from robotics_runtime_contracts._qualification_archive import _coverage
from robotics_runtime_contracts._qualification_native import _assessment_registry
from robotics_runtime_contracts.qualification import QualificationArtifact, QualificationError
from tests.test_oci_assessment_v3 import OCI, controls


def test_archive_coverage_keeps_missing_oci_ids_uncovered() -> None:
    identifier = OCI["expected_assertion_ids"][0]
    raw = json.dumps(controls()).encode()
    digest = sha256(raw).hexdigest()
    artifact = QualificationArtifact("other_evidence", "method.json", digest, len(raw), None, raw)
    result: dict[str, Any] = {
        "schema_version": "acceptance-result.v3",
        "evaluators": [deepcopy(OCI)],
        "assertion_results": [],
        "evaluation": {
            "method": {"configuration": {"sha256": digest, "size_bytes": len(raw)}},
            "coverage": {
                "covered_assertions": [],
                "uncovered_assertions": [{"assertion_id": identifier, "reason": "unavailable"}],
            },
        },
    }
    context: Any = SimpleNamespace(
        results={"primary": SimpleNamespace(document=result)},
        grouped={"other_evidence": [artifact]},
        evidence_indexes={"primary": SimpleNamespace(document={"artifacts": []})},
    )
    covered, expected, rows = _coverage(context, "primary")
    assert covered == set()
    assert expected == {identifier}
    assert rows == {}
    result["evaluation"]["coverage"]["uncovered_assertions"].clear()
    result["evaluation"]["coverage"]["covered_assertions"].append(
        {"assertion_id": identifier, "evidence_sha256": ["a" * 64]}
    )
    with pytest.raises(QualificationError, match="classify each actual criterion"):
        _coverage(context, "primary")


def test_assessment_environment_is_identical_across_domains() -> None:
    reference = {"sha256": "a" * 64, "size_bytes": 20}
    evaluation: dict[str, Any] = {
        "method": {"implementation": "fixture", "version": "1", "configuration": dict(reference)},
        "environment": dict(reference),
    }
    first = SimpleNamespace(document={"evaluation": deepcopy(evaluation)})
    second = SimpleNamespace(document={"evaluation": deepcopy(evaluation)})
    context: Any = SimpleNamespace(results={"first": first, "second": second})
    _assessment_registry(context)
    second.document["evaluation"]["environment"]["sha256"] = "b" * 64
    with pytest.raises(QualificationError, match="assessment environment"):
        _assessment_registry(context)
