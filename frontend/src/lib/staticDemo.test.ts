import { buildAnalogRequest } from './request';
import { analyzeStatic, distanceKm, OUTSIDE_MESSAGE, TEST_FIELDS, testFieldRing } from './staticDemo';
import { ApiError } from './api';

describe('static demo', () => {
  it('bundles the 5 test fields and both scenarios', () => {
    expect(TEST_FIELDS.map((f) => f.id).sort()).toEqual(['colfax', 'cook', 'dayton', 'lacrosse', 'lind']);
    for (const f of TEST_FIELDS) {
      for (const scenario of ['ssp245', 'ssp585'] as const) {
        const r = analyzeStatic(buildAnalogRequest(testFieldRing(f), scenario, 5));
        expect(r.scenario).toBe(scenario);
        expect(r.analogs).toHaveLength(5);
        expect(r.models).toHaveLength(8);
        expect(r.notes?.[0]).toContain(`nearby example field at ${f.label}.`);
      }
    }
  });

  it('answers a field near a test field and refuses one far away', () => {
    const colfax = TEST_FIELDS.find((f) => f.id === 'colfax')!;
    const near = testFieldRing({ ...colfax, lat: colfax.lat + 0.03 }); // ~3.3 km north
    const r = analyzeStatic(buildAnalogRequest(near, 'ssp245'));
    expect(r.field_id).toBe('static-colfax');
    expect(r.notes?.[0]).toContain('nearby example field at Colfax.');
    expect(r.rotations?.length).toBeGreaterThanOrEqual(3);
    expect(r.farm_hazards).toBeTruthy();

    const far = testFieldRing({ ...colfax, lat: 47.6, lon: -120.5 });
    try {
      analyzeStatic(buildAnalogRequest(far, 'ssp245'));
      throw new Error('expected a refusal');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).message).toBe(OUTSIDE_MESSAGE);
      expect((e as ApiError).status).toBe(400);
    }
  });

  it('measures distance', () => {
    expect(distanceKm(46.88, -117.36, 46.78, -117.09)).toBeCloseTo(23.3, 0);
  });
});

describe('saved summaries (M18)', () => {
  it('has a checked summary for every test field and scenario, matched by field id', async () => {
    const { savedSummary } = await import('./staticDemo');
    for (const f of TEST_FIELDS) {
      for (const scenario of ['ssp245', 'ssp585'] as const) {
        const r = analyzeStatic(buildAnalogRequest(testFieldRing(f), scenario));
        const s = savedSummary(r.field_id, r.scenario);
        expect(s, `${f.id} ${scenario}`).not.toBeNull();
        expect(s!.text).toContain(r.analogs[0]!.place_name!.split(',')[0]!);
        expect(s!.generated).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      }
    }
    expect(savedSummary('fake-colfax', 'ssp245')).toBeNull();
    expect(savedSummary('static-nowhere', 'ssp245')).toBeNull();
  });
});
