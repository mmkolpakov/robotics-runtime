import type { ArtifactRef } from './index.js';
import type { OwnedRun, RunCompletion } from '../run-owner/index.js';
export const HOST_EXTENSION_NAMESPACE = 'org.robotics.runtime.host';
export const HOST_EXTENSION_SCHEMA_URI = 'urn:robotics:host:composition:v1';
export interface ProviderObservation {
  id: string;
  identity: { package: string; version: string; source_sha256?: string; image_digest?: string; scene_ref?: ArtifactRef; config_ref: ArtifactRef };
  bindings: readonly { service: string; provider: string; evidence_ref: ArtifactRef }[];
  capabilities: { declared: readonly string[]; effective: readonly string[]; qualification_refs: readonly ArtifactRef[] };
  endpoints: readonly { kind: string; evidence_ref: ArtifactRef }[];
  time: readonly { authority: string; domain: string; epoch: string; native_unit: string;
    precision: { representation: 'float64' | 'integer' | 'decimal'; description: string };
    native_observation_ref: ArtifactRef; coordinates: { frame: string; units: string; axes: string } }[];
  lifecycle_refs: readonly ArtifactRef[]; cleanup_refs: readonly ArtifactRef[];
}
export function compositionObservation(
  run: OwnedRun, completion: RunCompletion, host: { package: string; version: string; node: string; package_lock_ref: ArtifactRef },
  configRef: ArtifactRef, providers: readonly ProviderObservation[],
) {
  if (completion.runId !== run.runId) throw new Error('completion belongs to another run');
  if (configRef.sha256 !== run.profile.profileSha256) throw new Error('profile identity changed');
  for (const provider of providers) {
    if (provider.capabilities.effective.some(capability => !provider.capabilities.declared.includes(capability))) {
      throw new Error('effective capability was not declared');
    }
    if (provider.capabilities.effective.length && !provider.capabilities.qualification_refs.length) {
      throw new Error('effective capability has no qualification evidence');
    }
  }
  return {
    run_id: run.runId, profile: { id: run.profile.id, sha256: run.profile.profileSha256, config_ref: configRef },
    host, providers, lifecycle: {
      status: completion.status, phases: completion.phases, evidence_refs: completion.evidenceRefs, errors: completion.errors,
      resource_outcomes: completion.resourceOutcomes.map(outcome => ({
        id: outcome.id, owner_id: outcome.ownerId, attempted: outcome.attempted, released: outcome.released, evidence_refs: outcome.evidenceRefs,
        ...(outcome.diagnostic === undefined ? {} : { diagnostic: outcome.diagnostic }),
        ...(outcome.cleanupError === undefined ? {} : { cleanup_error: outcome.cleanupError }),
      })),
    },
  };
}
