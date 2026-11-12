# Robotics runtime

Contracts and evidence tools for composing and qualifying robotic software.

The workspace contains two independently versioned Python packages:

- **robotics-runtime-contracts** validates execution, evidence and qualification
  documents, and writes artifacts without changing signed bytes.
- **robotics-acceptance-harness** observes an existing execution and evaluates
  retained evidence. It does not launch services or control a robot.

[robotics-runtime-infra](https://github.com/mmkolpakov/robotics-runtime-infra)
owns worker images, simulator providers, product provisioning, deployment and
execution qualification. Product repositories own robot models, scenes, control
logic and vision models. Deployment operators supply host prerequisites.

## Start with the part you need

[Install the published Python tools and produce your first result](docs/first-result.md).
The guide includes downloadable exact inputs, their producers, expected JSON/JUnit,
exit codes and an integrity refusal. The document path needs no Node or ROS.

Use contracts to validate files independently of ROS or a simulator. Use the
harness to evaluate evidence for a supported qualification profile. Use infra
to launch a composition and record what actually ran.

The published pair is
[contracts 0.21.1](https://pypi.org/project/robotics-runtime-contracts/0.21.1/) and
[harness 0.22.3](https://pypi.org/project/robotics-acceptance-harness/0.22.3/):

```bash
python -m pip install robotics-runtime-contracts==0.21.1 robotics-acceptance-harness==0.22.3
robotics-contracts --help
robotics-acceptance --help
```

Package reference:
[contracts](packages/contracts/README.md),
[harness](packages/harness/README.md),
[consumer examples](packages/contracts/consumer-examples/README.md).

Harness requires contracts `>=0.21,<0.22`; release checks install the exact
published pair outside the workspace. Package installation does not qualify
a simulator, image, accelerator or physical target.

The compiled host is available as the immutable
[host 0.1.0-rc.1 prerelease](https://github.com/mmkolpakov/robotics-runtime/releases/tag/host-v0.1.0-rc.1).
Its TGZ installs as an ordinary npm dependency using Node 24.21.0 and npm 11.19.0:

```bash
npm install --ignore-scripts --save-exact https://github.com/mmkolpakov/robotics-runtime/releases/download/host-v0.1.0-rc.1/robotics-runtime-host-0.1.0-rc.1.tgz
```

The release includes a source manifest, checksums and the external installation
report. Host package integrity and provider execution qualification have separate
scopes; see the [host reference](host/README.md).

## Architecture

These views describe the target architecture across both repositories. They are
not a list of released commands or qualified profiles. Use the package and host
references above for available interfaces, and the
[architecture reference](docs/architecture.md) for the target boundaries.

### Process composition

<!-- architecture:Container:start -->

![Target platform composition](docs/architecture/generated/Container.svg)

[Canonical C4 source](docs/architecture/workspace.dsl) · [Generated Mermaid](docs/architecture/generated/structurizr-Container.mmd)

<!-- architecture:Container:end -->

Colors distinguish roles: composition, published Python tools, native workers,
media and retained files. They are not qualification verdicts. Control and video
use their native connections; lifecycle completion and evidence evaluation are
separate outcomes.

<details>
<summary>C4 context — product boundaries and external systems</summary>

<!-- architecture:Context:start -->

![Verification workflow context](docs/architecture/generated/Context.svg)

[Canonical C4 source](docs/architecture/workspace.dsl) · [Generated Mermaid](docs/architecture/generated/structurizr-Context.mmd)

<!-- architecture:Context:end -->

</details>

[Native interfaces](docs/architecture/generated/NativeInterfaces.svg) and
[consumer interfaces](docs/architecture/generated/ConsumerInterfaces.svg)
separate SDK/media paths from document and evaluation dependencies.
The [complete graph](docs/architecture/generated/ContainerDetail.svg) remains
available as a reference.

[Diagram sources, sequence and deployment](docs/architecture/README.md).

The host can coordinate resources through upstream
[Cordis](https://github.com/cordiverse/cordis). Campaign orchestration is external;
commands and frames use native SDK and media connections.

[Composition framework and its limits](docs/architecture.md#composition-framework).
Common document/evaluation code does not require Gazebo, Isaac Sim, Webots or
ROS. Engine-specific APIs and assets belong to selected infra providers.
Simulator support does not imply the same physics, frame output or autopilot
integration in every backend.

The [architecture reference](docs/architecture.md) describes repository
boundaries, native API lines, time and evidence ownership, and qualification.
Current public compatibility is recorded in
[harness compatibility](packages/harness/docs/compatibility.md) and the package
[compatibility policy](packages/contracts/COMPATIBILITY.md).

The optional [external Test API](docs/external-test-api.md) supports a limited
SignalFlag SDK 1.8.0 recipe: existing project/branch, explicit JWT, configuration
sync and six REST operations. It stores immutable configuration snapshots and
retains opaque uploads through existing custody tools. This source service is separate from
native execution and qualification;
it has no published API image release.

The [optional offline MCP package](mcp/README.md) provides six read tools through
stdio. Its [Linux MCPB release](https://github.com/mmkolpakov/robotics-runtime/releases/tag/mcp-v0.1.0-rc.1)
uses separately installed published CLI workers.

[Architecture and implementation references](docs/future-designs.md) connect the
target design to the current package references.

## Host development

The TypeScript packages `host`, `api` and `mcp` form one npm workspace with the Node version in
`.node-version` and a single root npm lockfile. Internal dependencies link the workspace host
directly, so development needs no release archive:

```bash
npm ci --ignore-scripts
npm run build --workspace @robotics-runtime/host
npm test --workspace @robotics-runtime/host
npm run check:boundary --workspace @robotics-runtime/host
```

[Host configuration and worker integration](host/README.md) describes admission,
native clients and retained recovery.
[Host publication](docs/releasing.md#compiled-host) covers the separate TGZ release,
immutable assets and independent consumer checks.

## Development

Use Python 3.12–3.14 and uv. One workspace lock installs both packages:

```bash
uv sync --locked --all-packages --all-groups
uv run --directory packages/contracts pytest
uv run --directory packages/harness pytest
uv run ruff check packages
uv run --directory packages/contracts mypy src tests
uv run --directory packages/harness mypy src tests
uv run python scripts/ci/check_complexity.py
```

Run the package suites in separate processes: each has a `tests` support module.
Build distributions independently:

```bash
uv build --package robotics-runtime-contracts --no-sources
uv build --package robotics-acceptance-harness --no-sources
```

The editable workspace override is for development. Wheels retain normal
versioned dependencies and are verified in clean consumer environments before
publication. Shared CI checks Python 3.12, 3.13 and 3.14 and
[live ROS observer behavior](packages/harness/docs/live-tests.md) on Jazzy.

[Complexity budgets](quality/README.md) keep existing debt visible.
[Release procedure](docs/releasing.md) explains package tags, artifacts and
consumer verification. Source history lives in `packages/contracts` and
`packages/harness`; older tags have `contracts-legacy/` and
`harness-legacy/` prefixes.

## Documentation reader

Edit the public Markdown, SVG and canonical diagram sources in this repository.
The reader uses the stock Sphinx, MyST and Furo toolchain; its source allowlist is in
`docs/reader/build.py`. Keep release instructions current
when package versions or interfaces change. Preserve the exact version and commit
pins in archived examples and qualification records.
The LLM export includes current guidance and the C4 DSL and Mermaid sequence/state
sources exactly once. Historical run records, ADRs and migration archives remain readable in HTML
and the source download but are excluded from the LLM text. The source archive
and manifest bind the exported bytes to the build.
The consumer-inputs archive contains the first-result producer and templates.

Build and check documentation in a separate Python 3.12 environment:

```bash
uv venv .docs-venv --python 3.12
uv pip sync --python .docs-venv/bin/python --require-hashes docs/reader/requirements.lock
.docs-venv/bin/python docs/reader/build.py
```

Refresh the documentation dependency lock, then run the build and CI audit:

```bash
uv pip compile docs/reader/requirements.in --generate-hashes --python-version 3.12 --output-file docs/reader/requirements.lock
```

Open `build/docs/html/index.html` or serve that directory locally. The strict PR
build checks document references; the existing scheduled `links` workflow checks
external links. Main rebuilds the reader from committed source through the Pages
workflow. Generated HTML, text and downloads stay in the ignored `build/` directory.
