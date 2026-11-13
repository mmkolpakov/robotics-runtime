# CI executors

The software workflows accept the repository variable `ROBOTICS_CI_EXECUTOR`.
Its default is `hosted`. Set it to `home` to select the corresponding registered
self-hosted runner; an unknown value fails job selection. No repository variable
or runner registration is changed by adding these workflows.

| Executor | x64 jobs | ARM64 build jobs |
| --- | --- | --- |
| `hosted` | `ubuntu-24.04` | `ubuntu-24.04-arm` |
| `home` | `self-hosted`, `linux`, `x64`, `robotics-ci-home` | `self-hosted`, `linux`, `arm64`, `robotics-ci-home` |

The labels are requirements, not evidence that a runner exists or that hardware
has been qualified. With no matching runner a home job waits; it never falls back
to a hosted runner. ARM64 software builds and native device qualification are
separate capabilities.

Every selected software job starts with the pinned executor action before
checkout or project commands. It checks the reported execution environment,
Linux architecture and event identity. Home checks admit same-repository pull
requests, exact branch pushes, main-branch manual/scheduled runs, and matching
merge-group references. Fork pull requests and unrecognized events are refused.
Cleanup steps do not run when that preflight fails.

This check is defense in depth, not a security boundary against a pull request
that rewrites its own workflow. Before enabling a home runner, its administrator
must enforce approvals for **all external contributors**, isolate jobs and
credentials, and restrict runner access to the enrolled repository. A past
approval for a contributor does not approve their future workflow changes.
The runner must not share deployment credentials or control of other projects.
A `home` setting alone does not establish those controls.

Use the same project commands on each executor. Install the pinned toolchain in
the runner environment; do not alias Docker to Podman. Docker/Buildx, architecture
and resource behavior must be checked on that environment. No workstation-wide
services or other projects are configured by these repositories.

## Release trust

Selecting `home` does not grant a new signing identity. Jobs that create GitHub
provenance refuse home execution until a separate home-builder profile has been
admitted. Read-only verification of existing signed artifacts can run at home.
The published GitHub-hosted trust profile, immutable releases and verifier rules
remain unchanged. Package authenticity and native qualification are separate.

The executor selector is an execution path for the listed checks, not evidence
that every CI job already runs at home. Complete home CI also requires runner
enrollment/tooling and the release/provenance profile below.

A path-filtered success is not evidence that the full matrix ran at home.
Complete home validation must force the applicable build and qualification
jobs at one reviewed commit, retain their actual outcomes, and exercise the
publisher profile separately. An unavailable capability remains unverified.

## Workflow coverage

- `ci.yml`: Python 3.12/3.13/3.14 package matrix, quality and compatibility,
  installed consumers, ROS observation, MCP and installed MCP.
- `host.yml` and `external-test-api.yml`: existing Node host/API checks.
- `docs.yml` build and `links.yml`: documentation build and link checks.
- `ci.yml` evaluator admission creates a GitHub attestation; home execution fails
  at preflight until its new trust profile is admitted.
- `release.yml`, `host-release.yml` and the `docs.yml` deployment job retain their
  hosted execution and existing publication rules. They are outside this selector
  and must be migrated explicitly before claiming complete home CI.

The action is pinned to an immutable commit in this repository. A fork adopting
these checks must review and repin that action and its check-issuer policy.
