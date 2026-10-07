from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from robotics_runtime_contracts.errors import ContractError

from robotics_acceptance_harness.errors import HarnessInputError
from robotics_acceptance_harness.metrics import evaluate_metric_assertions
from robotics_acceptance_harness.signalflag_emissions import MetricBinding, read_emissions

BINDINGS = {("motion", "speed"): MetricBinding("org.example.speed", "m/s")}


def read(source: bytes, **kwargs: Any) -> tuple[Any, ...]:
    return read_emissions(source, bindings=BINDINGS, timestamp_basis="unix_ns", **kwargs)


@pytest.mark.parametrize(
    "source",
    [
        b'{"$metadata":{"topic":"motion","timestamp":1},"$data":{"speed":1,"speed":2}}',
        b'{"$metadata":{"topic":"motion","timestamp":1},"$data":{"speed":NaN}}',
        b'{"$metadata":{"topic":"motion","timestamp":1},"$data":{"speed":Infinity}}',
        b'{"$metadata":{"topic":"motion","timestamp":1},"$data":{"speed":1e999}}',
        b'{"$metadata":{"topic":"motion","timestamp":1},"$data":',
        b"$metadata: {topic: motion, timestamp: 1}\n$data: {speed: 1}",
        b"\xff",
        b"{}\n\n{}",
    ],
)
def test_strict_json_parser_refuses_invalid_original_bytes(source: bytes) -> None:
    before = sha256(source).hexdigest()
    with pytest.raises((ContractError, HarnessInputError)):
        read(source)
    assert sha256(source).hexdigest() == before


@pytest.mark.parametrize("timestamp", ["null", "true", "1.0", '"1"', "-1"])
def test_selected_timestamp_is_exact_nonnegative_integer(timestamp: str) -> None:
    source = (
        '{"$metadata":{"topic":"motion","timestamp":' + timestamp + '},"$data":{"speed":1}}'
    ).encode()
    with pytest.raises(HarnessInputError, match="integer Unix-ns"):
        read(source)


@pytest.mark.parametrize("value", ['"1"', "true", "null", "[1]", '{"v":1}', "9007199254740993"])
def test_selected_value_must_be_representable_numeric_gauge(value: str) -> None:
    source = (
        '{"$metadata":{"topic":"motion","timestamp":1},"$data":{"speed":' + value + "}}"
    ).encode()
    with pytest.raises(HarnessInputError):
        read(source)


@pytest.mark.parametrize(
    "source",
    [
        b'{"$metadata":[],"$data":{"speed":1}}',
        b'{"$metadata":{"topic":1,"timestamp":1},"$data":{"speed":1}}',
        b'{"$metadata":{"topic":"","timestamp":1},"$data":{"speed":1}}',
        b'{"$metadata":{"topic":"motion","timestamp":1,"event":1},"$data":{"speed":1}}',
        b'{"$metadata":{"topic":"motion","timestamp":1,"clock":"simulation"},"$data":{"speed":1}}',
        b'{"$metadata":{"topic":"motion","timestamp":1},"$data":[]}',
        b'{"$metadata":{"topic":"motion","timestamp":1},"$data":{"other":1}}',
        b'{"$metadata":{"topic":"motion","timestamp":1},"$data":{"speed":1},"extra":0}',
    ],
)
def test_malformed_metadata_envelope_or_selected_field_is_refused(source: bytes) -> None:
    with pytest.raises(HarnessInputError):
        read(source)


def test_selected_missing_timestamp_is_refused_but_unselected_opaque_event_is_allowed() -> None:
    selected = b'{"$metadata":{"topic":"motion"},"$data":{"speed":1}}'
    with pytest.raises(HarnessInputError, match="integer Unix-ns"):
        read(selected)
    opaque = b'{"$metadata":{"topic":"note","event":true},"$data":{"text":"retained separately"}}'
    assert read(opaque) == ()
    assert opaque.endswith(b'"retained separately"}}')


@pytest.mark.parametrize("basis", ["simulation_ns", "unix_ms", "", None, True])
def test_ambiguous_or_wrong_clock_basis_is_refused(basis: Any) -> None:
    with pytest.raises(HarnessInputError, match="explicitly unix_ns"):
        read_emissions(b"", bindings=BINDINGS, timestamp_basis=basis)


@pytest.mark.parametrize("name,unit", [("", "m/s"), ("speed", ""), ("speed", True)])
def test_name_and_unit_are_explicit_nonempty_strings(name: Any, unit: Any) -> None:
    with pytest.raises(HarnessInputError):
        MetricBinding(name, unit)


def test_total_payload_limit_is_enforced_before_interpretation() -> None:
    from robotics_runtime_contracts.serialization import MAX_DOCUMENT_BYTES

    with pytest.raises(HarnessInputError, match="byte limit"):
        read(b" " * (MAX_DOCUMENT_BYTES + 1))


def test_existing_node_limit_bounds_lines_bindings_and_result_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from robotics_acceptance_harness import signalflag_emissions

    monkeypatch.setattr(signalflag_emissions, "MAX_DOCUMENT_NODES", 3)
    with pytest.raises(HarnessInputError, match="lines"):
        read(b"\n" * 4)
    with pytest.raises(HarnessInputError, match="bindings"):
        read_emissions(
            b"",
            bindings={("motion", str(i)): MetricBinding(str(i), "1") for i in range(4)},
            timestamp_basis="unix_ns",
        )
    line = b'{"$metadata":{"topic":"motion","timestamp":1},"$data":{"speed":1,"distance":2}}\n'
    with pytest.raises(HarnessInputError, match="samples"):
        read_emissions(
            line * 2,
            bindings={
                ("motion", "speed"): MetricBinding("speed", "m/s"),
                ("motion", "distance"): MetricBinding("distance", "m"),
            },
            timestamp_basis="unix_ns",
        )


@pytest.mark.parametrize("value", [2**53, 2**100])
def test_representable_large_integer_is_not_rejected_by_blanket_threshold(value: int) -> None:
    source = (
        '{"$metadata":{"topic":"motion","timestamp":0},"$data":{"speed":' + str(value) + "}}"
    ).encode()
    sample = read(source)[0]
    assert sample.value == value
    assert sample.observed_at_ns == 0


def test_pinned_actual_emitter_fixture_supports_native_gauge_assertions() -> None:
    path = Path(__file__).parent / "fixtures/signalflag/emissions-sdk-1.8.0.jsonl"
    source = path.read_bytes()
    digest = "b3d92727949e534172f45a0a79abb654952bf35a93c0c046017d3275043b7ee4"
    assert sha256(source).hexdigest() == digest
    samples = read(source)
    assert [sample.value for sample in samples] == [1, 2, 3, 4]
    assert [sample.observed_at_ns for sample in samples] == [
        1_791_000_000_000_000_000 + i for i in range(4)
    ]
    assert samples[-1].attributes["signalflag.event"] is True
    assert all(sample.attributes["signalflag.source_sha256"] == digest for sample in samples)
    assert all(not ({"run.id", "domain.id"} & sample.attributes.keys()) for sample in samples)
    assertion = {
        "assertion_id": "bounded-speed",
        "metric_name": "org.example.speed",
        "unit": "m/s",
        "aggregation": "max",
        "operator": "lte",
        "threshold": 4,
        "window_sec": 1,
    }
    assert evaluate_metric_assertions((assertion,), samples)[0].status == "passed"
    assert (
        evaluate_metric_assertions(({**assertion, "unit": "km/h"},), samples)[0].status == "error"
    )
    assert path.read_bytes() == source


@pytest.mark.parametrize("line_ending", [b"\r\n", b"\n", b""])
def test_jsonl_lf_crlf_and_final_record_without_lf_keep_original_byte_identity(
    line_ending: bytes,
) -> None:
    path = Path(__file__).parent / "fixtures/signalflag/emissions-sdk-1.8.0.jsonl"
    original = path.read_bytes()
    lines = original.rstrip(b"\n").split(b"\n")
    source = (line_ending if line_ending else b"\n").join(lines) + line_ending
    samples = read(source)
    assert [sample.value for sample in samples] == [1, 2, 3, 4]
    assert all(
        sample.attributes["signalflag.source_sha256"] == sha256(source).hexdigest()
        for sample in samples
    )
    assert path.read_bytes() == original


@pytest.mark.parametrize("separator", [b"\r", b"\v", b"\f", b"\n\n"])
def test_bare_non_lf_separators_and_blank_records_are_not_jsonl(separator: bytes) -> None:
    path = Path(__file__).parent / "fixtures/signalflag/emissions-sdk-1.8.0.jsonl"
    original = path.read_bytes()
    first = original.split(b"\n", 1)[0]
    with pytest.raises(ContractError):
        read(first + separator + first)
    assert path.read_bytes() == original


def test_line_count_is_bounded_before_interpreting_many_empty_records() -> None:
    from robotics_runtime_contracts.serialization import MAX_DOCUMENT_NODES

    with pytest.raises(HarnessInputError, match="lines"):
        read(b"\n" * (MAX_DOCUMENT_NODES + 1))
