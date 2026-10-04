import { readFile, mkdir, writeFile, chmod } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
const inputs = JSON.parse(await readFile('test/native-inputs.json', 'utf8'));
const identity = execFileSync('podman', ['image', 'inspect', inputs.media_image, '--format', '{{.Id}}'], { encoding: 'utf8' }).trim();
if (identity.replace(/^sha256:/, '') !== inputs.media_image_id.replace(/^sha256:/, '')) throw new Error('native media worker image differs from qualified source');
const raw = Buffer.from(await (await fetch(inputs.tini.url, { signal: AbortSignal.timeout(30000) })).arrayBuffer());
if (createHash('sha256').update(raw).digest('hex') !== inputs.tini.sha256) throw new Error('project Tini identity mismatch');
await mkdir('.tools', { recursive: true });
await writeFile('.tools/tini', raw); await chmod('.tools/tini', 0o755);
const path = resolve('.');
execFileSync('podman', ['run', '--rm', '--userns=keep-id:uid=1000,gid=1000', '--user', '1000:1000',
  '-v', path + ':/workspace', '-v', '/usr/local/bin/uv:/uv:ro', '-w', '/workspace', '--entrypoint', '/bin/sh',
  inputs.media_image, '-c', '/uv venv --clear .tools/mavlink --python /usr/bin/python3 && /uv pip sync --python .tools/mavlink/bin/python --require-hashes test/requirements-mavlink.lock'], { stdio: 'inherit', timeout: 120000 });
console.log('native test input identities prepared');
