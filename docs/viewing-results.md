# Inspect results and native recordings

Start with the canonical verdict and its causes:

```bash
robotics-acceptance why --format markdown assessment/acceptance-result.json
```

Use the accompanying JUnit XML in your CI report viewer. JSON retains the source
identities and observation coverage; JUnit reports assertion outcomes. A successful
`why` invocation explains the stored verdict and does not change a failed or
incomplete result into a pass. The [optional MCP adapter](../mcp/README.md) exposes
these same document operations without starting or evaluating a workload.

## Open the original format

[Rerun](https://rerun.io/docs/concepts/logging-and-ingestion/mcap) opens MCAP and
its native RRD recordings. Its MCAP importer decodes supported ROS 2 and Protobuf
messages; visual mappings depend on the message schema and installed decoder.
For a compatible retained recording:

```bash
rerun archive/recording.mcap
```

Rerun 0.41.0 includes a
[stock Viewer MCP server](https://github.com/rerun-io/rerun/blob/0.41.0/docs/content/reference/viewer/mcp.md).
Configure a compatible stdio client to launch `rerun viewer-mcp`; it connects to
an already running local Viewer over gRPC, without a hosted Hub. Its tools inspect
viewer state and recording schemas, select the time cursor, change blueprints and
save screenshots. These viewer controls have broader UI effects than the six
offline domain tools; use the existing server directly without another adapter.

Choose the recording's declared clock and timestamp field when navigating it.
Rerun's [MCAP import](https://github.com/rerun-io/rerun/blob/0.41.0/docs/content/concepts/logging-and-ingestion/mcap/message-formats.md)
keeps log, publish and payload-header timelines distinct; its timestamp heuristics
do not establish an authoritative clock relation. Retain layouts, screenshots and
converted RRD files as derived outputs with source identities. Open original
evidence read-only and write derived outputs separately; viewing does not change
the retained qualification verdict.

[PlotJuggler](https://github.com/PlotJuggler/PlotJuggler) provides MCAP and PX4 ULog
loaders for time-series inspection. Install the relevant loader and message parser
from its supported plugin distribution; not every installation includes every
plugin. Open a compatible `.mcap` or `.ulg` through its file loader. ROS live-stream
plugins are separate from file loading.

A file extension alone does not establish decodability. Select the timestamp
field and clock declared by the recording/profile. A viewer timeline does not
establish a relation between different clocks. Keep exact integer timestamps and
source hashes in the original evidence rather than relying on displayed values.

Keep ULog, HDF5, USD and Webots WBT assets in their native formats. Use the owning
SDK or application where the selected viewer has no compatible loader. The runtime
does not convert every artifact to MCAP or RRD. If you create a derived viewer
recording, retain it separately with its source identity; it does not replace the
original evidence. A readable plot cannot supply an observation that was not
measured or establish qualification.
