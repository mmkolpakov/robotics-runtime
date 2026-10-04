import { spawnSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const manifest = JSON.parse(await readFile('proto/source.json', 'utf8'));
for (const [name, identity] of Object.entries(manifest.files)) {
  const raw = await readFile('proto/' + name);
  if (raw.length !== identity.size_bytes || createHash('sha256').update(raw).digest('hex') !== identity.sha256) {
    throw new Error('official proto identity mismatch: ' + name);
  }
}
const result = spawnSync(process.execPath, ['node_modules/@grpc/proto-loader/build/bin/proto-loader-gen-types.js',
  '--grpcLib=@grpc/grpc-js', '--outDir=src/generated/mavsdk', '--keepCase', '--longs=String', '--enums=String',
  '--defaults', '--oneofs', '--importFileExtension=.js', '--includeDirs', 'proto', '--',
  'core/core.proto', 'telemetry/telemetry.proto', 'action/action.proto'], { stdio: 'inherit' });
if (result.status !== 0) throw new Error('official type generator failed');
