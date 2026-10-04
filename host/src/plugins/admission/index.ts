import { Service } from 'cordis';
import type { Context } from 'cordis';
import { readFile, lstat, realpath } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { lifecycleDeadline } from '../application-lifecycle/index.js';

export interface ImmutableFile { path: string; sha256: string; }
export interface RequiredBinding { entryId: string; service: string; }
export interface TrustedProfile {
  id: string; profilePath: string; files: readonly ImmutableFile[];
  requiredBindings: readonly RequiredBinding[]; isolatedServices: readonly string[];
  deadlineMs?: number;
}
export interface AdmittedProfile extends TrustedProfile { readonly profileSha256: string; }
function freezeClosure<T>(value: T): T {
  if (value && typeof value === 'object') { for (const child of Object.values(value)) freezeClosure(child); Object.freeze(value); }
  return value;
}
export interface AdmissionConfig { profiles: readonly TrustedProfile[]; }
declare module 'cordis' { interface Context { admission: Admission; } }

/** The trusted bootstrap supplies the full immutable module closure; operator input is only its ID. */
export class Admission extends Service {
  private readonly profiles = new Map<string, TrustedProfile>();
  private readonly issued = new WeakSet<object>();
  constructor(ctx: Context, config: AdmissionConfig) {
    super(ctx, 'admission');
    for (const input of config.profiles) {
      if (!input.id || this.profiles.has(input.id)) throw new Error('trusted profile IDs must be unique and nonempty');
      const profile = freezeClosure(structuredClone(input));
      
      this.profiles.set(profile.id, Object.freeze(profile));
    }
  }
  async admit(id: string): Promise<AdmittedProfile> {
    const profile = this.profiles.get(id);
    if (!profile) throw new Error(`profile is not trusted: ${id}`);
    const deadlineMs = lifecycleDeadline(profile.deadlineMs);
    const profilePath = resolve(profile.profilePath);
    let profileSha256: string | undefined;
    const seen = new Set<string>();
    if (!profile.files.length) throw new Error('immutable closure must be nonempty');
    if (!profile.requiredBindings.length) throw new Error('profile has no required backend binding');
    for (const file of profile.files) {
      const path = resolve(file.path);
      if (seen.has(path)) throw new Error(`duplicate immutable file: ${path}`);
      seen.add(path);
      if (!/^[a-f0-9]{64}$/.test(file.sha256)) throw new Error(`invalid pinned digest: ${path}`);
      const stat = await lstat(path);
      if (!stat.isFile() || (await realpath(path)) !== path || (stat.mode & 0o222) !== 0) {
        throw new Error(`profile closure must contain immutable regular files: ${path}`);
      }
      const digest = createHash('sha256').update(await readFile(path)).digest('hex');
      if (digest !== file.sha256) throw new Error(`immutable file digest mismatch: ${path}`);
      if (path === profilePath) profileSha256 = digest;
    }
    if (!profileSha256) throw new Error('the Include profile must be in the pinned closure');
    const result: AdmittedProfile = Object.freeze({ ...profile, profilePath, profileSha256, deadlineMs });
    this.issued.add(result);
    return result;
  }
  assertIssued(profile: AdmittedProfile): void {
    if (!this.issued.has(profile)) throw new Error('run profile was not admitted by this host');
  }
}
export default Admission;
