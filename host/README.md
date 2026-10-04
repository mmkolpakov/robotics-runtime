# Robotics runtime host

The host composes finite workers with upstream Cordis 4.0.0-rc.10, Loader 1.0.0-rc.7 and Include 1.1.0. Node 24.21.0, npm 11.19.0 and TypeScript 7.0.2 are pinned. Python packages remain in their existing uv workspace. Simulator libraries belong to selected worker environments.

Run `npm ci --ignore-scripts`, `npm test` and `npm run check:boundary` from this directory. The strict compiler checks upstream declarations without `skipLibCheck`, overrides or vendor patches. Sources compile to ESM with `.js` imports.

The native command is `cordis` in a directory containing `cordis.yml`. The native Include file is an array of entries with `id`, `name` and `config`. Include supports executable `!!js` expressions: deployment profiles and their complete module closure must be trusted and immutable. Context isolation is dependency scoping.

`createHost({ baseDirectory })` supplies the upstream Context and Loader. Awaiting a Fiber or Loader task proves task completion; a missing import can leave no Fiber and a required injection can remain PENDING. Required Fiber ACTIVE, binding existence and backend readiness are independent admission facts.

The host uses native Cordis logging and the console exporter. js-yaml 4.3.2 satisfies Include's upstream `^4.1.0` range and replaces the initially proposed 4.1.1 pin to address the published YAML CPU denial-of-service advisories. Native Include/CLI tests exercise the patched package.
