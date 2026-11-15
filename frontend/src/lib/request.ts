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

/**
 * Build the POST /analogs body. `ring` is the field outline in [lon, lat] order,
 * open or closed; it is closed here. Needs at least 3 distinct vertices.
 */
export function buildAnalogRequest(
  ring: LonLat[],
  scenario: Scenario,
  topN: number = DEFAULT_TOP_N,
): AnalogRequest {
  const closed = closeRing(ring);
  if (closed.length < 4) {
    throw new Error('A field needs at least 3 corners.');
  }
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
