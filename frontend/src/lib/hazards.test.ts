import { doyToDate, driestMonth, formatMonths, hazardRows, soilWaterPct } from './hazards';

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

  it('ensures frost-free days change equals spring shift plus fall shift', () => {
    // e.g. Colfax: spring 18 days earlier, fall 17 days later -> ffd change must be +35 days
    const rows = hazardRows(
      { frost_free_days: 147.2, last_spring_frost_doy: 126.0, first_fall_frost_doy: 279.0 },
      { frost_free_days: 183.0, last_spring_frost_doy: 108.0, first_fall_frost_doy: 296.0 },
    );
    const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
    expect(byId.spring.change).toBe('18 days earlier');
    expect(byId.fall.change).toBe('17 days later');
    expect(byId.ffd.change).toBe('+35 days');
  });
});

describe('soil water (SMAP)', () => {
  const farm = [0.287, 0.319, 0.333, 0.326, 0.295, 0.257, 0.201, 0.17, 0.166, 0.187, 0.228, 0.254];
  const place = [0.3, 0.329, 0.339, 0.328, 0.294, 0.256, 0.205, 0.177, 0.172, 0.193, 0.236, 0.263];

  it('finds the driest month, skipping missing ones', () => {
    expect(driestMonth(farm)).toEqual({ month: 9, value: 0.166 });
    expect(driestMonth([null, 0.3, null, 0.2, ...Array(8).fill(null)])).toEqual({ month: 4, value: 0.2 });
    expect(driestMonth(Array(12).fill(null))).toBeNull();
    expect(driestMonth(undefined)).toBeNull();
  });

  it('shows percent by volume and the change in points', () => {
    expect(soilWaterPct(0.166)).toBe('16.6%');
    const row = hazardRows({ soil_moisture_monthly: farm, missing_sources: [] },
      { soil_moisture_monthly: place, missing_sources: [] }).find((r) => r.id === 'soil');
    expect(row).toMatchObject({ farm: '16.6% (Sep)', place: '17.2% (Sep)', change: '+0.6 points' });
  });

  it('keeps the row when only one side has soil water', () => {
    const row = hazardRows({ soil_moisture_monthly: farm, missing_sources: [] }, { missing_sources: ['smap'] })
      .find((r) => r.id === 'soil');
    expect(row).toMatchObject({ farm: '16.6% (Sep)', place: '—', change: '—' });
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
