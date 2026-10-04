import { test } from 'node:test';
import assert from 'node:assert/strict';
import { promisify } from 'node:util';
import { execFile } from 'node:child_process';
test('compiled ESM exposes the native disposal predicate to JavaScript consumers', async () => {
  const script = `import {Context,isDisposed} from './dist/src/index.js'; const ctx = new Context(); const fiber = ctx.plugin(()=>{}); await fiber.await(); const before = isDisposed(fiber); await fiber.dispose(); const after = isDisposed(fiber); if(before || !after) throw new Error('native disposal predicate mismatch'); console.log(JSON.stringify({before,after}));`;
  const output = await promisify(execFile)(process.execPath, ['--input-type=module', '-e', script], { cwd: process.cwd(), timeout: 5000 });
  assert.deepEqual(JSON.parse(output.stdout), { before: false, after: true });
});
