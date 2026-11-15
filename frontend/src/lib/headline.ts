import type { Analog } from '../types/contract';
import type { AnalogResultView } from '../types/extensions';
import { matchScore } from './matchQuality';

export const NOVEL_CLIMATE_WARNING =
  "No place today has a close match to this field's future climate. Treat these suggestions with extra caution.";

export type Headline =
  | { kind: 'novel'; text: string }
  | { kind: 'best'; text: string; best: Analog }
  | { kind: 'empty'; text: string };

export function bestAnalog(result: AnalogResultView): Analog | undefined {
  return [...result.analogs].sort((a, b) => a.rank - b.rank)[0];
}

export function agreementText(a: Pick<Analog, 'models_agree' | 'models_total'>): string {
  return `${a.models_agree} of ${a.models_total} climate models agree`;
}

const MATCH_RATINGS: Record<Analog['match_quality'], string> = {
  strong: 'Strong!', good: 'Good!', weak: 'Weak match', none: 'No close match',
};

export function getHeadline(result: AnalogResultView): Headline {
  if (result.novel_climate) return { kind: 'novel', text: NOVEL_CLIMATE_WARNING };
  const best = bestAnalog(result);
  if (!best) return { kind: 'empty', text: 'No matching places were found for this field.' };
  return {
    kind: 'best',
    best,
    text: `Best match ${matchScore(best.sigma)} out of 100 (${MATCH_RATINGS[best.match_quality]})`,
  };
}
