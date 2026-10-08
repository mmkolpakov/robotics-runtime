#!/usr/bin/env node
import { serveStdio, StdioServerTransport } from '@modelcontextprotocol/server/stdio';
import { createOfflineAdapter } from '../src/server.mjs';
import { readBootstrap } from '../src/bootstrap.mjs';

async function main() {
  if (process.argv.length !== 4 || process.argv[2] !== '--config') throw new Error('usage: robotics-runtime-mcp --config OPERATOR_BOOTSTRAP.json');
  const config = await readBootstrap(process.argv[3]);
  const adapter = await createOfflineAdapter(config);
  const transport = new StdioServerTransport(process.stdin, process.stdout, { maxBufferSize: 262144 });
  const connection = serveStdio(() => adapter.serverFactory(), { transport, onerror: error => console.error(error.message) });
  let closing;
  const close = () => closing ??= (async () => { await adapter.close(); await connection.close(); })().catch(error => {
    console.error(error.message); process.exitCode = 1;
  });
  process.stdin.once('end', close);
  process.on('SIGINT', close);
  process.on('SIGTERM', close);
}
main().catch(error => { console.error(error.message); process.exitCode = 64; });
