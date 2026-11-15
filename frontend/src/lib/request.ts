import type { AnalogRequest, Scenario } from '../types/contract';

/** A position in GeoJSON order: [longitude, latitude]. */
export type LonLat = [number, number];
/** A map vertex as Leaflet gives it. */
export interface LatLngLike {
  lat: number;
  lng: number;
}

export const DEFAULT_TOP_N = 20;

/** Convert Leaflet lat/lng vertices to GeoJSON [lon, lat] positions. */
export function latLngsToLonLat(points: LatLngLike[]): LonLat[] {
  return points.map((p) => [p.lng, p.lat]);
}

/** Return a copy of the ring with the first point repeated at the end if it is not already. */
export function closeRing(ring: LonLat[]): LonLat[] {
  if (ring.length === 0) return [];
  const first = ring[0]!;
  const last = ring[ring.length - 1]!;
  const closed = first[0] === last[0] && first[1] === last[1];
  const out = ring.map((p) => [p[0], p[1]] as LonLat);
  if (!closed) out.push([first[0], first[1]]);
  return out;
}

function ccw(p1: LonLat, p2: LonLat, p3: LonLat): number {
  return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0]);
}

function segmentsIntersect(a: LonLat, b: LonLat, c: LonLat, d: LonLat): boolean {
  const d1 = ccw(c, d, a);
  const d2 = ccw(c, d, b);
  const d3 = ccw(a, b, c);
  const d4 = ccw(a, b, d);

  if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) &&
      ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) {
    return true;
  }
  return false;
}

/** Check if polygon edges cross each other (e.g. figure-eight / bowtie shape). */
export function isSelfIntersecting(ring: LonLat[]): boolean {
  const closed = closeRing(ring);
  const n = closed.length - 1;
  if (n < 4) return false;
  for (let i = 0; i < n; i++) {
    const a = closed[i]!;
    const b = closed[i + 1]!;
    for (let j = i + 1; j < n; j++) {
      if (Math.abs(i - j) <= 1 || (i === 0 && j === n - 1)) continue;
      const c = closed[j]!;
      const d = closed[j + 1]!;
      if (segmentsIntersect(a, b, c, d)) return true;
    }
  }
  return false;
}

/** Approximate polygon area in km² (Shoelace formula). */
export function polygonAreaKm2(ring: LonLat[]): number {
  const closed = closeRing(ring);
  if (closed.length < 4) return 0;
  let area = 0;
  for (let i = 0; i < closed.length - 1; i++) {
    const [x1, y1] = closed[i]!;
    const [x2, y2] = closed[i + 1]!;
    area += x1 * y2 - x2 * y1;
  }
  const degArea = Math.abs(area) / 2;
  // km per degree: ~111.32 north-south; east-west shrinks with the cosine of the latitude.
  const meanLat = closed.slice(0, -1).reduce((s, p) => s + p[1], 0) / (closed.length - 1);
  return degArea * 111.32 * 111.32 * Math.cos((meanLat * Math.PI) / 180);
}

/** Maximum field size in km² (50 km² ~ 12,355 acres, matching backend config). */
export const MAX_FIELD_AREA_KM2 = 50.0;

export function validatePolygon(ring: LonLat[]): string | null {
  if (distinctPointCount(ring) < 3) {
    return 'A field needs at least 3 distinct corners.';
  }
  if (isSelfIntersecting(ring)) {
    return 'Self-intersecting polygon (bowtie) is not a valid field. Please draw a simple shape.';
  }
  const area = polygonAreaKm2(ring);
  if (area < 0.0005) {
    return 'Field area is too small. Please draw a larger field.';
  }
  if (area > MAX_FIELD_AREA_KM2) {
    return `Field area (${area.toFixed(1)} km²) exceeds the maximum limit of ${MAX_FIELD_AREA_KM2} km² (~12,000 acres). Please draw a single field.`;
  }
  return null;
}

/**
 * Build the POST /analogs body. `ring` is the field outline in [lon, lat] order,
 * open or closed; it is closed here. Needs at least 3 distinct vertices.
 */
export function buildAnalogRequest(
  ring: LonLat[],
  scenario: Scenario,
  topN: number = DEFAULT_TOP_N,
): AnalogRequest {
  const err = validatePolygon(ring);
  if (err) {
    throw new Error(err);
  }
  const closed = closeRing(ring);
  return {
    field: { type: 'Polygon', coordinates: [closed] },
    scenario,
    top_n: topN,
  };
}

/** A small field near Colfax, WA, so the demo never depends on drawing. Open ring, [lon, lat]. */
export const EXAMPLE_FIELD: LonLat[] = [
  [-117.375, 46.872],
  [-117.345, 46.872],
  [-117.345, 46.889],
  [-117.375, 46.889],
];

/** Number of distinct corners (ignores a repeated closing point and zero-size drags). */
export function distinctPointCount(ring: LonLat[]): number {
  return new Set(ring.map(([lon, lat]) => `${lon},${lat}`)).size;
}
