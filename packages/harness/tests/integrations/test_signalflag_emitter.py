from __future__ import annotations

import json
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

import pytest

from robotics_acceptance_harness.errors import HarnessInputError
from robotics_acceptance_harness.metrics import evaluate_metric_assertions
from robotics_acceptance_harness.signalflag_emissions import MetricBinding, read_emissions

metrics = pytest.importorskip("signalflag.sdk.metrics", reason="optional pinned SDK producer")
if version("signalflag") != "1.8.0":
    pytest.skip("producer qualification requires pinned SignalFlag 1.8.0", allow_module_level=True)


def test_actual_installed_emitter_scalar_series_event_and_opaque_records(tmp_path: Path) -> None:
    path = tmp_path / "emissions.jsonl"
    epoch = 1_791_000_000_000_000_000
    with metrics.Emitter(config_path=None, output_path=path) as emitter:
        emitter.emit("motion", {"speed": 1}, timestamp=epoch)
        emitter.emit_series("motion", {"speed": [2, 3]}, timestamps=[epoch + 1, epoch + 2])
        emitter.emit_event("motion", {"speed": 4}, timestamp=epoch + 3)
        emitter.emit_event("note", {"text": "opaque"}, timestamp=epoch + 4)
        emitter.emit("untimed", {"value": 7})
    source = path.read_bytes()
    fixture = Path(__file__).parents[1] / "fixtures/signalflag/emissions-sdk-1.8.0.jsonl"
    assert source == fixture.read_bytes()
    rows = [json.loads(line) for line in source.splitlines()]
    assert len(rows) == 6
    assert all(set(row) == {"$metadata", "$data"} for row in rows)
    assert [row["$data"]["speed"] for row in rows[:4]] == [1, 2, 3, 4]
    assert rows[3]["$metadata"]["event"] is True
    assert "timestamp" not in rows[-1]["$metadata"]
    samples = read_emissions(
        source,
        bindings={("motion", "speed"): MetricBinding("org.example.speed", "m/s")},
        timestamp_basis="unix_ns",
    )
    assert [sample.value for sample in samples] == [1, 2, 3, 4]
    assert [sample.observed_at_ns for sample in samples] == [epoch + i for i in range(4)]
    assert all(
        sample.attributes["signalflag.source_sha256"] == sha256(source).hexdigest()
        for sample in samples
    )
    assert samples[-1].attributes["signalflag.event"] is True
    assert all(not ({"run.id", "domain.id"} & sample.attributes.keys()) for sample in samples)
    assert all(sample.instrument_kind == "gauge" for sample in samples)
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
    with pytest.raises(HarnessInputError, match="integer Unix-ns"):
        read_emissions(
            source,
            bindings={("untimed", "value"): MetricBinding("untimed", "1")},
            timestamp_basis="unix_ns",
        )
    assert path.read_bytes() == source


def test_actual_installed_emitter_nonfinite_output_remains_opaque_on_refusal(
    tmp_path: Path,
) -> None:
    from robotics_runtime_contracts.errors import ContractError

    path = tmp_path / "nonfinite.jsonl"
    with metrics.Emitter(config_path=None, output_path=path) as emitter:
        emitter.emit("motion", {"speed": float("nan")}, timestamp=1)
    source = path.read_bytes()
    assert b"NaN" in source
    with pytest.raises(ContractError):
        read_emissions(
            source,
            bindings={("motion", "speed"): MetricBinding("speed", "m/s")},
            timestamp_basis="unix_ns",
        )
    assert path.read_bytes() == source
