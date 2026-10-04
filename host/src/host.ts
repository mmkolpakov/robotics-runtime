import { Context } from 'cordis';
import Loader from '@cordisjs/plugin-loader';
import ConsoleExporter from '@cordisjs/plugin-logger-console';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

export interface HostOptions {
  baseDirectory: string;
  console?: boolean;
}

/** Creates the upstream loader context. Profiles are admitted separately. */
export async function createHost(options: HostOptions): Promise<Context> {
  const ctx = new Context();
  ctx.baseUrl = pathToFileURL(resolve(options.baseDirectory)).href + '/';
  if (options.console) await ctx.plugin(ConsoleExporter, { colors: false });
  await ctx.plugin(Loader, { baseUrl: ctx.baseUrl });
  return ctx;
}
