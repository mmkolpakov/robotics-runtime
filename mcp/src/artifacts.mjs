import { constants } from 'node:fs';
import { chmod, lstat, mkdtemp, open, realpath, rm } from 'node:fs/promises';
import { isAbsolute, join, relative, resolve, sep } from 'node:path';
import { referenceFile } from '@robotics-runtime/host';

const identifier = /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$/;
const digest = /^[a-f0-9]{64}$/;
const unchanged = (a, b) => a.dev === b.dev && a.ino === b.ino && a.size === b.size
  && a.mtimeNs === b.mtimeNs && a.ctimeNs === b.ctimeNs && b.isFile();

export async function createArtifactRegistry(config) {
  const root = resolve(config.artifactRoot);
  const scratch = resolve(config.scratchRoot);
  for (const directory of [root, scratch]) {
    const stat = await lstat(directory);
    if (!isAbsolute(directory) || !stat.isDirectory() || stat.isSymbolicLink()
      || await realpath(directory) !== directory || (stat.mode & 0o022)) {
      throw new Error('artifact and scratch roots must be canonical private directories');
    }
  }
  const records = new Map();
  if (!Array.isArray(config.artifacts) || config.artifacts.length > 64) throw new Error('invalid artifact registry');
  for (const record of config.artifacts) {
    if (!identifier.test(record.id) || records.has(record.id) || typeof record.path !== 'string'
      || isAbsolute(record.path) || !record.path || record.path.split(/[\\/]/).includes('..')
      || !digest.test(record.sha256) || !Number.isSafeInteger(record.size_bytes)
      || record.size_bytes < 0) {
      throw new Error('invalid registered artifact');
    }
    const path = resolve(root, record.path);
    if (!path.startsWith(root + sep)) throw new Error('artifact escapes registered root');
    records.set(record.id, Object.freeze({ ...record, path }));
  }
  return {
    has: id => records.has(id),
    async snapshot(ids, signal) {
      if (new Set(ids).size !== ids.length) throw new Error('duplicate artifact ID');
      let total = 0;
      for (const id of ids) {
        const record = records.get(id);
        if (!record) throw new Error('artifact ID is not registered');
        if (record.size_bytes > config.limits.maxInputBytes - total) throw new Error('combined input exceeds the byte limit');
        total += record.size_bytes;
      }
      if (total > config.limits.maxInputBytes) throw new Error('combined input exceeds the byte limit');
      signal?.throwIfAborted();
      const directory = await mkdtemp(join(scratch, 'mcp-input-'));
      const files = new Map(), references = [];
      try {
        for (const [index, id] of ids.entries()) {
          const record = records.get(id);
          let current = root;
          for (const part of relative(root, record.path).split(sep)) {
            current = join(current, part);
            if ((await lstat(current)).isSymbolicLink()) throw new Error('artifact path contains a symlink');
          }
          if (await realpath(record.path) !== record.path) throw new Error('artifact path is not canonical');
          const source = await open(record.path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
          const destination = join(directory, String(index) + '.json');
          try {
            const before = await source.stat({ bigint: true });
            if (!before.isFile() || (before.mode & 0o222n) || before.size !== BigInt(record.size_bytes)) {
              throw new Error('registered artifact is not an immutable regular file of the declared size');
            }
            const target = await open(destination, 'wx', 0o600);
            try {
              const buffer = Buffer.alloc(65536);
              let position = 0;
              while (position <= record.size_bytes) {
                signal?.throwIfAborted();
                const { bytesRead } = await source.read(buffer, 0, Math.min(buffer.length, record.size_bytes - position + 1), position);
                if (!bytesRead) break;
                position += bytesRead;
                if (position > record.size_bytes) throw new Error('artifact grew during capture');
                await target.writeFile(buffer.subarray(0, bytesRead));
              }
              if (position !== record.size_bytes || !unchanged(before, await source.stat({ bigint: true }))
                || !unchanged(before, await lstat(record.path, { bigint: true }))) {
                throw new Error('artifact changed during capture');
              }
            } finally { await target.close(); }
          } finally { await source.close(); }
          await chmod(destination, 0o444);
          const captured = await referenceFile(destination, { maxBytes: config.limits.maxInputBytes });
          if (captured.sha256 !== record.sha256 || captured.size_bytes !== record.size_bytes) {
            throw new Error('artifact digest differs from the registered identity');
          }
          files.set(id, destination);
          references.push({ id, sha256: captured.sha256, size_bytes: captured.size_bytes });
        }
        return { files, references, close: () => rm(directory, { recursive: true, force: true }) };
      } catch (error) {
        await rm(directory, { recursive: true, force: true });
        throw error;
      }
    },
  };
}
