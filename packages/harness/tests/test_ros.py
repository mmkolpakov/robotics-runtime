from __future__ import annotations

from collections.abc import Callable
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import robotics_acceptance_harness.ros as ros_module
from robotics_acceptance_harness.readiness import evaluate_graph
from robotics_acceptance_harness.ros import RosGraphObserver, RosObserverError
from tests.graph_types import ExpectedGraph


class FakeContext:
    def __init__(self, *, initialized: bool = False) -> None:
        self.initialized = initialized
        self.closed = False
        self.shutdown_calls = 0

    def ok(self) -> bool:
        return self.initialized and not self.closed

    def try_shutdown(self) -> None:
        self.shutdown_calls += 1
        self.closed = True


class FakeFuture:
    def done(self) -> bool:
        return True

    def result(self) -> object:
        return SimpleNamespace(current_state=SimpleNamespace(label="active"))


class FakeClient:
    def service_is_ready(self) -> bool:
        return True

    def call_async(self, _request: object) -> FakeFuture:
        return FakeFuture()


class FakeNode:
    def __init__(self) -> None:
        self.callbacks: dict[str, Callable[[object], None]] = {}
        self.subscription_qos: dict[str, object] = {}
        self.destroyed = False
        self.executor_started = Event()
        self.executor_stopped = Event()
        self.shutdown_results: list[bool] = []

    def create_subscription(
        self,
        _message_type: object,
        topic: str,
        callback: Callable[[object], None],
        qos: object,
    ) -> object:
        self.callbacks[topic] = callback
        self.subscription_qos[topic] = qos
        return object()

    def create_client(self, _service_type: object, _name: str) -> FakeClient:
        return FakeClient()

    def get_topic_names_and_types(self) -> list[tuple[str, list[str]]]:
        return [
            ("/camera/image", ["sensor_msgs/msg/Image"]),
            ("/clock", ["rosgraph_msgs/msg/Clock"]),
        ]

    def count_subscribers(self, name: str) -> int:
        return 2 if name == "/camera/image" else 1

    def count_publishers(self, _name: str) -> int:
        return 1

    def get_publishers_info_by_topic(self, _name: str) -> list[object]:
        return [SimpleNamespace(qos_profile="sensor-data")]

    def get_service_names_and_types(self) -> list[tuple[str, list[str]]]:
        return [("/camera/get_parameters", ["rcl_interfaces/srv/GetParameters"])]

    def get_name(self) -> str:
        return "robotics_acceptance_observer"

    def get_namespace(self) -> str:
        return "/"

    def get_node_names_and_namespaces(self) -> list[tuple[str, str]]:
        return [("camera", "/"), ("robotics_acceptance_observer", "/")]

    def get_client_names_and_types_by_node(
        self,
        node_name: str,
        _node_namespace: str,
    ) -> list[tuple[str, list[str]]]:
        if node_name == "robotics_acceptance_observer":
            return [("/camera/get_state", ["lifecycle_msgs/srv/GetState"])]
        return [("/camera/get_parameters", ["rcl_interfaces/srv/GetParameters"])]

    def get_service_names_and_types_by_node(
        self,
        _node_name: str,
        _node_namespace: str,
    ) -> list[tuple[str, list[str]]]:
        return [
            ("/camera/get_parameters", ["rcl_interfaces/srv/GetParameters"]),
            ("/arm", ["example_interfaces/srv/Trigger"]),
        ]

    def destroy_node(self) -> None:
        self.destroyed = True


class FakeExecutor:
    def __init__(self, *, context: FakeContext) -> None:
        self.context = context
        self.node: FakeNode | None = None

    def add_node(self, node: FakeNode) -> None:
        self.node = node

    def spin(self) -> None:
        assert self.node is not None
        for topic, callback in self.node.callbacks.items():
            message = (
                SimpleNamespace(clock=SimpleNamespace(sec=1, nanosec=2))
                if topic == "/clock"
                else object()
            )
            callback(message)
        self.node.executor_started.set()
        self.node.executor_stopped.wait()

    def shutdown(self, timeout_sec: float) -> bool:
        assert timeout_sec == 5.0
        if self.node is None:
            return True
        result = self.node.shutdown_results.pop(0) if self.node.shutdown_results else True
        if not result:
            return False
        self.node.executor_stopped.set()
        return True

    def remove_node(self, node: FakeNode) -> None:
        assert node is self.node


class GetState:
    class Request:
        pass


def expected_graph() -> ExpectedGraph:
    return {
        "topics": [
            {
                "name": "/camera/image",
                "type": "sensor_msgs/msg/Image",
                "min_publishers": 1,
                "min_subscribers": 1,
                "first_message_timeout_sec": 2,
                "qos_profile": "sensor_data",
            }
        ],
        "services": [
            {
                "name": "/camera/get_parameters",
                "type": "rcl_interfaces/srv/GetParameters",
                "server_required": True,
            }
        ],
        "actions": [
            {
                "name": "/takeoff",
                "type": "example_interfaces/action/Fibonacci",
                "server_required": True,
            }
        ],
        "lifecycle_nodes": [
            {
                "name": "/camera",
                "required_state": "active",
                "timeout_sec": 2,
                "stable_for_sec": 0,
            }
        ],
    }


def fake_modules(node: FakeNode) -> dict[str, object]:
    return {
        "rclpy": SimpleNamespace(
            init=lambda **_kwargs: None,
            create_node=lambda *_args, **_kwargs: node,
        ),
        "rclpy.action": SimpleNamespace(
            get_action_server_names_and_types_by_node=lambda observed_node, *_args: (
                [("/takeoff", ["example_interfaces/action/Fibonacci"])]
                if observed_node is node
                else []
            ),
            get_action_client_names_and_types_by_node=lambda observed_node, *_args: (
                [("/land", ["example_interfaces/action/Fibonacci"])]
                if observed_node is node
                else []
            ),
        ),
        "rclpy.context": SimpleNamespace(Context=FakeContext),
        "rclpy.executors": SimpleNamespace(SingleThreadedExecutor=FakeExecutor),
        "rclpy.qos": SimpleNamespace(
            qos_profile_system_default="system-default",
            qos_profile_sensor_data="sensor-data",
            qos_profile_services_default="services-default",
            qos_profile_parameters="parameters",
            QoSProfile=SimpleNamespace,
            ReliabilityPolicy=SimpleNamespace(BEST_EFFORT="best-effort", RELIABLE="reliable"),
            DurabilityPolicy=SimpleNamespace(
                VOLATILE="volatile", TRANSIENT_LOCAL="transient-local"
            ),
            HistoryPolicy=SimpleNamespace(KEEP_LAST="keep-last"),
            QoSCompatibility=SimpleNamespace(ERROR="error"),
            qos_check_compatible=lambda *_args: ("ok", ""),
        ),
        "rosidl_runtime_py.utilities": SimpleNamespace(get_message=lambda name: name),
        "lifecycle_msgs.srv": SimpleNamespace(GetState=GetState),
        "rosgraph_msgs.msg": SimpleNamespace(Clock=object),
    }


def test_ros_observer_fails_clearly_outside_ros_runtime() -> None:
    def missing_module(name: str) -> object:
        raise ModuleNotFoundError(name)

    with pytest.raises(RosObserverError, match="must be available"):
        RosGraphObserver(
            {"topics": [], "services": [], "actions": [], "lifecycle_nodes": []},
            observe_clock=True,
            module_loader=missing_module,
        )


def test_ros_observer_reports_graph_clock_and_lifecycle_without_writing() -> None:
    node = FakeNode()
    modules = fake_modules(node)
    observer = RosGraphObserver(
        expected_graph(),
        observe_clock=True,
        module_loader=modules.__getitem__,
    )

    assert node.executor_started.wait(timeout=1.0)
    assert node.subscription_qos["/clock"] == SimpleNamespace(
        depth=1, reliability="best-effort", durability="volatile"
    )
    initial_samples = observer.clock_samples
    assert initial_samples == ()
    observer.start_clock_observation()
    node.callbacks["/clock"](SimpleNamespace(clock=SimpleNamespace(sec=1, nanosec=2)))
    samples = observer.stop_clock_observation()
    assert samples[-1].source_time_ns == 1_000_000_002
    node.callbacks["/clock"](SimpleNamespace(clock=SimpleNamespace(sec=2, nanosec=0)))
    assert len(observer.clock_samples) == 1
    observer.snapshot()
    snapshot = observer.snapshot()

    assert evaluate_graph(expected_graph(), snapshot) == ()
    assert snapshot.topics["/camera/image"].subscribers == 1
    assert snapshot.lifecycle_nodes["/camera"].state == "active"
    observer.close()
    observer.close()
    assert node.executor_stopped.is_set()
    assert node.destroyed
    with pytest.raises(RosObserverError, match="closed"):
        observer.snapshot()


@pytest.mark.parametrize("source_seconds", [(1, 1, 1, 1), (1, 2, 3, 4)])
def test_ros_observer_bounds_all_clock_samples(source_seconds: tuple[int, ...]) -> None:
    node = FakeNode()
    observer = RosGraphObserver(
        expected_graph(),
        observe_clock=True,
        module_loader=fake_modules(node).__getitem__,
        max_clock_samples=2,
    )

    assert node.executor_started.wait(timeout=1.0)
    observer.start_clock_observation()
    for source in source_seconds:
        node.callbacks["/clock"](SimpleNamespace(clock=SimpleNamespace(sec=source, nanosec=0)))
    assert len(observer.clock_samples) == 2
    with pytest.raises(RosObserverError, match="exceeded the configured limit"):
        observer.stop_clock_observation()
    observer.start_clock_observation()
    for _ in range(2):
        node.callbacks["/clock"](SimpleNamespace(clock=SimpleNamespace(sec=5, nanosec=0)))
    assert [sample.source_time_ns for sample in observer.stop_clock_observation()] == [
        5_000_000_000,
        5_000_000_000,
    ]
    assert RosGraphObserver.DEFAULT_MAX_CLOCK_SAMPLES == 1_000_000
    observer.close()


@pytest.mark.parametrize("node_present, status", [(False, "failed"), (True, "error")])
def test_lifecycle_cache_cannot_hide_disappearance_or_unavailable_service(
    monkeypatch: pytest.MonkeyPatch,
    node_present: bool,
    status: str,
) -> None:
    node = FakeNode()
    with RosGraphObserver(
        expected_graph(),
        observe_clock=False,
        module_loader=fake_modules(node).__getitem__,
    ) as observer:
        assert node.executor_started.wait(timeout=1.0)
        observer.snapshot()
        assert observer.snapshot().lifecycle_nodes["/camera"].state == "active"

        # Node and service discovery may disagree while DDS propagates disappearance.
        monkeypatch.setattr(FakeClient, "service_is_ready", lambda _self: not node_present)
        nodes = [("camera", "/")] if node_present else []
        monkeypatch.setattr(node, "get_node_names_and_namespaces", lambda: nodes)
        snapshot = observer.snapshot()

        assert snapshot.node_names == (frozenset({"/camera"}) if node_present else frozenset())
        assert "/camera" not in snapshot.lifecycle_nodes
        issues = [
            issue
            for issue in evaluate_graph(expected_graph(), snapshot)
            if "lifecycle_nodes" in issue.json_path
        ]
        (issue,) = issues
        assert issue.status == status
        assert ("unavailable" if node_present else "absent") in issue.message


def test_lifecycle_presence_uses_fully_qualified_names(monkeypatch: pytest.MonkeyPatch) -> None:
    node = FakeNode()
    graph = expected_graph()
    graph["lifecycle_nodes"][0]["name"] = "/robot/camera"
    monkeypatch.setattr(node, "get_node_names_and_namespaces", lambda: [("camera", "/robot")])
    with RosGraphObserver(
        graph,
        observe_clock=False,
        module_loader=fake_modules(node).__getitem__,
    ) as observer:
        assert node.executor_started.wait(timeout=1.0)
        observer.snapshot()
        snapshot = observer.snapshot()
        assert snapshot.node_names == frozenset({"/robot/camera"})
        assert snapshot.lifecycle_nodes["/robot/camera"].state == "active"
        assert evaluate_graph(graph, snapshot) == ()


def test_ros_observer_keeps_failed_shutdown_terminal_but_retryable() -> None:
    node = FakeNode()
    node.shutdown_results = [False, True]
    observer = RosGraphObserver(
        expected_graph(),
        observe_clock=True,
        module_loader=fake_modules(node).__getitem__,
    )

    assert node.executor_started.wait(timeout=1.0)
    with pytest.raises(RosObserverError, match="did not stop"):
        observer.close()
    with pytest.raises(RosObserverError, match="closing"):
        observer.snapshot()
    assert not node.destroyed
    observer.close()
    assert node.destroyed


def test_ros_observer_context_manager_detaches() -> None:
    node = FakeNode()
    modules = fake_modules(node)

    with RosGraphObserver(
        expected_graph(),
        observe_clock=False,
        module_loader=modules.__getitem__,
    ) as observer:
        observer.snapshot()

    assert node.destroyed


def test_ros_observer_skips_action_graph_outside_scenario_scope() -> None:
    def unexpected_query(*_args: object) -> None:
        pytest.fail("unexpected action graph query")

    node = FakeNode()
    modules = fake_modules(node)
    modules["rclpy.action"] = SimpleNamespace(
        get_action_server_names_and_types_by_node=unexpected_query,
        get_action_client_names_and_types_by_node=unexpected_query,
    )
    graph: ExpectedGraph = {"topics": [], "services": [], "actions": [], "lifecycle_nodes": []}

    with RosGraphObserver(
        graph,
        observe_clock=False,
        module_loader=modules.__getitem__,
    ) as observer:
        assert observer.snapshot().actions == {}


def test_ros_observer_queries_forbidden_names_without_subscribing() -> None:
    node = FakeNode()
    modules = fake_modules(node)
    observer = RosGraphObserver(
        expected_graph(),
        forbidden_graph={
            "topics": ["/cmd_vel"],
            "services": ["/arm", "/camera/get_state"],
            "actions": ["/land"],
        },
        observe_clock=False,
        module_loader=modules.__getitem__,
    )

    snapshot = observer.snapshot()

    assert snapshot.topics["/cmd_vel"].publishers == 1
    assert snapshot.services["/arm"].server_nodes == 1
    assert snapshot.services["/arm"].client_nodes == 0
    assert snapshot.services["/camera/get_state"].client_nodes == 0
    assert snapshot.actions["/land"].server_nodes == 0
    assert snapshot.actions["/land"].client_nodes == 1
    assert "/cmd_vel" not in node.callbacks
    observer.close()


def test_an_unanswered_lifecycle_request_expires_the_cached_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node = FakeNode()
    now_ns = [0]
    monkeypatch.setattr(ros_module, "monotonic_ns", lambda: now_ns[0])
    cancelled: list[bool] = []
    pending = SimpleNamespace(done=lambda: False, cancel=lambda: cancelled.append(True))
    with RosGraphObserver(
        expected_graph(),
        observe_clock=False,
        module_loader=fake_modules(node).__getitem__,
    ) as observer:
        assert node.executor_started.wait(timeout=1.0)
        observer.snapshot()
        monkeypatch.setattr(FakeClient, "call_async", lambda _self, _request: pending)
        assert observer.snapshot().lifecycle_nodes["/camera"].state == "active"

        now_ns[0] = RosGraphObserver.LIFECYCLE_RESPONSE_TIMEOUT_NS
        assert observer.snapshot().lifecycle_nodes["/camera"].state == "active"

        now_ns[0] += 1
        snapshot = observer.snapshot()

    assert "/camera" not in snapshot.lifecycle_nodes
    assert cancelled == [True]
    (issue,) = (
        issue
        for issue in evaluate_graph(expected_graph(), snapshot)
        if "lifecycle_nodes" in issue.json_path
    )
    assert issue.status == "error"


@pytest.mark.parametrize(
    "name, expected",
    [
        ("system_default", "system-default"),
        ("sensor_data", "sensor-data"),
        ("services_default", "services-default"),
        ("parameters", "parameters"),
        (
            "transient_local",
            SimpleNamespace(
                history="keep-last", depth=10, reliability="reliable", durability="transient-local"
            ),
        ),
    ],
)
def test_named_topic_qos_reaches_the_subscription_unchanged(name: str, expected: object) -> None:
    node = FakeNode()
    graph = expected_graph()
    graph["topics"][0]["qos_profile"] = name
    with RosGraphObserver(graph, observe_clock=False, module_loader=fake_modules(node).__getitem__):
        assert node.subscription_qos["/camera/image"] == expected


def test_default_context_is_initialized_and_closed_once() -> None:
    node = FakeNode()
    context = FakeContext()
    initialized: list[FakeContext] = []
    created: list[FakeContext] = []
    modules = fake_modules(node)

    def create_context() -> FakeContext:
        created.append(context)
        return context

    def initialize(*, args: object, context: FakeContext) -> None:
        assert args is None
        initialized.append(context)
        context.initialized = True

    modules["rclpy.context"] = SimpleNamespace(Context=create_context)
    modules["rclpy"] = SimpleNamespace(init=initialize, create_node=lambda *_args, **_kwargs: node)
    observer = RosGraphObserver(
        expected_graph(), observe_clock=False, module_loader=modules.__getitem__
    )
    assert node.executor_started.wait(timeout=1.0)
    assert created == initialized == [context]
    assert context.ok()
    observer.close()
    observer.close()
    assert node.destroyed
    assert node.executor_stopped.is_set()
    assert context.shutdown_calls == 1
    assert not context.ok()


def test_borrowed_context_survives_observer_close_and_caller_can_continue() -> None:
    context = FakeContext(initialized=True)
    caller_node = FakeNode()
    caller_executor = FakeExecutor(context=context)
    caller_executor.add_node(caller_node)
    observer_node = FakeNode()
    modules = fake_modules(observer_node)
    executors: list[FakeExecutor] = []

    def unexpected(*_args: object, **_kwargs: object) -> None:
        pytest.fail("borrowed context must not be created or initialized")

    def create_node(*_args: object, **kwargs: object) -> FakeNode:
        assert kwargs["context"] is context
        return observer_node

    def create_executor(*, context: FakeContext) -> FakeExecutor:
        executor = FakeExecutor(context=context)
        executors.append(executor)
        return executor

    modules["rclpy.context"] = SimpleNamespace(Context=unexpected)
    modules["rclpy"] = SimpleNamespace(init=unexpected, create_node=create_node)
    modules["rclpy.executors"] = SimpleNamespace(SingleThreadedExecutor=create_executor)
    with RosGraphObserver(
        expected_graph(),
        observe_clock=False,
        context=context,
        module_loader=modules.__getitem__,
    ) as observer:
        assert observer_node.executor_started.wait(timeout=1.0)
        assert observer.snapshot().topics["/camera/image"].publishers == 1
        assert len(executors) == 1
        assert executors[0].context is context
        assert executors[0].node is observer_node

    observer.close()
    assert observer_node.destroyed
    assert observer_node.executor_stopped.is_set()
    assert context.ok()
    assert context.shutdown_calls == 0
    assert not caller_node.destroyed
    assert caller_executor.node is caller_node
    assert not caller_node.executor_stopped.is_set()
    caller_node.create_subscription(object, "/still_running", lambda _message: None, object())
    assert "/still_running" in caller_node.callbacks


@pytest.mark.parametrize("initialized, closed", [(False, False), (True, True)])
def test_borrowed_context_must_already_be_running(initialized: bool, closed: bool) -> None:
    context = FakeContext(initialized=initialized)
    context.closed = closed
    modules = fake_modules(FakeNode())

    def unexpected(*_args: object, **_kwargs: object) -> None:
        pytest.fail("invalid borrowed context must not acquire ROS resources")

    modules["rclpy.context"] = SimpleNamespace(Context=unexpected)
    modules["rclpy"] = SimpleNamespace(init=unexpected, create_node=unexpected)
    modules["rclpy.executors"] = SimpleNamespace(SingleThreadedExecutor=unexpected)
    with pytest.raises(RosObserverError, match="must already be initialized and running"):
        RosGraphObserver(
            expected_graph(),
            observe_clock=False,
            context=context,
            module_loader=modules.__getitem__,
        )
    assert context.shutdown_calls == 0
    assert context.closed is closed


@pytest.mark.parametrize("borrowed", [False, True])
@pytest.mark.parametrize(
    "stage", ["create_node", "create_executor", "add_node", "subscription", "thread_start"]
)
def test_constructor_failure_releases_only_observer_resources(
    monkeypatch: pytest.MonkeyPatch, borrowed: bool, stage: str
) -> None:
    context = FakeContext(initialized=borrowed)
    node = FakeNode()
    executor = FakeExecutor(context=context)
    modules = fake_modules(node)
    failure = RuntimeError("injected " + stage + " failure")

    def initialize(*, args: object, context: FakeContext) -> None:
        assert not borrowed
        assert args is None
        context.initialized = True

    create_context = Mock(return_value=context)
    init = Mock(side_effect=initialize)
    create_node = Mock(return_value=node)
    create_executor = Mock(return_value=executor)
    add_node = Mock(wraps=executor.add_node)
    subscription = Mock(wraps=node.create_subscription)
    shutdown = Mock(wraps=executor.shutdown)
    modules["rclpy.context"] = SimpleNamespace(Context=create_context)
    modules["rclpy"] = SimpleNamespace(init=init, create_node=create_node)
    modules["rclpy.executors"] = SimpleNamespace(SingleThreadedExecutor=create_executor)
    monkeypatch.setattr(executor, "add_node", add_node)
    monkeypatch.setattr(executor, "shutdown", shutdown)
    monkeypatch.setattr(node, "create_subscription", subscription)
    failures = {
        "create_node": create_node,
        "create_executor": create_executor,
        "add_node": add_node,
        "subscription": subscription,
    }
    if stage in failures:
        failures[stage].side_effect = failure
    else:
        monkeypatch.setattr(Thread, "start", Mock(side_effect=failure))

    with pytest.raises(RuntimeError) as caught:
        RosGraphObserver(
            expected_graph(),
            observe_clock=True,
            context=context if borrowed else None,
            module_loader=modules.__getitem__,
        )

    assert caught.value is failure
    assert create_context.call_count == init.call_count == (0 if borrowed else 1)
    assert context.shutdown_calls == (0 if borrowed else 1)
    assert context.ok() is borrowed
    assert node.destroyed is (stage != "create_node")
    if stage in {"create_node", "create_executor"}:
        shutdown.assert_not_called()
    else:
        shutdown.assert_called_once_with(timeout_sec=5.0)
    assert not node.executor_started.is_set()


def test_owned_context_init_failure_closes_context_without_creating_node() -> None:
    context = FakeContext()
    modules = fake_modules(FakeNode())
    failure = RuntimeError("context initialization failed")

    def initialize(*, args: object, context: FakeContext) -> None:
        context.initialized = True
        raise failure

    def unexpected(*_args: object, **_kwargs: object) -> None:
        pytest.fail("node must not be created after init failure")

    modules["rclpy.context"] = SimpleNamespace(Context=lambda: context)
    modules["rclpy"] = SimpleNamespace(init=initialize, create_node=unexpected)
    with pytest.raises(RuntimeError) as caught:
        RosGraphObserver(expected_graph(), observe_clock=False, module_loader=modules.__getitem__)

    assert caught.value is failure
    assert context.shutdown_calls == 1
    assert not context.ok()


def test_borrowed_context_is_not_closed_when_executor_shutdown_must_be_retried() -> None:
    context = FakeContext(initialized=True)
    node = FakeNode()
    node.shutdown_results = [False, True]
    observer = RosGraphObserver(
        expected_graph(),
        observe_clock=False,
        context=context,
        module_loader=fake_modules(node).__getitem__,
    )
    assert node.executor_started.wait(timeout=1.0)
    with pytest.raises(RosObserverError, match="did not stop"):
        observer.close()
    assert not node.destroyed
    assert context.ok()
    assert context.shutdown_calls == 0
    with pytest.raises(RosObserverError, match="closing"):
        observer.snapshot()
    observer.close()
    observer.close()
    assert node.destroyed
    assert node.executor_stopped.is_set()
    assert context.ok()
    assert context.shutdown_calls == 0


@pytest.mark.parametrize("borrowed", [False, True])
@pytest.mark.parametrize("observe_clock", [False, True])
def test_process_ros_arguments_cannot_remap_subscriptions_or_enable_sim_time(
    borrowed: bool, observe_clock: bool
) -> None:
    class ArgumentNode(FakeNode):
        def __init__(self) -> None:
            super().__init__()
            self.use_sim_time = False
            self.remaps: dict[str, str] = {}
            self.subscription_names: list[str] = []

        def apply_global_arguments(self, use_global_arguments: bool) -> None:
            self.use_sim_time = use_global_arguments
            self.remaps = {"/odom": "/other"} if use_global_arguments else {}
            if self.use_sim_time:
                self.create_subscription(object, "/clock", lambda _message: None, object())

        def create_subscription(
            self,
            message_type: object,
            topic: str,
            callback: Callable[[object], None],
            qos: object,
        ) -> object:
            resolved = self.remaps.get(topic, topic)
            self.subscription_names.append(resolved)
            return super().create_subscription(message_type, resolved, callback, qos)

    caller_context = FakeContext(initialized=True)
    observer_context = caller_context if borrowed else FakeContext()
    caller = ArgumentNode()
    caller.apply_global_arguments(True)
    caller.create_subscription(object, "/odom", lambda _message: None, object())
    node = ArgumentNode()
    modules = fake_modules(node)

    def initialize(*, args: object, context: FakeContext) -> None:
        assert not borrowed
        context.initialized = True

    def create_node(
        _name: str, *, use_global_arguments: bool = True, **kwargs: object
    ) -> ArgumentNode:
        assert kwargs["context"] is observer_context
        node.apply_global_arguments(use_global_arguments)
        return node

    modules["rclpy.context"] = SimpleNamespace(Context=lambda: observer_context)
    modules["rclpy"] = SimpleNamespace(init=initialize, create_node=create_node)
    graph: ExpectedGraph = {
        "topics": [
            {
                "name": "/odom",
                "type": "std_msgs/msg/String",
                "min_publishers": 0,
                "min_subscribers": 0,
                "qos_profile": "system_default",
                "first_message_timeout_sec": 2.0,
            }
        ],
        "services": [],
        "actions": [],
        "lifecycle_nodes": [],
    }
    with RosGraphObserver(
        graph,
        observe_clock=observe_clock,
        context=observer_context if borrowed else None,
        module_loader=modules.__getitem__,
    ):
        assert node.executor_started.wait(timeout=1.0)
        assert not node.use_sim_time
        assert node.subscription_names == (["/odom", "/clock"] if observe_clock else ["/odom"])
        assert "/other" not in node.callbacks

    assert caller_context.ok()
    assert caller_context.shutdown_calls == 0
    assert caller.use_sim_time
    assert caller.subscription_names == ["/clock", "/other"]
    assert not caller.destroyed
