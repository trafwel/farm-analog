import type { MatchQuality } from '../types/contract';

export interface MatchQualityStyle {
  /** Marker fill colour (colorblind-friendly sequential blues; gray for no match). */
  color: string;
  /** Short label, e.g. "Strong match". */
  label: string;
  /** Plain-language explanation including the sigma range. */
  description: string;
}

export const MATCH_QUALITY_STYLES: Record<MatchQuality, MatchQualityStyle> = {
  strong: { color: '#08306b', label: 'Strong match', description: 'sigma below 1' },
  good: { color: '#2171b5', label: 'Good match', description: 'sigma 1 to 2' },
  weak: { color: '#6baed6', label: 'Weak match', description: 'sigma 2 to 4' },
  none: { color: '#969696', label: 'No real match', description: 'sigma 4 or more' },
};

/** Legend / display order, best first. */
export const MATCH_QUALITY_ORDER: MatchQuality[] = ['strong', 'good', 'weak', 'none'];

export function matchQualityStyle(q: MatchQuality): MatchQualityStyle {
  return MATCH_QUALITY_STYLES[q];
}
