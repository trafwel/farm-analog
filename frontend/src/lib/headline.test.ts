import fixtureJson from '../fixtures/fake_results.json';
import { parseFixtures, getDemoResult } from './fixtures';
import { getHeadline, NOVEL_CLIMATE_WARNING } from './headline';

describe('bundled fixture and headline logic', () => {
  it('parses both fixture cases', () => {
    const all = parseFixtures(fixtureJson);
    expect(all.map((r) => r.field_id)).toEqual(['fake-colfax', 'fake-lind']);
    expect(all.every((r) => r.source === 'fixture')).toBe(true);
    expect(all.every((r) => r.baseline_years.length === 2)).toBe(true);
  });

  it('normal case gives a best-match headline', () => {
    const h = getHeadline(getDemoResult('fake-colfax'));
    expect(h.kind).toBe('best');
    expect(h.text).toBe('Best match: rank 1, strong match (score 92 out of 100).');
  });

  it('novel-climate case gives the warning instead', () => {
    const r = getDemoResult('fake-lind');
    expect(r.novel_climate).toBe(true);
    const h = getHeadline(r);
    expect(h.kind).toBe('novel');
    expect(h.text).toBe(NOVEL_CLIMATE_WARNING);
  });

  it('rejects data that does not match the contract', () => {
    expect(() => parseFixtures([{ source: 'fixture' }])).toThrow();
  });
});
