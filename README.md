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
logic and vision models. Home machine administration is a separate project and
supplies target prerequisites.

## Start with the part you need

Use contracts to validate files independently of ROS or a simulator. Use the
harness to evaluate evidence for a supported qualification profile. Use infra
to launch a composition and record what actually ran.

The published pair is
[contracts 0.19.0](https://pypi.org/project/robotics-runtime-contracts/0.19.0/) and
[harness 0.20.1](https://pypi.org/project/robotics-acceptance-harness/0.20.1/):

```bash
python -m pip install robotics-runtime-contracts==0.19.0 robotics-acceptance-harness==0.20.1
robotics-contracts --help
robotics-acceptance --help
```

Package reference:
[contracts](packages/contracts/README.md),
[harness](packages/harness/README.md),
[consumer examples](packages/contracts/consumer-examples/README.md).

Harness requires contracts `>=0.19,<0.20`; release checks install the exact
published pair outside the workspace. Package installation does not qualify
a simulator, image, accelerator or physical target.

The compiled host is available as the immutable
[host 0.1.0-rc.0 prerelease](https://github.com/mmkolpakov/robotics-runtime/releases/tag/host-v0.1.0-rc.0).
Its TGZ installs as an ordinary npm dependency using Node 24.21.0 and npm 11.19.0:

```bash
npm install --ignore-scripts --save-exact https://github.com/mmkolpakov/robotics-runtime/releases/download/host-v0.1.0-rc.0/robotics-runtime-host-0.1.0-rc.0.tgz
```

The release includes a source manifest, checksums and the external installation
report. Host package integrity and provider execution qualification have separate
scopes; see the [host reference](host/README.md).

## Architecture

These C4 views cover the joint platform in both repositories. The Python pair and
compiled host have separate releases; candidate providers require their own
execution qualification.

### Process composition

<!-- architecture:Container:start -->

![Execution and external Test boundaries](docs/architecture/generated/Container.svg)

[Canonical C4 source](docs/architecture/workspace.dsl) · [Generated Mermaid](docs/architecture/generated/structurizr-Container.mmd)

<!-- architecture:Container:end -->

Colors distinguish roles: composition, published Python tools, native candidates,
media and retained files. They are not qualification verdicts. Control and video
use their native connections; lifecycle completion and evidence evaluation are
separate outcomes.

<details>
<summary>C4 context — product boundaries and external systems</summary>

<!-- architecture:Context:start -->

![Platform context](docs/architecture/generated/Context.svg)

[Canonical C4 source](docs/architecture/workspace.dsl) · [Generated Mermaid](docs/architecture/generated/structurizr-Context.mmd)

<!-- architecture:Context:end -->

</details>

[Native interfaces](docs/architecture/generated/NativeInterfaces.svg) and
[consumer interfaces](docs/architecture/generated/ConsumerInterfaces.svg)
separate SDK/media paths from document and evaluation dependencies.
The [complete graph](docs/architecture/generated/ContainerDetail.svg) remains
available as a reference.

[Diagram sources, sequence and deployment](docs/architecture/README.md).

The selected host uses upstream [Cordis](https://github.com/cordiverse/cordis)
for local plugin loading, service bindings and managed effects. Cluster scheduling
belongs to the deployment backend.
The host coordinates resources; commands and frames use native SDK and media
connections. Its implementation and simulator providers are separate from the
published Python pair.

[Composition framework and its limits](docs/architecture.md#composition-framework).
The process overview shows execution/evidence and the optional external Test boundary;
[complete worker and tool interfaces](docs/architecture/generated/ContainerDetail.svg)
are shown separately.

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
SignalFlag SDK 1.8.0 recipe: existing project/branch, explicit JWT and disabled
configuration synchronization. It retains opaque uploads through existing custody
tools. This source service is separate from native execution and qualification;
it has no published API image release.

## Host development

The source host uses the pinned Node version in `host/.node-version`.
Its own lockfile is separate from the Python workspace:

```bash
npm --prefix host ci --ignore-scripts
npm --prefix host test
npm --prefix host run check:boundary
```

See [host configuration and worker integration](host/README.md).
The compiled host prerelease has passed package and external installation checks.
A new host/provider composition still requires its own consumer qualification.

The separate `host-release.yml` workflow builds the compiled core host as a
GitHub Release TGZ, retaining `private: true` and ordinary npm `file:` installation.
PR and manual runs check the archive, a clean rebuild and installation outside
the source workspace; they do not publish or establish native acceptance.

The first host prerelease is published with release immutability enabled.
Further publication requires the current setting, the exact live tag and the
accepted archive to be verified. Historical immutable releases do not prove the
current setting. Its authenticated settings
API requires Administration read, which the workflow's ordinary GitHub token
cannot acquire; missing authorization does not mean the setting is disabled.

The owner then completes the current host/provider source cohort, including
cancellation and retained verification after source deletion, and sets
`HOST_QUALIFIED_SOURCE_SHA` and `HOST_QUALIFIED_ASSET_SHA256`. The built archive
and source tree must match that explicit reference. Its original source identity
is retained separately from the actual release tag/build commit. Only then enable
`HOST_RELEASE_PUBLISH_ENABLED=true` and create a unique tag that exactly matches
`host-v<host/package.json version>` and belongs to main.

The current host version is an RC; this package path grants no general simulator,
hardware or cloud qualification. Published artifacts require a fresh independent
consumer of the admitted profiles. Existing PyPI environments and their required
reviews remain separate.

The workflow stages new assets as a draft, not a completed host release. Before
accepting a new or existing draft, it downloads the five expected assets to a
fresh directory, compares every byte with this run and requires the exact remote
asset set. Partial, stale or surplus drafts fail without replacing remote assets.
After the accepted source cohort and current setting are verified, the owner uses
stock
`gh release edit <tag> --draft=false` to publish, rechecking the live peeled tag
against the built manifest and tag-trigger SHA immediately before that transition.
Repeat the workflow's `check_draft_assets` and `check_live_tag` functions with
the same archived run inputs immediately before that transition. An earlier draft
check does not freeze mutable assets.
A refused draft requires explicit owner repair before retrying.
No new approval environment or credential service is introduced.

For an existing published release, the job requires `isImmutable`, verifies the
signed release with `gh release verify --format json`, rechecks the locked live
commit and verifies each immutable asset. Release jobs recheck the live
peeled tag against the actual build and tag-trigger commit, independently of the
earlier byte-equivalent reference, and never replace existing tags or release assets.

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
