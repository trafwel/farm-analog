import { buildAnalogRequest, closeRing, distinctPointCount, EXAMPLE_FIELD, latLngsToLonLat, type LonLat } from './request';

describe('request body builder', () => {
  const open: LonLat[] = [
    [-117.4, 46.8],
    [-117.3, 46.8],
    [-117.3, 46.9],
  ];

  it('closes an open ring', () => {
    const ring = closeRing(open);
    expect(ring).toHaveLength(4);
    expect(ring[3]).toEqual(ring[0]);
  });

  it('leaves an already-closed ring alone and does not mutate input', () => {
    const closed = [...open, open[0]!];
    expect(closeRing(closed)).toEqual(closed);
    expect(open).toHaveLength(3);
  });

  it('converts Leaflet lat/lng to GeoJSON [lon, lat] order', () => {
    expect(latLngsToLonLat([{ lat: 46.88, lng: -117.36 }])).toEqual([[-117.36, 46.88]]);
  });

  it('builds the POST /analogs body with scenario and top_n', () => {
    const body = buildAnalogRequest(open, 'ssp585', 20);
    expect(body).toEqual({
      field: {
        type: 'Polygon',
        coordinates: [
          [
            [-117.4, 46.8],
            [-117.3, 46.8],
            [-117.3, 46.9],
            [-117.4, 46.8],
          ],
        ],
      },
      scenario: 'ssp585',
      top_n: 20,
    });
    // Longitude first: every first value is the (negative, |x|>90) longitude.
    for (const [lon, lat] of body.field.coordinates[0]) {
      expect(lon).toBeLessThan(-100);
      expect(lat).toBeGreaterThan(40);
    }
  });

  it('defaults top_n to 20', () => {
    expect(buildAnalogRequest(EXAMPLE_FIELD, 'ssp245').top_n).toBe(20);
  });

  it('rejects a field with fewer than 3 corners', () => {
    expect(() => buildAnalogRequest(open.slice(0, 2), 'ssp245')).toThrow();
  });

  it('rejects a self-intersecting bowtie polygon', () => {
    const bowtie: LonLat[] = [
      [-117.4, 46.8],
      [-117.3, 46.9],
      [-117.3, 46.8],
      [-117.4, 46.9],
    ];
    expect(() => buildAnalogRequest(bowtie, 'ssp245')).toThrow(/self-intersecting/i);
  });

  it('example field is near Colfax, WA', () => {
    const lons = EXAMPLE_FIELD.map((p) => p[0]);
    const lats = EXAMPLE_FIELD.map((p) => p[1]);
    const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;
    expect(mean(lons)).toBeCloseTo(-117.36, 1);
    expect(mean(lats)).toBeCloseTo(46.88, 1);
  });
});

describe('distinctPointCount', () => {
  it('ignores repeated points', () => {
    expect(
      distinctPointCount([
        [1, 2],
        [3, 4],
        [1, 2],
        [3, 4],
      ]),
    ).toBe(2);
  });
});
