"""JSON shapes produced and inspected by the live test helpers (no ROS imports)."""

from typing import NotRequired, Required, TypedDict


class MetricGolden(TypedDict):
    name: str
    unit: str
    value: float
    resource_attributes: dict[str, str]


class QualificationGolden(TypedDict):
    interval_ns: int
    histogram_count: int
    message_age_ms: float
    delivery_latency_ms: float
    explicit_bounds_ms: list[float]
    counters: dict[str, int]


class StringValue(TypedDict):
    stringValue: str


class Attribute(TypedDict):
    key: str
    value: StringValue


class DataPoint(TypedDict, total=False):
    timeUnixNano: Required[str]
    startTimeUnixNano: str
    attributes: list[Attribute]
    asDouble: float
    asInt: str
    count: str
    sum: float
    min: float
    max: float
    explicitBounds: list[float]
    bucketCounts: list[str]


class Instrument(TypedDict):
    dataPoints: list[DataPoint]
    aggregationTemporality: NotRequired[int]
    isMonotonic: NotRequired[bool]


class Metric(TypedDict):
    name: str
    unit: str
    gauge: NotRequired[Instrument]
    histogram: NotRequired[Instrument]
    sum: NotRequired[Instrument]


class Resource(TypedDict):
    attributes: list[Attribute]


class ScopeMetrics(TypedDict):
    scope: dict[str, str]
    metrics: list[Metric]


class ResourceMetrics(TypedDict):
    resource: Resource
    scopeMetrics: list[ScopeMetrics]


class MetricsPayload(TypedDict):
    resourceMetrics: list[ResourceMetrics]


class AssertionResult(TypedDict):
    assertion_id: str
    status: str
    observed_value: float | int | str | bool | None


class TimeAuthorityResult(TypedDict):
    evidence_sha256: str
    within_policy: bool
    sample_count: int


class ObservedTopic(TypedDict):
    name: str
    publishers: int
    subscribers: int


class ObservedEndpoint(TypedDict):
    name: str
    server_nodes: int


class ObservedGraph(TypedDict):
    topics: list[ObservedTopic]
    services: list[ObservedEndpoint]
    actions: list[ObservedEndpoint]


class LifecycleState(TypedDict):
    state: str


class ClockObservation(TypedDict):
    monotonic: bool


class LiveResult(TypedDict):
    """The subset read after the CLI result has passed contract validation."""

    status: str
    evaluation_mode: str
    unevaluated: list[str]
    assertion_results: list[AssertionResult]
    time_authority_observation: TimeAuthorityResult
    observed_ros_graph: ObservedGraph
    lifecycle_states: list[LifecycleState]
    clock_observation: ClockObservation
    shutdown: dict[str, bool]
