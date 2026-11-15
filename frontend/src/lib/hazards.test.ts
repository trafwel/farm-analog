import { doyToDate, formatMonths, hazardRows } from './hazards';

describe('hazard helpers', () => {
  it('turns day of year into a date', () => {
    expect(doyToDate(1)).toBe('Jan 1');
    expect(doyToDate(127.45)).toBe('May 7');
    expect(doyToDate(277.2)).toBe('Oct 4');
    expect(doyToDate(365)).toBe('Dec 31');
  });

  it('groups months into ranges', () => {
    expect(formatMonths([1, 2, 3, 8, 9, 10, 11, 12])).toBe('Jan–Mar, Aug–Dec');
    expect(formatMonths([9, 10])).toBe('Sep–Oct');
    expect(formatMonths([4, 8, 9])).toBe('Apr, Aug–Sep');
    expect(formatMonths([])).toBe('none');
    expect(formatMonths(null)).toBe('none');
  });

  it('compares farm and place, skipping rows with no data', () => {
    const rows = hazardRows(
      { heat_days: 18.15, frost_free_days: 149.75, last_spring_frost_doy: 127.45, bare_months: [8, 9], missing_sources: [] },
      { heat_days: 27.75, frost_free_days: 186.3, last_spring_frost_doy: 108.15, bare_months: [4], missing_sources: [] },
    );
    const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
    expect(byId.heat).toMatchObject({ farm: '18 days', place: '28 days', change: '+10 days' });
    expect(byId.ffd!.change).toBe('+36 days');
    expect(byId.spring).toMatchObject({ farm: 'May 7', place: 'Apr 18', change: '19 days earlier' });
    expect(byId.bare).toMatchObject({ farm: 'Aug–Sep', place: 'Apr' });
    expect(byId.rain).toBeUndefined();
    expect(hazardRows(null, null)).toEqual([]);
  });
});

describe('chart gridlines', () => {
  it('cover the whole data range', async () => {
    const { niceTicks } = await import('../components/ClimateChart');
    expect(niceTicks(-1.2, 21.1)).toEqual([-5, 0, 5, 10, 15, 20, 25]);
    expect(niceTicks(0, 80)).toEqual([0, 20, 40, 60, 80]);
    const t = niceTicks(0, 33);
    expect(t[0]).toBe(0);
    expect(t[t.length - 1]).toBeGreaterThanOrEqual(33);
  });
});
