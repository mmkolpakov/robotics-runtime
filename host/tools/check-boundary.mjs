import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';

const forbidden = /(?:^|[/@_-])(ros(?:2)?|rclpy|rclnodejs|gazebo|gz[-_]|isaac(?:sim)?|webots)(?:[/@_-]|$)/i;
// Conservative source gate: all module specifiers must be literal and inspectable.
// Provider selection belongs to upstream Loader, not computed imports in common host.
const moduleReference = /\b(?:import|export)\s+(?:type\s+)?(?:[^;]*?\bfrom\s+)?(['"])([^'"]+)\1|\b(?:import|require)\s*\(\s*(['"])([^'"]+)\3/g;
async function check(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) { await check(path); continue; }
    if (!path.endsWith('.ts')) continue;
    const source = await readFile(path, 'utf8');
    if (/\b(?:import|require)\s*\(\s*[^'"\s]/.test(source)) {
      throw new Error(`computed module reference in common host: ${path}`);
    }
    for (const match of source.matchAll(moduleReference)) {
      const specifier = match[2] ?? match[4];
      if (forbidden.test(specifier)) throw new Error(`simulator SDK import in common host: ${path}: ${specifier}`);
    }
  }
}
await check('src');
console.log('common host dependency boundary passed');
