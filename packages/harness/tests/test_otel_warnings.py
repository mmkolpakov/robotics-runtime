from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import pytest
from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, ArrayValue, KeyValue, KeyValueList
from opentelemetry.proto.metrics.v1.metrics_pb2 import AggregationTemporality, DataPointFlags

from robotics_acceptance_harness.metrics import HistogramSample, MetricSample
from robotics_acceptance_harness.otel import (
    MetricInputError,
    load_otlp_json_metrics,
    otlp_attribute_value,
    otlp_attributes,
)
from robotics_acceptance_harness.traces import load_otlp_json_traces

_SECRET = "attribute-content-must-not-appear-in-logs"
_UNSUPPORTED_VALUES = ("array_value", "kvlist_value", "bytes_value", "unset")
_ABSENT = DataPointFlags.DATA_POINT_FLAGS_NO_RECORDED_VALUE_MASK


def _unsupported_value(kind: str) -> AnyValue:
    return {
        "array_value": AnyValue(array_value=ArrayValue(values=[AnyValue(string_value=_SECRET)])),
        "kvlist_value": AnyValue(
            kvlist_value=KeyValueList(
                values=[KeyValue(key="nested", value=AnyValue(string_value=_SECRET))]
            )
        ),
        "bytes_value": AnyValue(bytes_value=_SECRET.encode()),
        "unset": AnyValue(),
    }[kind]


def _metrics_request() -> ExportMetricsServiceRequest:
    request = ExportMetricsServiceRequest()
    resource = request.resource_metrics.add()
    resource.resource.attributes.add(key="resource", value=AnyValue(string_value="kept"))
    scope = resource.scope_metrics.add()
    scope.scope.attributes.add(key="scope", value=AnyValue(bool_value=False))
    gauge = scope.metrics.add(name="supported.gauge", unit="1")
    gauge.gauge.data_points.add(time_unix_nano=200, as_int=0)
    counter = scope.metrics.add(name="supported.sum", unit="1")
    counter.sum.aggregation_temporality = AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE
    counter.sum.is_monotonic = True
    counter.sum.data_points.add(start_time_unix_nano=100, time_unix_nano=200, as_double=2.5)
    histogram = scope.metrics.add(name="supported.histogram", unit="ms")
    histogram.histogram.aggregation_temporality = (
        AggregationTemporality.AGGREGATION_TEMPORALITY_DELTA
    )
    histogram.histogram.data_points.add(
        start_time_unix_nano=100,
        time_unix_nano=200,
        count=2,
        sum=3.0,
        explicit_bounds=[1.0],
        bucket_counts=[1, 1],
    )
    return request


def _write_json_lines(path: Path, payload: object) -> Path:
    path.write_text("{}\n\n" + json.dumps(payload) + "\n", encoding="utf-8")
    return path


def _warning(caplog: pytest.LogCaptureFixture, diagnostic_id: str) -> logging.LogRecord:
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.name == "robotics_acceptance_harness.otel"
    assert record.levelno == logging.WARNING
    assert record.__dict__["diagnostic_id"] == diagnostic_id
    assert _SECRET not in repr(record.__dict__)
    assert base64.b64encode(_SECRET.encode()).decode() not in repr(record.__dict__)
    assert _SECRET not in caplog.text
    return record


@pytest.mark.parametrize("kind", ("summary", "exponential_histogram"))
def test_unsupported_instrument_warns_and_preserves_supported_points(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    request = _metrics_request()
    path = tmp_path / "metrics.jsonl"
    expected = load_otlp_json_metrics(_write_json_lines(path, MessageToDict(request)))
    assert len(expected) == 3
    assert isinstance(expected[0], MetricSample) and expected[0].value == 0.0
    assert isinstance(expected[1], MetricSample) and expected[1].temporality == "cumulative"
    assert isinstance(expected[2], HistogramSample) and expected[2].count == 2
    metric = request.resource_metrics[0].scope_metrics[0].metrics.add(name="unsupported.metric")
    instrument = getattr(metric, kind)
    instrument.data_points.add(time_unix_nano=200, flags=_ABSENT)
    point = instrument.data_points.add(time_unix_nano=200, count=1, sum=0.0)
    if kind == "exponential_histogram":
        instrument.aggregation_temporality = AggregationTemporality.AGGREGATION_TEMPORALITY_DELTA
        point.zero_count = 1
    point.attributes.add(key="private", value=_unsupported_value("array_value"))

    observed = load_otlp_json_metrics(_write_json_lines(path, MessageToDict(request)))

    assert observed == expected
    record = _warning(caplog, "otlp.unsupported_instrument")
    assert record.__dict__["otlp_type"] == kind
    assert record.__dict__["metric_name"] == "unsupported.metric"
    assert record.__dict__["source_path"] == str(path.resolve())
    assert record.__dict__["line_number"] == 3
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", _UNSUPPORTED_VALUES)
@pytest.mark.parametrize("location", ("resource", "scope", "point"))
def test_unsupported_metric_attribute_warns_with_context_and_keeps_points(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    location: str,
) -> None:
    request = _metrics_request()
    path = tmp_path / "attributes.jsonl"
    expected = load_otlp_json_metrics(_write_json_lines(path, MessageToDict(request)))
    resource = request.resource_metrics[0]
    scope = resource.scope_metrics[0]
    items = {
        "resource": resource.resource.attributes,
        "scope": scope.scope.attributes,
        "point": scope.metrics[0].gauge.data_points[0].attributes,
    }[location]
    items.add(key="discarded.attribute", value=_unsupported_value(kind))

    observed = load_otlp_json_metrics(_write_json_lines(path, MessageToDict(request)))

    assert observed == expected
    record = _warning(caplog, "otlp.unsupported_attribute")
    assert record.__dict__["otlp_type"] == kind
    assert record.__dict__["attribute_key"] == "discarded.attribute"
    assert record.__dict__["source_path"] == str(path.resolve())
    assert record.__dict__["line_number"] == 3
    assert record.__dict__["metric_name"] == ("supported.gauge" if location == "point" else None)
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", ("gauge", "sum", "histogram", "summary", "exponential_histogram"))
def test_no_recorded_value_is_absent_without_warnings(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, kind: str
) -> None:
    request = ExportMetricsServiceRequest()
    metric = request.resource_metrics.add().scope_metrics.add().metrics.add(name="absent")
    point = getattr(metric, kind).data_points.add(time_unix_nano=200, flags=_ABSENT | 4)
    point.attributes.add(key="not-inspected", value=_unsupported_value("array_value"))
    path = _write_json_lines(tmp_path / "absent.jsonl", MessageToDict(request))

    assert load_otlp_json_metrics(path) == ()
    assert caplog.records == []


@pytest.mark.parametrize("kind", ("summary", "exponential_histogram"))
def test_empty_unsupported_instrument_does_not_warn_about_discarded_points(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, kind: str
) -> None:
    request = ExportMetricsServiceRequest()
    metric = request.resource_metrics.add().scope_metrics.add().metrics.add(name="empty")
    getattr(metric, kind).SetInParent()

    path = _write_json_lines(tmp_path / "empty.jsonl", MessageToDict(request))

    assert load_otlp_json_metrics(path) == ()
    assert caplog.records == []


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (AnyValue(string_value=""), ""),
        (AnyValue(bool_value=False), False),
        (AnyValue(int_value=0), 0),
        (AnyValue(double_value=0.0), 0.0),
    ],
)
def test_scalar_attribute_helpers_keep_legacy_calls_and_types_without_warnings(
    caplog: pytest.LogCaptureFixture, value: AnyValue, expected: object
) -> None:
    observed = otlp_attribute_value(value)
    assert observed == expected
    assert type(observed) is type(expected)
    assert otlp_attributes([KeyValue(key="scalar", value=value)]) == {"scalar": expected}
    assert caplog.records == []


@pytest.mark.parametrize("kind", _UNSUPPORTED_VALUES)
def test_attribute_value_helper_warns_without_requiring_new_context_arguments(
    caplog: pytest.LogCaptureFixture, kind: str
) -> None:
    assert otlp_attribute_value(_unsupported_value(kind)) is None

    record = _warning(caplog, "otlp.unsupported_attribute")
    assert record.__dict__["otlp_type"] == kind
    assert record.__dict__["source_path"] is None
    assert record.__dict__["line_number"] is None
    assert record.__dict__["attribute_key"] is None


def _traces_request() -> ExportTraceServiceRequest:
    request = ExportTraceServiceRequest()
    resource = request.resource_spans.add()
    resource.resource.attributes.add(key="run.id", value=AnyValue(string_value="run"))
    scope = resource.scope_spans.add()
    scope.scope.attributes.add(key="domain.id", value=AnyValue(string_value="domain"))
    span = scope.spans.add(
        name="supported.span",
        trace_id=bytes.fromhex("1" * 32),
        span_id=bytes.fromhex("2" * 16),
        start_time_unix_nano=100,
        end_time_unix_nano=200,
    )
    span.attributes.add(key="messaging.message.id", value=AnyValue(string_value="message"))
    link = span.links.add(trace_id=bytes.fromhex("3" * 32), span_id=bytes.fromhex("4" * 16))
    link.attributes.add(key="messaging.message.id", value=AnyValue(string_value="linked-message"))
    return request


def _write_traces(path: Path, request: ExportTraceServiceRequest) -> Path:
    payload = MessageToDict(request)
    span = request.resource_spans[0].scope_spans[0].spans[0]
    document = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    document["traceId"] = span.trace_id.hex()
    document["spanId"] = span.span_id.hex()
    document["links"][0]["traceId"] = span.links[0].trace_id.hex()
    document["links"][0]["spanId"] = span.links[0].span_id.hex()
    return _write_json_lines(path, payload)


@pytest.mark.parametrize("kind", _UNSUPPORTED_VALUES)
@pytest.mark.parametrize("location", ("resource", "scope", "span", "link"))
def test_trace_attribute_warnings_keep_spans_and_links(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    location: str,
) -> None:
    request = _traces_request()
    path = tmp_path / "traces.jsonl"
    expected = load_otlp_json_traces(
        _write_traces(path, request), expected_run_id="run", expected_domain_id="domain"
    )
    resource = request.resource_spans[0]
    scope = resource.scope_spans[0]
    span = scope.spans[0]
    items = {
        "resource": resource.resource.attributes,
        "scope": scope.scope.attributes,
        "span": span.attributes,
        "link": span.links[0].attributes,
    }[location]
    items.add(key="discarded.attribute", value=_unsupported_value(kind))

    observed = load_otlp_json_traces(
        _write_traces(path, request), expected_run_id="run", expected_domain_id="domain"
    )

    assert observed == expected
    assert observed[0].message_id == "message"
    assert observed[0].links[0].message_id == "linked-message"
    record = _warning(caplog, "otlp.unsupported_attribute")
    assert record.__dict__["otlp_type"] == kind
    assert record.__dict__["attribute_key"] == "discarded.attribute"
    assert record.__dict__["source_path"] == str(path.resolve())
    assert record.__dict__["line_number"] == 3
    assert record.__dict__["metric_name"] is None
    assert capsys.readouterr().out == ""


def test_malformed_protobuf_is_still_an_error_not_a_discard_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    payload = MessageToDict(_metrics_request())
    payload["resourceMetrics"][0]["resource"]["attributes"][0]["value"] = {"arrayValue": 42}
    path = _write_json_lines(tmp_path / "invalid.jsonl", payload)

    with pytest.raises(MetricInputError, match=r"invalid\.jsonl:3:"):
        load_otlp_json_metrics(path)

    assert caplog.records == []
