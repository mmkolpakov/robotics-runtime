# Robotics runtime host

The host composes finite workers with upstream Cordis 4.0.0-rc.10, Loader 1.0.0-rc.7 and Include 1.1.0. Node 24.21.0, npm 11.19.0 and TypeScript 7.0.2 are pinned. Python packages remain in their existing uv workspace. Simulator libraries belong to selected worker environments.

Run `npm ci --ignore-scripts`, `npm test` and `npm run check:boundary` from this directory. The strict compiler checks upstream declarations without `skipLibCheck`, overrides or vendor patches. Sources compile to ESM with `.js` imports.

The native command is `cordis` in a directory containing `cordis.yml`. The native Include file is an array of entries with `id`, `name` and `config`. Include supports executable `!!js` expressions: deployment profiles and their complete module closure must be trusted and immutable. Context isolation is dependency scoping.

`createHost({ baseDirectory })` supplies the upstream Context and Loader. Awaiting a Fiber or Loader task proves task completion; a missing import can leave no Fiber and a required injection can remain PENDING. Required Fiber ACTIVE, binding existence and backend readiness are independent admission facts.

The host uses native Cordis logging and the console exporter. js-yaml 4.3.2 satisfies Include's upstream `^4.1.0` range and replaces the initially proposed 4.1.1 pin to address the published YAML CPU denial-of-service advisories. Native Include/CLI tests exercise the patched package.

Jobs is a Cordis service that invokes Execa 10.0.1 with literal argv, bounded wall timeout and output buffers, cancellation, exit status and retained diagnostics. Each owner cancels and reaps its own outstanding subprocesses. No shell command string is accepted. The environment can pin the selected execution endpoint explicitly.

Documents and Evaluation provide paths and CLI arguments to the installed `robotics-contracts` and `robotics-acceptance` commands. `WorkerCommand.prefixArgs` can select a finite worker launcher; no second evaluator, document serializer or frame bus is introduced. Evaluation windows accept decimal strings or bigint, preserving integers beyond JavaScript's safe range. Inputs and signed documents remain files; Node never reads and writes a parsed subject document.

For integration, install the existing Python workspace with `uv sync --locked --all-packages`, then run `npm run test:workers`. Optional `RR_CONTRACTS_COMMAND`, `RR_ACCEPTANCE_COMMAND` and `RR_PYTHON_COMMAND` name installed commands. Tests exercise real CLI errors, Python's exact writer, unchanged input hashes, JSON/JUnit results and raw-evidence diagnostics. The empty-metric fixture deliberately produces a non-PASS result; it does not qualify simulation behavior.
