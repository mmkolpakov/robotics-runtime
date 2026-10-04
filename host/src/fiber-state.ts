import { FiberState } from 'cordis';
import type { Fiber } from 'cordis';
/** Native Cordis predicate, usable by compiled JavaScript consumers. */
export function isDisposed(fiber: Pick<Fiber, 'state'>): boolean { return fiber.state === FiberState.DISPOSED; }
