import raw from '../fixtures/fake_results.json';
import type { AnalogResultView } from '../types/extensions';
import { isAnalogResult } from './validate';

export type DemoCaseId = 'fake-colfax' | 'fake-lind';

export const DEMO_CASES: { id: DemoCaseId; label: string }[] = [
  { id: 'fake-colfax', label: 'Normal case (Colfax)' },
  { id: 'fake-lind', label: 'Novel-climate case (Lind)' },
];

export function parseFixtures(data: unknown): AnalogResultView[] {
  if (!Array.isArray(data) || !data.every(isAnalogResult)) {
    throw new Error('Bundled demo data does not match the contract.');
  }
  return data;
}

const FIXTURES = parseFixtures(raw);

export function getDemoResult(id: DemoCaseId): AnalogResultView {
  const found = FIXTURES.find((r) => r.field_id === id);
  if (!found) throw new Error(`Demo case ${id} is missing from the bundled data.`);
  return found;
}
