# Live ROS 2 Jazzy integration tests

The `live-ros` CI job exercises `RosGraphObserver` against real `rclpy` nodes and
Fast DDS. The tests cover the implicit `/clock` subscription when the expected
graph omits `/clock`, topic types and endpoint counts, service and action servers
and clients, and an active lifecycle node queried through its real `GetState`
service. The observer's own topic subscription is excluded from the count.

The positive and negative CLI tests invoke `create-run` and `verify` in separate processes with
the installed workspace harness. It uses the current package simulation
fixtures, changes their expected graph and observation window, and observes a
real stepped clock. No observer factory, ROS module, executor, or clock is mocked.

Both tests send controlled gauge data through an actual OpenTelemetry Collector
0.148.0 HTTP receiver and JSON file exporter. The checked-in
`tests/live/fixtures/metric-golden.json` describes the expected normalized value
and resource attributes; it is test input, not a claimed collector capture.
The job produces `metrics.collector.otlp.jsonl` with current timestamps and run
attributes. The test checks the exported points against the golden expectation,
then checks that the CLI's metric assertion passes with the same value.
The exporter is stopped and flushed before its bytes are hashed and the finalized
evidence index is published after the CLI's measurement-complete marker.

The positive test requires exit 0, `evaluation_mode: live`, `status: passed`, no
unevaluated checks, all assertions passed, and JUnit without errors, failures, or
skips. In addition to the gauge, it declares and exports these qualification inputs:

- `robotics.message.age`: delta histogram, three synthetic observations per interval.
- `robotics.message.received`, `robotics.message.lost`, and
  `robotics.message.sequence_error`: monotonic delta sums over identical intervals,
  with the required channel and sequence-method attributes. Loss and sequence
  errors are zero in this fixture.
- `robotics.time_authority.delivery_latency`: delta histogram, at least 30 samples
  in the measurement window, with the declared run, domain, source, and method attributes.

These qualification values are **synthetic harness integration fixtures**, including
the method labels; they are not measurements of DDS latency or loss. After the
measurement marker, the fixture builds contiguous 10 ms intervals spanning process
startup through completion and sends them through the real Collector. The harness
selects the intervals inside its own live observation window. No wall clock or
observer is injected, and no timestamps are rewritten in the Collector output.
The additional values are pinned in `tests/live/fixtures/qualification-golden.json`.

The positive case also writes the last 100 CDR `/clock` messages received by the test node
to a valid ROS 2 MCAP with zstd compression using the test-only `mcap==1.3.0`
dependency. It verifies the message count and CRCs, derives `recording-summary.v1`
from the MCAP reader, and indexes both files by their actual hashes. The required
recording topic remains `/clock`; no recording requirement is bypassed.

The negative case omits the qualification metrics and recording. It requires exit
1, a non-passing live result, the passing golden gauge assertion, missing-evidence
outcomes, and JUnit failures or errors. It does not fix the current precedence of
`error` versus `failed` in status aggregation. A negative case cannot make this job
green unless the separate positive case also passes.

This gate checks real ROS observation, Collector export, and CLI orchestration.
The runtime manifest retains fixture provenance. Physical qualification and real
exporter performance measurement are later E2E work.

## Read-only graph API

The following submodule interfaces support observation of an already running
ROS domain. They do not start workloads, issue commands or establish native
postconditions.

```python
from robotics_acceptance_harness.readiness import wait_for_readiness
from robotics_acceptance_harness.ros import RosGraphObserver

with RosGraphObserver(expected_graph, observe_clock=True) as observer:
    readiness = wait_for_readiness(expected_graph, observer, timeout_sec=30.0, stable_for_sec=1.0)
    observer.start_clock_observation()
    # The caller owns the measurement interval.
    samples = observer.stop_clock_observation()
```

`RosGraphObserver(expected_graph, *, observe_clock, forbidden_graph=None,
node_name="robotics_acceptance_observer", module_loader=import_module,
max_clock_samples=1_000_000)` owns a ROS context, node, executor and spin
thread. Use the installed ROS modules in the selected runtime; `module_loader`
is an injection seam for tests. `snapshot()` observes the configured graph;
discovery is not an atomic snapshot of the distributed system. The observer's
own subscriptions are excluded from subscriber counts. A declared `/clock`
uses its configured QoS; otherwise `observe_clock=True` adds a best-effort,
volatile subscription.

`GraphSnapshot` contains `observed_at_ns`, topic, service, action and
lifecycle mappings, and optional `node_names`. The mappings are copied into
read-only views; `node_names=None` means node presence is unavailable.
`TopicObservation` includes types, publisher and subscriber counts,
`first_message_at_ns` and QoS compatibility. `EndpointObservation` includes
types and server/client counts; `LifecycleObservation` includes state and
observation time. Snapshot time is monotonic nanoseconds, while first-message
and lifecycle observation times are Unix nanoseconds; do not compare their
epochs as if they were the same clock. A ready snapshot is a sampled fact,
not proof of uninterrupted graph state between samples.

`wait_for_readiness(expected_graph, observer, *, timeout_sec, stable_for_sec,
poll_interval_sec=0.1, now_ns=monotonic_ns, sleep_fn=sleep,
on_snapshot=None)` samples the borrowed `GraphObserver` synchronously.
Supply a contract-validated graph, positive finite timeout and poll interval,
a nonnegative finite stability period, and a monotonic nanosecond clock. It
requires one uninterrupted ready window at least as long as the requested and
declared lifecycle stability periods. A sampled issue resets the window.
`on_snapshot` runs synchronously after each snapshot; its exceptions propagate.

The returned `ReadinessResult` contains the final snapshot,
`first_ready_at_ns` and `stable_for_sec`. Missing first-message or lifecycle
facts may trigger their declared deadlines before the overall deadline.
`GraphReadinessTimeout` is a `HarnessError` and `TimeoutError` with
`error_id = "GraphReadinessTimeout.failed"`; its `issues` carry JSON paths,
messages and status. An otherwise ready graph with an insufficient stability
window can time out with no issues.

The timeout is cooperative: snapshot, callback and sleep calls cannot be
interrupted by this function. The implementation checks readiness before its
final deadline check, so a slow call can return ready after the deadline.
Callers requiring a strict budget must enforce an outer process deadline and
reject a late result with their own monotonic deadline check. The helper never
closes the borrowed observer; the caller owns cleanup even on error.

Clock capture starts disabled. `start_clock_observation()` clears prior
samples and overflow state, including when called again.
`stop_clock_observation()` disables capture and returns an immutable tuple of
`ClockSample` values; repeated source times remain in the buffer. Each sample
contains monotonic reception time and integer source nanoseconds. These facts
do not establish UTC offset, delivery latency or physics ticks. Overflow raises
`RosObserverError` rather than returning a truncated success.
`clock_samples` returns a tuple copy without a health or overflow check and
does not replace a successful stop.

`RosObserverError` is a `HarnessError` and `RuntimeError` with
`error_id = "RosObserverError.failed"`. Missing ROS modules and a stopped
executor are among its failure cases; other ROS exceptions may propagate.
`close()` shuts down the executor, removes and destroys the node, and shuts
down the context. It is idempotent after successful closure and may raise if
the executor does not stop. The context manager invokes `close()`; neither
closure nor a readiness result proves that the workload or robot stopped.

## Running the same job locally

From the workspace root, with Docker ready:

```bash
docker build --file packages/harness/tests/live/Dockerfile --tag harness-live:step2 .
mkdir -p artifacts/live
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --mount "type=bind,source=${PWD}/artifacts/live,target=/workspace/artifacts/live" \
  harness-live:step2
```

PowerShell:

```powershell
docker build --file packages/harness/tests/live/Dockerfile --tag harness-live:step2 .
New-Item -ItemType Directory -Force artifacts/live | Out-Null
docker run --rm `
  --mount "type=bind,source=$((Get-Location).Path)/artifacts/live,target=/workspace/artifacts/live" `
  harness-live:step2
```

Use an empty output directory for each run. CLI output, result JSON, evidence
index, Collector configuration/version/log, golden OTLP capture, and test JUnit
remain under `artifacts/live/`. CI uploads them even when a test fails.

On Linux, CI runs the container with the runner's UID/GID so the uploader can
read owner-only result files from the bind mount. `HOME=/tmp` gives ROS a writable
log directory, and the live entrypoint places pytest's cache in the artifact
directory. The harness's result file permissions are preserved.

The image uses the official `ros:jazzy-ros-base` image pinned by digest.
It installs ROS interfaces explicitly and creates a clean
`/usr/bin/python3 -m venv --system-site-packages` environment to use Jazzy's
apt-installed Python bindings. Python dependencies come from the existing lock.
The image runs the installed package and does not copy the host's virtualenv.

The live entrypoint sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. The system packages
needed for `rclpy` also expose ROS pytest plugins; Jazzy's `launch_testing` uses
the removed `pytest_pycollect_makemodule(path, parent)` hook argument and fails
under pytest 9 before test collection. Only automatic entry-point plugin loading
is disabled. Built-in pytest plugins and the explicit repository `conftest.py`
plugins still load, while real ROS bindings and the Collector remain available.

The container uses ROS domain 121 and localhost discovery. Run the tests serially
in an isolated domain; another `/clock` publisher would invalidate the fixture.
On an existing Jazzy host with the same dependencies and a Collector binary on
`PATH`, source `/opt/ros/jazzy/setup.bash`, then run from the workspace root:

```bash
cd packages/harness
ROBOTICS_LIVE_ROS=1 ROS_DOMAIN_ID=121 \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
  python -m pytest tests/live -m live_ros -ra
```

Ordinary `pytest` collects and skips these tests unless `ROBOTICS_LIVE_ROS=1`.
With opt-in enabled, missing Jazzy, `rclpy`, interfaces, or Collector is a failure,
never a skip. The Docker job always enables opt-in. The marker is registered in
`tests/live/conftest.py`; no shared pytest configuration change is required.

References: [Jazzy lifecycle API](https://docs.ros.org/en/jazzy/p/rclpy/rclpy.lifecycle.html)
and [Collector file exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.148.0/exporter/fileexporter).
