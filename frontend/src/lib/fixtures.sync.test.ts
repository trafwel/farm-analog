import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

// The frontend bundles a copy of the backend's fixture so the demo works without the API.
// This fails if the copy drifts from the repo's fixtures/fake_results.json.
// Fix: cp ../fixtures/fake_results.json src/fixtures/fake_results.json
describe('bundled demo fixture', () => {
  it('matches the backend fixture exactly', () => {
    const read = (rel: string) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), 'utf8');
    expect(read('../fixtures/fake_results.json')).toBe(read('../../../fixtures/fake_results.json'));
  });
});
