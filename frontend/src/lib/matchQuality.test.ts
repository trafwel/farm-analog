import { MATCH_QUALITY_ORDER, MATCH_QUALITY_STYLES, matchQualityStyle } from './matchQuality';

describe('match quality mapping', () => {
  it.each([
    ['strong', '#08306b', 'Strong match'],
    ['good', '#2171b5', 'Good match'],
    ['weak', '#6baed6', 'Weak match'],
    ['none', '#969696', 'No real match'],
  ] as const)('%s -> %s, %s', (q, color, label) => {
    expect(matchQualityStyle(q).color).toBe(color);
    expect(matchQualityStyle(q).label).toBe(label);
  });

  it('covers every quality exactly once, best first', () => {
    expect(MATCH_QUALITY_ORDER).toEqual(['strong', 'good', 'weak', 'none']);
    expect(Object.keys(MATCH_QUALITY_STYLES).sort()).toEqual([...MATCH_QUALITY_ORDER].sort());
  });
});
