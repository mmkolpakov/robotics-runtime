# Robotics runtime

Evaluate robotic software from recorded evidence and inspect why a check passed,
failed or remains incomplete.

## Start with the part you need

- [Produce a first result](docs/first-result.md): install the published Python
  tools, create example inputs, evaluate them and inspect an integrity refusal.
- [Inspect recorded results](docs/viewing-results.md): open the evidence and read
  the reported causes and coverage.
- [Run a selected execution profile](https://github.com/mmkolpakov/robotics-runtime-infra):
  use the infrastructure repository's images, workload and qualification guides.
- [Integrate a consumer](packages/contracts/consumer-examples/README.md): use the
  public document APIs and CLI; [MCP](mcp/README.md) exposes offline document tools
  to agents.

The Python document path needs neither Node nor ROS. The
[compatibility reference](packages/harness/docs/compatibility.md) describes
package lines and the components that must be selected together. Installing the
packages does not qualify a simulator, image, accelerator or physical target.

This repository contains two independently versioned Python packages:
[contracts](packages/contracts/README.md) validates and writes documents, while
[harness](packages/harness/README.md) observes an existing execution and evaluates
retained evidence. The host, Test API and MCP packages provide separate interfaces.

[robotics-runtime-infra](https://github.com/mmkolpakov/robotics-runtime-infra)
owns worker images, simulator providers, deployment and execution qualification.
Consumers own robot models, scenes, control logic and vision models; operators
supply the selected host environment.

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
<summary>C4 context: product boundaries and external systems</summary>

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

The host uses [Cordis](https://github.com/cordiverse/cordis) for resource
composition. Native control and media stay with the selected SDK and provider.

- [Host reference](host/README.md): configuration and worker integration.
- [External Test API](docs/external-test-api.md): a source service for selected SDK
  operations; its reference describes the scope and deployment requirements.
  It has no published API image.
- [Offline MCP](mcp/README.md): six document tools and their packaged distribution.
- [Architecture reference](docs/architecture.md): component, time and evidence
  ownership; [implementation references](docs/future-designs.md) link the design
  to available interfaces.

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
`docs/reader/build.py`. Installation pins belong to the executable examples;
release prerequisites and dependency pins stay in their package and release
metadata. Archived examples and qualification records retain their original pins.
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
