from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from hashlib import sha256
from typing import Any

import pytest
from robotics_runtime_contracts import dumps_canonical, loads_mapping

from robotics_acceptance_harness.evaluation import EvaluationError
from robotics_acceptance_harness.evaluator_json import (
    MAX_PACKET_BYTES,
    decode_evaluator_response,
    encode_evaluator_request,
)
from robotics_acceptance_harness.metrics import AssertionEvaluation

NAMESPACE = "org.example.evidence-bytes-json"
IDS = (f"{NAMESPACE}.nonempty", f"{NAMESPACE}.calibrated-error")
DIGEST = "a" * 64
CALIBRATION_DIGEST = "b" * 64
REQUEST_SHA = "c" * 64


def reference(digest: str = DIGEST) -> dict[str, Any]:
    return {
        "uri": f"file:///original-unavailable-root/{digest}.json",
        "sha256": digest,
        "size_bytes": 7,
        "media_type": "application/json",
    }


def request() -> dict[str, Any]:
    return {
        "schema_version": "evaluator-request.v1",
        "run_id": "run-6cfcfcbd-5e82-45b1-a480-4478f367eeea",
        "domain_id": "primary",
        "namespace": NAMESPACE,
        "expected_assertion_ids": list(IDS),
        "method": {
            "implementation": "org.example.calibrated-evidence-json",
            "version": "1",
            "configuration": reference(),
        },
        "documents": {
            role: reference()
            for role in (
                "acceptance_scenario",
                "runtime_manifest",
                "acceptance_run",
                "acceptance_observation",
                "evidence_index",
            )
        },
        "controls": reference(),
        "evidence": [
            {
                "artifact_id": "native-state",
                "kind": "observation",
                "uri": reference()["uri"],
                "media_type": "application/json",
                "sha256": DIGEST,
                "size_bytes": 7,
                "retention_class": "qualification",
            }
        ],
        "locations": [{"sha256": DIGEST, "path": "captured/source.json"}],
    }


def row(identifier: str = IDS[0]) -> dict[str, Any]:
    return {
        "assertion_id": identifier,
        "source": "product",
        "namespace": NAMESPACE,
        "status": "passed",
        "observed_value": 7,
        "unit": "1",
        "evidence_sha256": [DIGEST],
    }


def response(*rows: dict[str, Any]) -> bytes:
    return dumps_canonical(
        {
            "schema_version": "evaluator-response.v1",
            "request_sha256": REQUEST_SHA,
            "assertion_results": list(rows or (row(IDS[0]), row(IDS[1]))),
        }
    )


def decode(raw: bytes, **bindings: Any) -> tuple[AssertionEvaluation, ...]:
    return decode_evaluator_response(
        raw,
        **{
            "request_sha256": REQUEST_SHA,
            "namespace": NAMESPACE,
            "expected_assertion_ids": IDS,
            "allowed_evidence_sha256": {DIGEST, CALIBRATION_DIGEST},
            **bindings,
        },
    )


def test_request_is_deterministic_preserves_original_references_and_does_not_read_them() -> None:
    data = request()
    data["documents"]["acceptance_result"] = reference(CALIBRATION_DIGEST)
    data["locations"].append(
        {"sha256": CALIBRATION_DIGEST, "path": "captured/original-result.json"}
    )
    original = deepcopy(data)

    raw = encode_evaluator_request(data)

    assert raw == encode_evaluator_request(dict(reversed(list(data.items()))))
    assert loads_mapping(raw, source_name="request.json") == original
    assert data == original
    assert b"original-unavailable-root" in raw


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data["documents"].pop("acceptance_observation"),
        lambda data: data["documents"].update({"private_role": reference()}),
        lambda data: data.update({"metric_samples": []}),
        lambda data: data["method"].update({"version": ""}),
        lambda data: data["controls"].update({"sha256": "invalid"}),
        lambda data: data["evidence"][0].update({"size_bytes": -1}),
        lambda data: data["evidence"][0].update({"local_path": "/private/source"}),
        lambda data: data.update({"expected_assertion_ids": []}),
        lambda data: data.update({"expected_assertion_ids": [IDS[0], IDS[0]]}),
        lambda data: data.update({"expected_assertion_ids": ["org.other.result"]}),
        lambda data: data.update({"namespace": "not-a-domain"}),
        lambda data: data["controls"].update({"sha256": CALIBRATION_DIGEST}),
    ],
)
def test_request_refuses_unknown_or_unbound_data(
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    data = request()
    mutate(data)
    with pytest.raises(EvaluationError):
        encode_evaluator_request(data)


@pytest.mark.parametrize(
    "path",
    ["/absolute", "../escape", "a/../b", "a/./b", "a//b", "a/", ".", "a\\b", "a\x00b"],
)
def test_locations_refuse_unconfined_paths(path: str) -> None:
    data = request()
    data["locations"][0]["path"] = path
    with pytest.raises(EvaluationError, match="relative POSIX"):
        encode_evaluator_request(data)


@pytest.mark.parametrize(
    "location",
    [
        {"sha256": DIGEST, "path": "another.json"},
        {"sha256": CALIBRATION_DIGEST, "path": "captured/source.json"},
    ],
)
def test_locations_refuse_duplicate_digest_or_destination(location: dict[str, str]) -> None:
    data = request()
    data["locations"].append(location)
    with pytest.raises(EvaluationError, match="unique"):
        encode_evaluator_request(data)


def test_optional_window_retains_large_native_integers_and_declared_clock() -> None:
    data = request()
    data["window"] = {
        "start_ns": 9007199254740993,
        "end_ns": 18446744073709551615,
        "clock": {"kind": "external", "source_id": "px4-boot"},
        "timestamp_encoding": "native_ns",
    }

    raw = encode_evaluator_request(data)

    assert loads_mapping(raw, source_name="request.json")["window"] == data["window"]
    assert b'"start_ns":9007199254740993' in raw
    data["window"]["end_ns"] = data["window"]["start_ns"]
    with pytest.raises(EvaluationError, match="precede"):
        encode_evaluator_request(data)


def test_window_rejects_unsupported_clock_encoding_and_false_integer() -> None:
    data = request()
    data["window"] = {
        "start_ns": True,
        "end_ns": 2,
        "clock": {"kind": "unknown", "source_id": "px4-boot"},
        "timestamp_encoding": "assumed_host_ns",
    }
    with pytest.raises(EvaluationError):
        encode_evaluator_request(data)


def test_response_explicitly_maps_public_assertions_with_exact_integer_and_evidence() -> None:
    first, second = row(IDS[0]), row(IDS[1])
    first["observed_value"] = 9007199254740993
    second.update(
        {
            "status": "failed",
            "observed_value": 18446744073709551615,
            "message": "selected calibration applied",
            "evidence_sha256": [DIGEST, CALIBRATION_DIGEST],
        }
    )

    actual = decode(response(first, second))

    assert actual == (
        AssertionEvaluation(
            IDS[0],
            "passed",
            9007199254740993,
            "1",
            source="product",
            namespace=NAMESPACE,
            evidence_sha256=(DIGEST,),
        ),
        AssertionEvaluation(
            IDS[1],
            "failed",
            18446744073709551615,
            "1",
            message="selected calibration applied",
            source="product",
            namespace=NAMESPACE,
            evidence_sha256=(DIGEST, CALIBRATION_DIGEST),
        ),
    )


@pytest.mark.parametrize("status", ["error", "skipped"])
def test_unavailable_assertions_remain_null_and_never_become_passed(status: str) -> None:
    unavailable = row(IDS[1])
    unavailable.update({"status": status, "observed_value": None, "message": "offset unavailable"})
    actual = decode(response(row(), unavailable))
    assert actual[1].status == status
    assert actual[1].observed_value is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda item: item.update({"source": "core"}),
        lambda item: item.update({"namespace": "org.other"}),
        lambda item: item.update({"assertion_id": "org.other.accepted"}),
        lambda item: item.update({"status": "incomplete"}),
        lambda item: item.update({"evidence_sha256": []}),
        lambda item: item.update({"evidence_sha256": ["f" * 64]}),
        lambda item: item.update({"evidence_sha256": [DIGEST, DIGEST]}),
        lambda item: item.update({"observed_value": {"hidden": "context"}}),
        lambda item: item.update({"unit": ""}),
        lambda item: item.update({"message": "x" * 4097}),
        lambda item: item.update({"complete": True}),
    ],
)
def test_response_reuses_schema_and_product_ownership_guards(
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    first = row()
    mutate(first)
    with pytest.raises(EvaluationError):
        decode(response(first, row(IDS[1])))


@pytest.mark.parametrize("field", ["status", "coverage", "observations", "complete", "environment"])
def test_worker_cannot_claim_final_result_authority(field: str) -> None:
    data = loads_mapping(response(), source_name="response.json")
    data[field] = True
    with pytest.raises(EvaluationError):
        decode(dumps_canonical(data))


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [row()],
        [row(), row()],
        [row(), row(IDS[1]), row(f"{NAMESPACE}.extra")],
    ],
)
def test_missing_partial_duplicate_or_extra_assertions_cannot_raise_a_verdict(
    rows: list[dict[str, Any]],
) -> None:
    data = {
        "schema_version": "evaluator-response.v1",
        "request_sha256": REQUEST_SHA,
        "assertion_results": rows,
    }
    with pytest.raises(EvaluationError):
        decode(dumps_canonical(data))


@pytest.mark.parametrize(
    "bindings",
    [
        {"request_sha256": "invalid"},
        {"request_sha256": "f" * 64},
        {"namespace": "invalid"},
        {"expected_assertion_ids": ()},
        {"expected_assertion_ids": (IDS[0], IDS[0])},
        {"expected_assertion_ids": ("org.other.result",)},
        {"expected_assertion_ids": IDS[0]},
        {"allowed_evidence_sha256": DIGEST},
        {"allowed_evidence_sha256": {"invalid"}},
        {"allowed_evidence_sha256": set()},
    ],
)
def test_response_refuses_invalid_trusted_bindings(bindings: dict[str, Any]) -> None:
    with pytest.raises(EvaluationError):
        decode(response(), **bindings)


def test_response_sha_binds_original_request_bytes_not_reencoded_data() -> None:
    canonical = encode_evaluator_request(request())
    original = canonical + b"\n"
    data = loads_mapping(response(), source_name="response.json")
    data["request_sha256"] = sha256(original).hexdigest()
    raw = dumps_canonical(data)

    assert decode(raw, request_sha256=sha256(original).hexdigest())
    with pytest.raises(EvaluationError, match="captured request"):
        decode(raw, request_sha256=sha256(canonical).hexdigest())


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema_version":"evaluator-response.v1","schema_version":"evaluator-response.v1"}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b'{"x":1e999}',
        b'{"x":' + b"[" * 70 + b"0" + b"]" * 70 + b"}",
        b'{"x":[' + b"0," * 100_001 + b"0]}",
        b"schema_version: evaluator-response.v1",
        b"\xff",
        b"[]",
    ],
)
def test_response_retains_strict_existing_json_parser(raw: bytes) -> None:
    with pytest.raises(EvaluationError):
        decode(raw)


def test_packet_byte_budget_is_checked_before_response_parse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_parse(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("oversized response reached JSON parser")

    monkeypatch.setattr(
        "robotics_acceptance_harness.evaluator_json.loads_mapping", unexpected_parse
    )
    with pytest.raises(EvaluationError, match="exceeds"):
        decode(b" " * (MAX_PACKET_BYTES + 1))


def test_request_budget_and_response_row_count_are_finite() -> None:
    data = request()
    data["method"]["implementation"] = "x" * (MAX_PACKET_BYTES + 1)
    with pytest.raises(EvaluationError, match="exceeds"):
        encode_evaluator_request(data)
    with pytest.raises(EvaluationError):
        decode(response(*(row(f"{NAMESPACE}.item{i}") for i in range(257))))
