import type { Scenario } from '../types/contract';

export const SCENARIO_LABELS: Record<Scenario, string> = {
  ssp245: 'Moderate emissions (SSP2-4.5)',
  ssp585: 'High emissions (SSP5-8.5)',
};

export const SCENARIOS: Scenario[] = ['ssp245', 'ssp585'];
export const DEFAULT_SCENARIO: Scenario = 'ssp245';
