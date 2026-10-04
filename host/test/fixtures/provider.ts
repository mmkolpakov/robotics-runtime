import type { Context } from 'cordis';
export default function fixture(ctx: Context, config: { marker: string; announce?: boolean }): void {
  ctx.provide('hostFixture', { marker: config.marker });
  ctx.logger.info('native profile loaded %s', config.marker);
  if (config.announce) process.stdout.write(`native profile loaded ${config.marker}\n`);
}
