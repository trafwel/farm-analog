import type { MatchQuality } from '../types/contract';

export interface MatchQualityStyle {
  /** Marker fill colour (colorblind-friendly orange to green scale; gray for no match). */
  color: string;
  /** Short label, e.g. "Strong match". */
  label: string;
  /** Plain-language range on the 0–100 match score. */
  description: string;
}

export const MATCH_QUALITY_STYLES: Record<MatchQuality, MatchQualityStyle> = {
  strong: { color: '#17ab4b', label: 'Strong match', description: 'score 85–100' },
  good: { color: '#8fd317', label: 'Good match', description: 'score 70–84' },
  weak: { color: '#f5a52c', label: 'Weak match', description: 'score 50–69' },
  none: { color: '#969696', label: 'No real match', description: 'score below 50' },
};

/** Legend / display order, best first. */
export const MATCH_QUALITY_ORDER: MatchQuality[] = ['strong', 'good', 'weak', 'none'];

export function matchQualityStyle(q: MatchQuality): MatchQualityStyle {
  return MATCH_QUALITY_STYLES[q];
}

/**
 * Sigma -> score anchor points. They sit on the backend's quality thresholds
 * (config.STRONG_SIGMA = 1, GOOD_SIGMA = 2, NOVEL_SIGMA = 4), so the score bands
 * (85+, 70–84, 50–69, below 50) always agree with ``match_quality``.
 * Must match schema.match_score in the backend.
 */
export const SCORE_ANCHORS: ReadonlyArray<readonly [sigma: number, score: number]> = [
  [0, 100],
  [1, 85],
  [2, 70],
  [4, 50],
  [8, 0],
];

/** Highest score in each band. */
const BAND_MAX: Record<MatchQuality, number> = { strong: 100, good: 84, weak: 69, none: 49 };

/** Same thresholds as the backend's schema.match_quality. */
function sigmaQuality(sigma: number): MatchQuality {
  if (sigma < 1) return 'strong';
  if (sigma < 2) return 'good';
  if (sigma < 4) return 'weak';
  return 'none';
}

/**
 * Plain 0–100 match score for a sigma dissimilarity (higher = closer match).
 * Linear between the anchors, rounded down, and capped at the top of the sigma's
 * band so a sigma exactly on a threshold (e.g. 1.0, "good") never shows 85 ("strong").
 */
export function matchScore(sigma: number): number {
  if (!Number.isFinite(sigma)) return 0;
  if (sigma <= 0) return 100;
  let raw = 0;
  for (let i = 1; i < SCORE_ANCHORS.length; i++) {
    const [s0, v0] = SCORE_ANCHORS[i - 1]!;
    const [s1, v1] = SCORE_ANCHORS[i]!;
    if (sigma <= s1) {
      raw = v0 + ((sigma - s0) * (v1 - v0)) / (s1 - s0);
      break;
    }
  }
  // The epsilon keeps float noise (e.g. 96.99999 for sigma 0.2) from losing a point.
  return Math.max(0, Math.min(Math.floor(raw + 1e-9), BAND_MAX[sigmaQuality(sigma)]));
}

/** The quality band a score falls in (same thresholds as the backend's match_quality). */
export function scoreQuality(score: number): MatchQuality {
  if (score >= 85) return 'strong';
  if (score >= 70) return 'good';
  if (score >= 50) return 'weak';
  return 'none';
}
