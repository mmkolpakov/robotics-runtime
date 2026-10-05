import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { mkdtemp, open, writeFile, symlink, link, rm } from 'node:fs/promises';
import type { FileHandle } from 'node:fs/promises';
import { syncBuiltinESMExports } from 'node:module';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { referenceFile } from '../src/index.js';
import type { FileReferenceOptions } from '../src/index.js';

async function fixture(work: (directory: string, path: string, bytes: Buffer) => Promise<void>): Promise<void> {
  const directory = await mkdtemp(join(tmpdir(), 'rr-reference-'));
  const path = join(directory, 'evidence.bin');
  const bytes = Buffer.alloc(256 * 1024, 0x35);
  try { await writeFile(path, bytes); await work(directory, path, bytes); }
  finally { await rm(directory, { recursive: true, force: true }); }
}

/** Schedule real filesystem changes at native stream events, with no timing sleeps. */
async function duringRead(path: string, event: 'data' | 'end', change: () => void, work: () => Promise<void>): Promise<void> {
  const probe = await open(path, 'r');
  const prototype = Object.getPrototypeOf(probe) as FileHandle;
  await probe.close();
  const original = prototype.createReadStream;
  let changes = 0;
  let captured: FileHandle | undefined;
  prototype.createReadStream = function(options) {
    captured = this;
    const stream = original.call(this, options);
    stream.once(event, () => { changes++; change(); });
    return stream;
  };
  try { await work(); assert.equal(changes, 1, 'filesystem change occurred during capture'); }
  finally { prototype.createReadStream = original; }
  if (captured) await assert.rejects(captured.stat(), { code: 'EBADF' });
}

test('references original bytes and preserves file URI aliases', async () => {
  await fixture(async (directory, path, bytes) => {
    const expected = { sha256: createHash('sha256').update(bytes).digest('hex'), size_bytes: bytes.length };
    for (const alias of [path, join(directory, 'symbolic.bin'), join(directory, 'hard.bin')]) {
      if (alias.endsWith('symbolic.bin')) await symlink(path, alias);
      if (alias.endsWith('hard.bin')) await link(path, alias);
      assert.deepEqual(await referenceFile(alias), { uri: pathToFileURL(alias).href, ...expected });
    }
  });
});

test('empty files can use a zero-byte limit', async () => {
  await fixture(async (_directory, path) => {
    await writeFile(path, '');
    assert.deepEqual(await referenceFile(path, { maxBytes: 0 }), {
      uri: pathToFileURL(path).href, sha256: createHash('sha256').digest('hex'), size_bytes: 0,
    });
  });
});

test('optional limits accept the exact size and reject oversized or invalid input', async () => {
  await fixture(async (_directory, path, bytes) => {
    assert.equal((await referenceFile(path, { maxBytes: bytes.length })).size_bytes, bytes.length);
    await assert.rejects(referenceFile(path, { maxBytes: bytes.length - 1 }), /exceeds maxBytes/);
    for (const maxBytes of [-1, 0.5, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
      await assert.rejects(referenceFile(path, { maxBytes }), RangeError);
    }
  });
});

test('capture snapshots its optional limit before asynchronous work', async () => {
  await fixture(async (_directory, path, bytes) => {
    const options: FileReferenceOptions = { maxBytes: bytes.length };
    const capture = referenceFile(path, options);
    options.maxBytes = 0;
    assert.equal((await capture).size_bytes, bytes.length);
  });
});

test('large files stream without a whole-file read or a mandatory default cap', async () => {
  await fixture(async (_directory, path) => {
    const chunk = Buffer.alloc(64 * 1024, 0x81);
    const expected = createHash('sha256');
    const writer = await open(path, 'w');
    try {
      for (let index = 0; index < 1024; index++) { await writer.write(chunk); expected.update(chunk); }
    } finally { await writer.close(); }
    const originalReadFile = fs.promises.readFile;
    const prototype = Object.getPrototypeOf(writer) as FileHandle;
    const originalHandleReadFile = prototype.readFile;
    const forbidden = async (): Promise<never> => { throw new Error('whole-file reads are forbidden'); };
    fs.promises.readFile = forbidden;
    prototype.readFile = forbidden;
    syncBuiltinESMExports();
    try {
      const ref = await referenceFile(path);
      assert.equal(ref.size_bytes, 64 * 1024 * 1024);
      assert.equal(ref.sha256, expected.digest('hex'));
    } finally {
      fs.promises.readFile = originalReadFile; prototype.readFile = originalHandleReadFile;
      syncBuiltinESMExports();
    }
  });
});

test('same-size rewrites while streaming are rejected', async () => {
  await fixture(async (_directory, path, bytes) => {
    await duringRead(path, 'data', () => fs.writeFileSync(path, Buffer.alloc(bytes.length, 0x74)),
      async () => { await assert.rejects(referenceFile(path), /changed during capture/); });
  });
});

test('truncation while streaming is rejected', async () => {
  await fixture(async (_directory, path) => {
    await duringRead(path, 'data', () => fs.truncateSync(path, 1),
      async () => { await assert.rejects(referenceFile(path), /changed during capture/); });
  });
});

test('growth is bounded by the original extent even without an optional cap', async () => {
  await fixture(async (_directory, path) => {
    await duringRead(path, 'data', () => fs.appendFileSync(path, Buffer.alloc(1024 * 1024)),
      async () => { await assert.rejects(referenceFile(path), /changed during capture/); });
  });
});

test('growth beyond the selected byte limit is rejected during streaming', async () => {
  await fixture(async (_directory, path, bytes) => {
    await duringRead(path, 'data', () => fs.appendFileSync(path, 'extra'),
      async () => { await assert.rejects(referenceFile(path, { maxBytes: bytes.length }), /exceeds maxBytes/); });
  });
});

test('replacement with identical bytes cannot substitute the opened file', async () => {
  await fixture(async (directory, path, bytes) => {
    const replacement = join(directory, 'replacement.bin');
    await writeFile(replacement, bytes);
    await duringRead(path, 'data', () => fs.renameSync(replacement, path),
      async () => { await assert.rejects(referenceFile(path), /changed during capture/); });
  });
});

test('a same-size change after the last byte is read is rejected', async () => {
  await fixture(async (_directory, path, bytes) => {
    await duringRead(path, 'end', () => fs.writeFileSync(path, Buffer.alloc(bytes.length, 0x26)),
      async () => { await assert.rejects(referenceFile(path), /changed during capture/); });
  });
});

test('a path removed after the last read reports a changed capture', async () => {
  await fixture(async (_directory, path) => {
    await duringRead(path, 'end', () => fs.unlinkSync(path),
      async () => { await assert.rejects(referenceFile(path), /changed during capture/); });
  });
});

test('retargeted symbolic aliases cannot substitute a different file', async () => {
  await fixture(async (directory, path, bytes) => {
    const alias = join(directory, 'alias.bin'), replacement = join(directory, 'replacement.bin');
    await symlink(path, alias); await writeFile(replacement, bytes);
    await duringRead(alias, 'end', () => { fs.unlinkSync(alias); fs.symlinkSync(replacement, alias); },
      async () => { await assert.rejects(referenceFile(alias), /changed during capture/); });
  });
});

test('nonregular evidence is rejected before streaming', async () => {
  await fixture(async directory => { await assert.rejects(referenceFile(directory), /regular file/); });
});
