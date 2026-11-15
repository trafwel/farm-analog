import {
  MATCH_QUALITY_ORDER,
  MATCH_QUALITY_STYLES,
  matchQualityStyle,
  matchScore,
  scoreQuality,
} from './matchQuality';

// Same table as tests/test_schema.py::test_match_score_table: the two score functions must agree.
describe('match score', () => {
  it.each([
    [0, 100], [0.2, 97], [0.3, 95], [0.999, 85], [1, 84], [1.5, 77], [2, 69],
    [3, 60], [3.99, 50], [4, 49], [6, 25], [8, 0], [12, 0],
  ])('sigma %s -> score %s', (sigma, score) => {
    expect(matchScore(sigma)).toBe(score);
  });

  it('score band always matches the backend sigma thresholds', () => {
    for (let i = 0; i <= 1000; i++) {
      const sigma = i / 100;
      const expected = sigma < 1 ? 'strong' : sigma < 2 ? 'good' : sigma < 4 ? 'weak' : 'none';
      expect(scoreQuality(matchScore(sigma))).toBe(expected);
    }
    expect(matchScore(Number.POSITIVE_INFINITY)).toBe(0);
  });
});

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
