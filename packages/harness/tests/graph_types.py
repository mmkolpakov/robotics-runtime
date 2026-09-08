"""Mutable scenario graph shapes shared by unit and live ROS fixtures."""

from typing import NotRequired, TypedDict


class ExpectedTopic(TypedDict):
    name: str
    type: str
    min_publishers: int
    min_subscribers: int
    first_message_timeout_sec: float
    qos_profile: NotRequired[str]


class ExpectedEndpoint(TypedDict):
    name: str
    type: str
    server_required: bool


class ExpectedLifecycleNode(TypedDict):
    name: str
    required_state: str
    timeout_sec: float
    stable_for_sec: float


class ExpectedGraph(TypedDict):
    topics: list[ExpectedTopic]
    services: list[ExpectedEndpoint]
    actions: list[ExpectedEndpoint]
    lifecycle_nodes: list[ExpectedLifecycleNode]
