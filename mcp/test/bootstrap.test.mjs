import assert from 'node:assert/strict';
import { test, mock } from 'node:test';
import { appendFile, mkdtemp, open, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { readBootstrap } from '../src/bootstrap.mjs';

test('bootstrap accepts one regular small document and refuses oversized bytes', async t => {
  const root = await mkdtemp(join(tmpdir(), 'mcp-bootstrap-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const path = join(root, 'config.json');
  await writeFile(path, '{}');
  assert.deepEqual(await readBootstrap(path), {});
  await writeFile(path, Buffer.alloc(65537, 32));
  await assert.rejects(readBootstrap(path), /64 KiB/);
});

test('concurrent bootstrap growth is refused while each FD read stays capped', async t => {
  const root = await mkdtemp(join(tmpdir(), 'mcp-bootstrap-growth-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const path = join(root, 'config.json');
  await writeFile(path, '{}');
  const probe = await open(path, 'r'), prototype = Object.getPrototypeOf(probe);
  await probe.close();
  const original = prototype.read;
  let grown = false, maximumRequest = 0;
  const control = mock.method(prototype, 'read', async function(buffer, offset, length, position) {
    maximumRequest = Math.max(maximumRequest, length);
    if (!grown) { grown = true; await appendFile(path, Buffer.alloc(70000, 32)); }
    return original.call(this, buffer, offset, length, position);
  });
  t.after(() => control.mock.restore());
  await assert.rejects(readBootstrap(path), /changed/);
  assert.equal(grown, true);
  assert.ok(maximumRequest <= 65537);
});
