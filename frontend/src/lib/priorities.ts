import type { RotationStrategy, RotationTraits } from '../types/contract';

/**
 * Farmer priorities (M19). Each one scores a rotation from 0 to 1 using only the rotation's
 * traits, which the backend computes from a fixed crop-traits table (rotations.TRAITS), and
 * says why in plain words. Nothing here is a prediction: it's how the rotation's crops line up
 * with what the farmer cares about.
 */
export type PriorityId = 'water' | 'erosion' | 'organic' | 'nitrogen' | 'pests';

export interface Priority {
  id: PriorityId;
  label: string;
  score: (t: RotationTraits) => number;
  reason: (t: RotationTraits, flexible: boolean) => string;
}

/** "1 of 3 years", or for a flexible mix "1 of its 3 main crops". */
function count(share: number, t: RotationTraits, flexible: boolean): string {
  const n = Math.round(share * t.years);
  return flexible ? `${n} of its ${t.years} main crops` : `${n} of ${t.years} years`;
}

export const PRIORITIES: Priority[] = [
  {
    id: 'water',
    label: 'Save water',
    score: (t) => (1 + t.low_water - t.high_water) / 2,
    reason: (t, f) =>
      `low-water crop or fallow in ${count(t.low_water, t, f)}` +
      (t.high_water > 0 ? `; high-water crop in ${count(t.high_water, t, f)}` : ''),
  },
  {
    id: 'erosion',
    label: 'Cut erosion',
    score: (t) => 1 - t.low_cover,
    reason: (t, f) =>
      t.low_cover === 0 ? 'crop residue covers the soil every year' : `good residue cover in ${count(1 - t.low_cover, t, f)}`,
  },
  {
    id: 'organic',
    label: 'Build organic matter',
    score: (t) => t.high_residue,
    reason: (t, f) => `heavy residue in ${count(t.high_residue, t, f)}`,
  },
  {
    id: 'nitrogen',
    label: 'Add nitrogen',
    score: (t) => t.n_fixing,
    reason: (t, f) => (t.n_fixing === 0 ? 'no nitrogen-fixing crop' : `nitrogen-fixing crop in ${count(t.n_fixing, t, f)}`),
  },
  {
    id: 'pests',
    label: 'Break pest and disease cycles',
    score: (t) => t.break_crop,
    reason: (t, f) =>
      t.break_crop === 0 ? 'cereals and fallow only, no break crop' : `non-cereal break crop in ${count(t.break_crop, t, f)}`,
  },
];

export const NOT_SCORED =
  'Income, markets and equipment aren’t measured here, so they can’t be scored. Weigh them yourself.';

export interface PriorityFit {
  score: number;
  reasons: { label: string; text: string }[];
}

/** How a rotation fits the chosen priorities; null when it has no traits or none are chosen. */
export function priorityFit(r: RotationStrategy, chosen: PriorityId[]): PriorityFit | null {
  const t = r.traits;
  if (!t || chosen.length === 0) return null;
  const picked = PRIORITIES.filter((p) => chosen.includes(p.id));
  const score = picked.reduce((s, p) => s + p.score(t), 0) / picked.length;
  return {
    score,
    reasons: picked.map((p) => ({ label: p.label, text: p.reason(t, Boolean(r.flexible)) })),
  };
}

/**
 * The field's current rotation stays first; the others are sorted by fit to the chosen
 * priorities, ties kept in their original order (most used at the matching places first).
 */
export function sortByPriorities(rotations: RotationStrategy[], chosen: PriorityId[]): RotationStrategy[] {
  if (chosen.length === 0) return rotations;
  const current = rotations.filter((r) => r.current);
  const others = rotations
    .filter((r) => !r.current)
    .map((r, i) => ({ r, i, s: priorityFit(r, chosen)?.score ?? -1 }))
    .sort((a, b) => b.s - a.s || a.i - b.i)
    .map((x) => x.r);
  return [...current, ...others];
}

/**
 * Names of the options that fit the chosen priorities best: the highest score, but only when
 * some other option scores lower (a tie across all options singles none out). Scores are
 * compared between these options only; there is no absolute "good" score, since one pulse crop
 * in three years can be a strong nitrogen rotation for dryland wheat.
 */
export function bestFit(rotations: RotationStrategy[], chosen: PriorityId[]): Set<string> {
  const scored = rotations
    .map((r) => ({ name: r.name, s: priorityFit(r, chosen)?.score }))
    .filter((x): x is { name: string; s: number } => x.s !== undefined);
  if (scored.length < 2) return new Set();
  const top = Math.max(...scored.map((x) => x.s));
  if (scored.every((x) => Math.abs(x.s - top) < 1e-9)) return new Set();
  return new Set(scored.filter((x) => Math.abs(x.s - top) < 1e-9).map((x) => x.name));
}
