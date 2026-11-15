import type { AnalogResult } from './contract';

/**
 * The result type the UI works with. `notes` is now part of the generated contract
 * (added in M4), so this is a plain alias kept for the components that import it.
 */
export type AnalogResultView = AnalogResult;
