import { constants } from 'node:fs';
import { lstat, open } from 'node:fs/promises';

const limit = 65536;
const unchanged = (a, b) => a.isFile() && b.isFile() && a.dev === b.dev && a.ino === b.ino
  && a.size === b.size && a.mtimeNs === b.mtimeNs && a.ctimeNs === b.ctimeNs;

export async function readBootstrap(path) {
  const file = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const before = await file.stat({ bigint: true });
    if (!before.isFile() || before.size > BigInt(limit)) throw new Error('bootstrap exceeds its regular-file 64 KiB bound');
    const buffer = Buffer.alloc(limit + 1);
    let position = 0;
    while (position < buffer.length) {
      const { bytesRead } = await file.read(buffer, position, buffer.length - position, position);
      if (!bytesRead) break;
      position += bytesRead;
    }
    if (position > limit || BigInt(position) !== before.size
      || !unchanged(before, await file.stat({ bigint: true }))
      || !unchanged(before, await lstat(path, { bigint: true }))) {
      throw new Error('bootstrap changed during bounded capture');
    }
    return JSON.parse(buffer.subarray(0, position).toString('utf8'));
  } finally { await file.close(); }
}
