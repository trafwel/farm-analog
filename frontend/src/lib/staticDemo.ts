/**
 * Static demo mode (VITE_STATIC=1): the app runs with no server, for the hosted demo.
 *
 * The 10 saved live results (5 test fields × 2 scenarios, computed with Earth Engine by
 * `python -m farm_analog.saved`) are bundled from data/samples/. A field within
 * SAVED_RESULT_RADIUS_KM of a test field gets that field's saved result, with a note saying
 * so: the same rule as the backend's offline mode (src/farm_analog/saved.py).
 */
import type { AnalogRequest, AnalogResult } from '../types/contract';
import type { AnalogResultView } from '../types/extensions';
import { ApiError, type BillSummary } from './api';
import type { LonLat } from './request';

export const IS_STATIC = import.meta.env.VITE_STATIC === '1';
export const SAVED_RESULT_RADIUS_KM = 8;

interface SavedIndex {
  computed: string;
  fields: Record<string, { label: string; lat: number; lon: number }>;
  scenarios: string[];
}

const SAVED = import.meta.glob<AnalogResult>('../../../data/samples/live_*_ssp*.json', {
  eager: true,
  import: 'default',
});
const INDEX = Object.values(
  import.meta.glob<SavedIndex>('../../../data/samples/live_results.json', { eager: true, import: 'default' }),
)[0];

/** Bill's summary of each saved result, written ahead of time with the same number check as
 * POST /bill/summary (`python -m farm_analog.saved --summaries`, M18). */
const SUMMARIES = import.meta.glob<BillSummary>('../../../data/samples/summaries/live_*_ssp*.json', {
  eager: true,
  import: 'default',
});

export interface TestField {
  id: string;
  label: string;
  lat: number;
  lon: number;
}

export const TEST_FIELDS: TestField[] = INDEX
  ? Object.entries(INDEX.fields).map(([id, f]) => ({ id, ...f }))
  : [];

export const COMPUTED_ON: string = INDEX?.computed ?? '';

function savedResult(id: string, scenario: string): AnalogResult | undefined {
  const key = Object.keys(SAVED).find((k) => k.endsWith(`/live_${id}_${scenario}.json`));
  return key ? SAVED[key] : undefined;
}

/** Great-circle distance in km. */
export function distanceKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const r = Math.PI / 180;
  const h =
    Math.sin(((lat2 - lat1) * r) / 2) ** 2 +
    Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(((lon2 - lon1) * r) / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

/** Center of a small field: the mean of its distinct corners (fine at field scale). */
export function fieldCenter(ring: LonLat[]): { lat: number; lon: number } {
  const pts = ring.length > 1 && ring[0]![0] === ring[ring.length - 1]![0] && ring[0]![1] === ring[ring.length - 1]![1]
    ? ring.slice(0, -1)
    : ring;
  const lon = pts.reduce((s, p) => s + p[0], 0) / pts.length;
  const lat = pts.reduce((s, p) => s + p[1], 0) / pts.length;
  return { lat, lon };
}

/** A ~400 m square around a test field, as the backend analyzed it. */
export function testFieldRing(f: TestField, half = 0.0025): LonLat[] {
  return [
    [f.lon - half, f.lat - half],
    [f.lon + half, f.lat - half],
    [f.lon + half, f.lat + half],
    [f.lon - half, f.lat + half],
  ];
}

export const OUTSIDE_MESSAGE = 'This online demo has saved results for 5 Palouse test fields only.';

/** The static stand-in for POST /analogs. */
export function analyzeStatic(body: AnalogRequest): AnalogResultView {
  const ring = body.field.coordinates[0] as LonLat[];
  const c = fieldCenter(ring);
  const nearest = TEST_FIELDS.map((f) => ({ f, km: distanceKm(c.lat, c.lon, f.lat, f.lon) })).sort(
    (a, b) => a.km - b.km,
  )[0];
  const saved = nearest && nearest.km <= SAVED_RESULT_RADIUS_KM ? savedResult(nearest.f.id, body.scenario ?? "ssp245") : undefined;
  if (!nearest || !saved) {
    throw new ApiError(
      'http',
      OUTSIDE_MESSAGE,
      [
        `Draw your field within ${SAVED_RESULT_RADIUS_KM} km of one of them (green squares on the map), or pick one under “Try a test field”.`,
        'The full app analyzes any US field live with Google Earth Engine; see the README to run it.',
      ],
      400,
    );
  }
  const note =
    `Saved live result for the ${nearest.f.label} test field (${nearest.km.toFixed(1)} km from your field’s ` +
    `center), computed with Earth Engine on ${COMPUTED_ON}. Your own field’s climate may differ slightly.`;
  return {
    ...saved,
    field_id: `static-${nearest.f.id}`,
    analogs: saved.analogs.slice(0, body.top_n ?? saved.analogs.length),
    notes: [note, ...(saved.notes ?? [])],
  };
}

/** The saved summary for a static result (field_id "static-<test field>"), or null. */
export function savedSummary(fieldId: string, scenario: string): BillSummary | null {
  const id = fieldId.startsWith('static-') ? fieldId.slice('static-'.length) : '';
  const key = Object.keys(SUMMARIES).find((k) => k.endsWith(`/live_${id}_${scenario}.json`));
  const s = key ? SUMMARIES[key] : undefined;
  if (!id || !s || typeof s.text !== 'string' || (s.source !== 'gemini' && s.source !== 'template')) return null;
  return { text: s.text, source: s.source, notices: Array.isArray(s.notices) ? s.notices : [], model: s.model ?? null, generated: s.generated };
}
