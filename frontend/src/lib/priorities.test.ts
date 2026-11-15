import type { RotationStrategy, RotationTraits } from '../types/contract';
import { bestFit, PRIORITIES, priorityFit, sortByPriorities } from './priorities';

const traits = (t: Partial<RotationTraits>): RotationTraits => ({
  years: 3, n_fixing: 0, high_residue: 0, low_cover: 0, fallow: 0, low_water: 0, high_water: 0, break_crop: 0, ...t,
});

const rot = (name: string, t: Partial<RotationTraits> | null, extra: Partial<RotationStrategy> = {}): RotationStrategy => ({
  name, crops: ['Winter wheat'], analog_share: 0.1, analogs_using: 1, analogs_checked: 5, why: '', evidence: [],
  benefits: [], risks: [], gaps: [], traits: t ? traits(t) : null, ...extra,
});

describe('farmer priorities', () => {
  const current = rot('Winter wheat → Barley → Pulses', { n_fixing: 0.333, break_crop: 0.333 }, { current: true });
  const fallow = rot('Winter wheat → Fallow', { years: 2, fallow: 0.5, low_cover: 0.5, low_water: 0.5, high_residue: 0.5 });
  const pulses = rot('Winter wheat → Spring wheat → Pulses', { n_fixing: 0.333, break_crop: 0.333, low_water: 0.333 });
  const all = [current, fallow, pulses];

  it('keeps the original order with no priorities', () => {
    expect(sortByPriorities(all, [])).toEqual(all);
  });

  it('keeps the current rotation first and sorts the rest by fit', () => {
    expect(sortByPriorities(all, ['nitrogen']).map((r) => r.name)).toEqual([current.name, pulses.name, fallow.name]);
    expect(sortByPriorities(all, ['water']).map((r) => r.name)).toEqual([current.name, fallow.name, pulses.name]);
  });

  it('averages several priorities and explains each in years', () => {
    const fit = priorityFit(pulses, ['nitrogen', 'erosion'])!;
    expect(fit.score).toBeCloseTo((0.333 + 1) / 2);
    expect(fit.reasons).toEqual([
      { label: 'Cut erosion', text: 'crop residue covers the soil every year' },
      { label: 'Add nitrogen', text: 'nitrogen-fixing crop in 1 of 3 years' },
    ]);
    expect(priorityFit(fallow, ['erosion'])!.reasons[0]!.text).toBe('good residue cover in 1 of 2 years');
  });

  it('says "main crops" for a flexible mix', () => {
    const mix = rot('Flexible mix', { n_fixing: 0.333 }, { flexible: true });
    expect(priorityFit(mix, ['nitrogen'])!.reasons[0]!.text).toBe('nitrogen-fixing crop in 1 of its 3 main crops');
  });

  it('gives no fit without traits or priorities, and sorts those last', () => {
    const old = rot('Saved before M19', null);
    expect(priorityFit(old, ['water'])).toBeNull();
    expect(priorityFit(pulses, [])).toBeNull();
    expect(sortByPriorities([old, pulses], ['nitrogen']).map((r) => r.name)).toEqual([pulses.name, old.name]);
  });

  it('marks the best fit only when it beats another option', () => {
    expect([...bestFit(all, ['nitrogen'])].sort()).toEqual([pulses.name, current.name].sort());
    expect([...bestFit(all, ['water'])]).toEqual([fallow.name]);
    expect(bestFit([fallow, rot('Same', { years: 2, fallow: 0.5, low_cover: 0.5, low_water: 0.5, high_residue: 0.5 })], ['water']).size).toBe(0);
    expect(bestFit(all, []).size).toBe(0);
  });

  it('keeps every score between 0 and 1', () => {
    const extremes = [traits({}), traits({ n_fixing: 1, high_residue: 1, low_water: 1, break_crop: 1 }),
      traits({ low_cover: 1, high_water: 1 })];
    for (const p of PRIORITIES) for (const t of extremes) {
      expect(p.score(t)).toBeGreaterThanOrEqual(0);
      expect(p.score(t)).toBeLessThanOrEqual(1);
    }
  });
});
