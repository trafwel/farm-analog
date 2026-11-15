import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import '@geoman-io/leaflet-geoman-free';
import { Circle, MapContainer, Polygon, Rectangle, TileLayer, Tooltip, useMap } from 'react-leaflet';
import type { TestField } from '../lib/staticDemo';
import { SAVED_RESULT_RADIUS_KM } from '../lib/staticDemo';
import type { Analog } from '../types/contract';
import { matchQualityStyle, matchScore } from '../lib/matchQuality';
import type { LatLngLike, LonLat } from '../lib/request';
import { distinctPointCount, latLngsToLonLat, MAX_FIELD_AREA_KM2, polygonAreaKm2 } from '../lib/request';
import { Legend } from './Legend';
import { FIELD_COLOR_SWATCH } from './swatches';

export const PALOUSE_CENTER: [number, number] = [46.85, -117.6];
export const PALOUSE_ZOOM = 8;
export const FIELD_COLOR = FIELD_COLOR_SWATCH;

const FIELD_STYLE: L.PathOptions = { color: FIELD_COLOR, fillColor: FIELD_COLOR, fillOpacity: 0.3, weight: 3 };

/** Convert a Leaflet circle to the same boundary format as other fields. */
function circleRing(circle: L.Circle): LonLat[] {
  const { lat, lng } = circle.getLatLng();
  const latitude = lat * Math.PI / 180;
  const distance = circle.getRadius() / 6371000;
  return Array.from({ length: 64 }, (_, index) => {
    const bearing = index * 2 * Math.PI / 64;
    const nextLat = Math.asin(
      Math.sin(latitude) * Math.cos(distance) + Math.cos(latitude) * Math.sin(distance) * Math.cos(bearing),
    );
    const longitudeDelta = Math.atan2(
      Math.sin(bearing) * Math.sin(distance) * Math.cos(latitude),
      Math.cos(distance) - Math.sin(latitude) * Math.sin(nextLat),
    );
    return [lng + longitudeDelta * 180 / Math.PI, nextLat * 180 / Math.PI];
  });
}

/** Stops any drawing in progress and removes Geoman's half-drawn shape and markers. Uses
 * Geoman internals (no public API for this), so every step is guarded. */
function cancelDrawing(map: L.Map) {
  map.pm.disableDraw();
  const pmDraw = (map.pm as unknown as {
    Draw?: { Polygon?: { _cleanUpMarkers?: () => void; _layer?: L.Layer | null }; Rectangle?: { _layer?: L.Layer | null } };
  })?.Draw;
  if (pmDraw?.Polygon) {
    if (typeof pmDraw.Polygon._cleanUpMarkers === 'function') pmDraw.Polygon._cleanUpMarkers();
    if (pmDraw.Polygon._layer) {
      map.removeLayer(pmDraw.Polygon._layer);
      pmDraw.Polygon._layer = null;
    }
  }
  if (pmDraw?.Rectangle?._layer) {
    map.removeLayer(pmDraw.Rectangle._layer);
    pmDraw.Rectangle._layer = null;
  }
}

/** Adds Geoman's polygon-drawing control. Every new drawing replaces the field. */
function DrawControl({ onDraw, cancelSignal }: { onDraw: (ring: LonLat[]) => void; cancelSignal?: unknown }) {
  const map = useMap();
  const onDrawRef = useRef(onDraw);
  useEffect(() => {
    onDrawRef.current = onDraw;
  }, [onDraw]);

  // Cancel drawing and clean up temporary markers when external actions happen (e.g. clear field, pick test field, search)
  useEffect(() => {
    try {
      cancelDrawing(map);
    } catch {
      // ignore
    }
  }, [map, cancelSignal]);

  // Escape key cancels drawing mode and cleans up markers
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        try {
          cancelDrawing(map);
        } catch {
          // ignore
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [map]);

  useEffect(() => {
    map.pm.setGlobalOptions({
      pathOptions: FIELD_STYLE,
      templineStyle: { color: FIELD_COLOR },
      hintlineStyle: { color: FIELD_COLOR, dashArray: '5,5' },
      continueDrawing: false,
      snappable: true,
      snapDistance: 25,
      finishOn: 'dblclick',
    });
    map.pm.addControls({
      position: 'topleft',
      drawPolygon: true,
      drawMarker: false,
      drawCircleMarker: false,
      drawPolyline: false,
      drawRectangle: true,
      drawCircle: true,
      drawText: false,
      editMode: false,
      dragMode: false,
      cutPolygon: false,
      removalMode: false,
      rotateMode: false,
      oneBlock: true,
    });

    const handleCreate = (e: { layer: L.Layer }) => {
      map.pm.disableDraw();
      const layer = e.layer;
      if (layer instanceof L.Circle) {
        if (layer.getRadius() > 0) onDrawRef.current(circleRing(layer));
      } else if (layer instanceof L.Polygon) {
        const rings = layer.getLatLngs() as LatLngLike[][];
        const outer = rings[0];
        const ring = outer ? latLngsToLonLat(outer) : [];
        if (distinctPointCount(ring) >= 3) onDrawRef.current(ring);
      }
      // The field is rendered from React state, so drop Geoman's own copy.
      map.removeLayer(layer);
    };

    map.on('pm:create', handleCreate);

    // Support drag-to-draw for Rectangle mode without panning the map
    let startLatLng: L.LatLng | null = null;
    let previewRect: L.Rectangle | null = null;
    let isDrawingRectangle = false;

    let previewCircle: L.Circle | null = null;

    const onDrawStart = (e: { shape: string; workingLayer: L.Layer }) => {
      previewCircle = e.shape === 'Circle' && e.workingLayer instanceof L.Circle ? e.workingLayer : null;
      isDrawingRectangle = e.shape === 'Rectangle';
    };

    const onDrawEnd = () => {
      isDrawingRectangle = false;
      previewCircle = null;
      if (previewRect) {
        map.removeLayer(previewRect);
        previewRect = null;
      }
      startLatLng = null;
      map.dragging.enable();
    };

    const onMouseDown = (e: L.LeafletMouseEvent) => {
      if (!isDrawingRectangle) return;
      startLatLng = e.latlng;
      map.dragging.disable();
    };

    const onMouseMove = (e: L.LeafletMouseEvent) => {
      if (previewCircle) {
        const tooLarge = polygonAreaKm2(circleRing(previewCircle)) > MAX_FIELD_AREA_KM2;
        const color = tooLarge ? '#c52e36' : FIELD_COLOR;
        previewCircle.setStyle({ color, fillColor: color });
      }
      if (!isDrawingRectangle || !startLatLng) return;
      const bounds = L.latLngBounds(startLatLng, e.latlng);
      const ring = latLngsToLonLat([
        bounds.getSouthWest(), bounds.getSouthEast(), bounds.getNorthEast(), bounds.getNorthWest(),
      ]);
      const tooLarge = polygonAreaKm2(ring) > MAX_FIELD_AREA_KM2;
      const style = tooLarge ? { ...FIELD_STYLE, color: '#c52e36', fillColor: '#c52e36' } : FIELD_STYLE;
      if (!previewRect) {
        previewRect = L.rectangle(bounds, style).addTo(map);
      } else {
        previewRect.setBounds(bounds).setStyle(style);
      }
    };

    const onMouseUp = (e: L.LeafletMouseEvent) => {
      if (!isDrawingRectangle || !startLatLng) return;
      const endLatLng = e.latlng;
      const bounds = L.latLngBounds(startLatLng, endLatLng);
      map.dragging.enable();

      const p1 = map.latLngToLayerPoint(startLatLng);
      const p2 = map.latLngToLayerPoint(endLatLng);
      const pixelDist = p1.distanceTo(p2);

      if (pixelDist > 15) {
        const sw = bounds.getSouthWest();
        const ne = bounds.getNorthEast();
        const nw = bounds.getNorthWest();
        const se = bounds.getSouthEast();
        const ring: LonLat[] = [
          [sw.lng, sw.lat],
          [se.lng, se.lat],
          [ne.lng, ne.lat],
          [nw.lng, nw.lat],
        ];
        onDrawRef.current(ring);
        map.pm.disableDraw();
      }

      if (previewRect) {
        map.removeLayer(previewRect);
        previewRect = null;
      }
      startLatLng = null;
    };

    map.on('pm:drawstart', onDrawStart);
    map.on('pm:drawend', onDrawEnd);
    map.on('mousedown', onMouseDown);
    map.on('mousemove', onMouseMove);
    map.on('mouseup', onMouseUp);

    return () => {
      map.off('pm:create', handleCreate);
      map.off('pm:drawstart', onDrawStart);
      map.off('pm:drawend', onDrawEnd);
      map.off('mousedown', onMouseDown);
      map.off('mousemove', onMouseMove);
      map.off('mouseup', onMouseUp);
      map.dragging.enable();
      if (previewRect) {
        map.removeLayer(previewRect);
      }
      map.pm.removeControls();
    };
  }, [map]);
  return null;
}

function rightPanelOverlap(map: L.Map): number {
  const container = map.getContainer();
  const panel = container.closest('.layout')?.querySelector('.panel');
  const mapRect = container.getBoundingClientRect();
  const panelRect = panel?.getBoundingClientRect();
  if (!panelRect || panelRect.top >= mapRect.bottom || panelRect.bottom <= mapRect.top) return 0;
  return Math.max(0, mapRect.right - panelRect.left);
}

function FlyToField({ field, hidden }: { field: LonLat[] | null; hidden: boolean }) {
  const map = useMap();
  useEffect(() => {
    if (!field?.length || hidden) return;
    const bounds = L.latLngBounds(field.map(([lon, lat]) => L.latLng(lat, lon)));
    const coveredWidth = rightPanelOverlap(map);
    const zoom = Math.min(13, map.getBoundsZoom(bounds, false, L.point(coveredWidth + 64, 64)));
    const center = map.unproject(map.project(bounds.getCenter(), zoom).add([coveredWidth / 2, 0]), zoom);
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      map.setView(center, zoom, { animate: false });
    } else {
      map.flyTo(center, zoom, { duration: 0.85 });
    }
  }, [field, hidden, map]);
  return null;
}

function DemoCoverage({ fields }: { fields: TestField[] }) {
  const map = useMap();
  const [drawing, setDrawing] = useState(false);
  useEffect(() => {
    const start = () => setDrawing(true);
    const end = () => setDrawing(false);
    map.on('pm:drawstart', start);
    map.on('pm:drawend', end);
    return () => {
      map.off('pm:drawstart', start);
      map.off('pm:drawend', end);
    };
  }, [map]);

  return drawing ? fields.map((preset) => (
    <Circle
      key={preset.id}
      center={[preset.lat, preset.lon]}
      radius={SAVED_RESULT_RADIUS_KM * 1000}
      interactive={false}
      pathOptions={{ color: '#865c32', weight: 1, opacity: 0.48, fillOpacity: 0.15, pmIgnore: true } as L.PathOptions}
    />
  )) : null;
}

/** Pan to the selected analog quickly. */
function FlyToSelected({ analog, focusRequest, hidden }: {
  analog: Analog | undefined;
  focusRequest: number;
  hidden: boolean;
}) {
  const map = useMap();
  const lastRequest = useRef(0);
  useEffect(() => {
    if (!analog || hidden) return;
    map.invalidateSize({ pan: false });
    const requested = focusRequest !== lastRequest.current;
    lastRequest.current = focusRequest;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (requested) map.getContainer().scrollIntoView({ block: 'nearest', behavior: reducedMotion ? 'instant' : 'smooth' });
    const zoom = Math.max(map.getZoom(), requested ? 11 : 9);
    const center = map.unproject(map.project([analog.lat, analog.lon], zoom).add([rightPanelOverlap(map) / 2, 0]), zoom);
    if (reducedMotion) map.setView(center, zoom, { animate: false });
    else map.flyTo(center, zoom, { duration: requested ? 0.65 : 0.2 });
  }, [map, analog, focusRequest, hidden]);
  return null;
}

/** Center new matches in the part of the map visible beside the results panel. */
function FitToResult({ analogs, resultKey, hidden }: { analogs: Analog[]; resultKey: string; hidden: boolean }) {
  const map = useMap();
  const lastKey = useRef('');
  useEffect(() => {
    if (hidden || !resultKey || resultKey === lastKey.current || analogs.length === 0) return;
    lastKey.current = resultKey;
    map.invalidateSize({ pan: false });
    const bounds = L.latLngBounds(matchBackdrops(analogs).flat());
    for (const { lat, lon } of analogs) {
      bounds.extend([lat - 1 / 48, lon - 1 / 48]);
      bounds.extend([lat + 1 / 48, lon + 1 / 48]);
    }
    map.fitBounds(bounds, {
      paddingTopLeft: [44, 36],
      paddingBottomRight: [rightPanelOverlap(map) + 44, 48],
      maxZoom: 10,
    });
  }, [map, analogs, resultKey, hidden]);
  return null;
}

/** Leaflet measures its container once; re-measure when the map is shown again after being hidden. */
function ResizeWhenVisible({ hidden }: { hidden: boolean }) {
  const map = useMap();
  useEffect(() => {
    if (!hidden) map.invalidateSize();
  }, [hidden, map]);
  return null;
}

export interface MapViewProps {
  field: LonLat[] | null;
  onFieldDrawn: (ring: LonLat[]) => void;
  analogs: Analog[];
  resultKey: string;
  selectedRank: number | null;
  focusRequest?: number;
  onSelect: (rank: number) => void;
  /** Static demo: the test fields that have saved results, outlined so people can find them. */
  showDemoCoverage?: boolean;
  testFields?: TestField[];
  cancelSignal?: unknown;
  /** True while the results panel is full screen (the map is hidden but kept mounted). */
  hidden?: boolean;
}

const TEST_FIELD_NAMES: Record<string, string> = {
  cook: 'Cook Farm',
  colfax: 'Colfax',
  lacrosse: 'LaCrosse',
  lind: 'Lind',
  dayton: 'Dayton',
};

function TestFieldMarkers({ testFields }: { testFields: TestField[] }) {
  const map = useMap();
  const [zoom, setZoom] = useState(map.getZoom());
  useEffect(() => {
    const onZoom = () => setZoom(map.getZoom());
    map.on('zoomend', onZoom);
    return () => {
      map.off('zoomend', onZoom);
    };
  }, [map]);

  // At minimum zoom (6-7), permanent labels pile on top of each other.
  // Below zoom 8, show on hover instead of permanent.
  const isPermanent = zoom >= 8;

  return (
    <>
      {testFields.map((t) => {
        const baseName = t.label.split(' (')[0]?.split(',')[0] ?? t.id;
        const name = TEST_FIELD_NAMES[t.id] ?? baseName;
        return (
          <Rectangle
            key={t.id}
            bounds={[
              [t.lat - 0.02, t.lon - 0.027],
              [t.lat + 0.02, t.lon + 0.027],
            ]}
            pathOptions={{ color: FIELD_COLOR, weight: 3, fillColor: FIELD_COLOR, fillOpacity: 0.25, pmIgnore: true } as L.PathOptions}
          >
            <Tooltip permanent={isPermanent} direction="top" offset={[0, -6]}>
              {name}
            </Tooltip>
          </Rectangle>
        );
      })}
    </>
  );
}

function matchBackdrops(analogs: Analog[]): [number, number][][] {
  type Point = [number, number];
  const remaining = analogs.filter((analog) => matchScore(analog.sigma) >= 50);
  const backdrops: Point[][] = [];
  while (remaining.length) {
    const group = remaining.splice(0, 1);
    for (const member of group) {
      for (let index = remaining.length - 1; index >= 0; index--) {
        const candidate = remaining[index];
        if (candidate && Math.hypot(
          (candidate.lon - member.lon) / 0.45,
          (candidate.lat - member.lat) / 0.19,
        ) <= 1) group.push(...remaining.splice(index, 1));
      }
    }
    const points = group.flatMap(({ lat, lon }) =>
      Array.from({ length: 48 }, (_, index): Point => {
        const angle = index * Math.PI / 24;
        return [lon + 0.11 * Math.cos(angle), lat + 0.075 * Math.sin(angle)];
      }),
    ).sort(([x, y], [nextX, nextY]) => x - nextX || y - nextY);
    const halfHull = (ordered: Point[]) => {
      const hull: Point[] = [];
      for (const point of ordered) {
        while (hull.length >= 2) {
          const [ax, ay] = hull[hull.length - 2]!;
          const [bx, by] = hull[hull.length - 1]!;
          if ((bx - ax) * (point[1] - ay) > (by - ay) * (point[0] - ax)) break;
          hull.pop();
        }
        hull.push(point);
      }
      return hull.slice(0, -1);
    };
    backdrops.push([...halfHull(points), ...halfHull([...points].reverse())].map(([lon, lat]) => [lat, lon]));
  }
  return backdrops;
}

export function MapView({ field, onFieldDrawn, analogs, resultKey, selectedRank, focusRequest = 0, onSelect, testFields = [], showDemoCoverage = false, cancelSignal, hidden = false }: MapViewProps) {
  // Normalize the ring to clockwise order on screen, independent of drawing direction.
  const signedArea = field?.reduce((area, [lon, lat], index) => {
    const [nextLon, nextLat] = field[(index + 1) % field.length] ?? [lon, lat];
    return area + lon * nextLat - nextLon * lat;
  }, 0) ?? 0;
  const outline = field && signedArea > 0 ? [...field].reverse() : field;
  const [outlinedRequest, setOutlinedRequest] = useState(0);
  useEffect(() => {
    if (!focusRequest) return;
    const delay = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 650;
    const show = window.setTimeout(() => setOutlinedRequest(focusRequest), delay);
    const hide = window.setTimeout(() => setOutlinedRequest(0), delay + 1000);
    return () => {
      window.clearTimeout(show);
      window.clearTimeout(hide);
    };
  }, [focusRequest]);

  const backdrop = matchBackdrops(analogs);
  const selected = analogs.find((a) => a.rank === selectedRank);
  // Draw the best matches on top.
  const ordered = [...analogs].sort((a, b) => b.rank - a.rank);
  return (
    <div className="map-wrap">
      <MapContainer
        center={PALOUSE_CENTER}
        zoom={PALOUSE_ZOOM}
        minZoom={7}
        maxBounds={[
          [43.0, -125.0],
          [49.3, -112.0],
        ]}
        maxBoundsViscosity={1}
        className="map"
        aria-label="Map of your field and its climate analogs"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          noWrap={true}
        />
        <DrawControl onDraw={onFieldDrawn} cancelSignal={cancelSignal} />
        {showDemoCoverage && <DemoCoverage fields={testFields} />}
        <TestFieldMarkers testFields={showDemoCoverage ? [] : testFields} />
        {backdrop.length > 0 && (
          <Polygon
            positions={backdrop.map((ring) => [ring])}
            smoothFactor={0.15}
            interactive={false}
            pathOptions={{
              stroke: false, fillColor: '#343740', fillOpacity: 0.16, fillRule: 'nonzero',
              className: 'analog-backdrop', pmIgnore: true,
            } as L.PathOptions}
          />
        )}
        {outline && (
          <Polygon
            positions={outline.map(([lon, lat]) => [lat, lon] as [number, number])}
            pathOptions={{ ...FIELD_STYLE, color: '#459b63', weight: 1.5, dashArray: '7 5', lineCap: 'round', lineJoin: 'round', className: 'selected-field-outline', pmIgnore: true } as L.PathOptions}
          >
            <Tooltip sticky>Your field</Tooltip>
          </Polygon>
        )}
        {ordered.map((a) => {
          const style = matchQualityStyle(a.match_quality);
          const isSel = a.rank === selectedRank;
          const score = matchScore(a.sigma);
          // Keep the color tied to the score so it stays consistent across searches.
          const strength = Math.max(0, (score - 50) / 50);
          const cloudColor = score < 50 ? style.color : `hsl(${28 + strength * 113} ${90 - strength * 14}% ${58 - strength * 20}%)`;
          // Approximate the 1/24° PRISM grid cell around its reported center.
          const positions: [number, number][] = [
            [a.lat + 1 / 48, a.lon - 1 / 48],
            [a.lat + 1 / 48, a.lon + 1 / 48],
            [a.lat - 1 / 48, a.lon + 1 / 48],
            [a.lat - 1 / 48, a.lon - 1 / 48],
          ];
          return (
            <Polygon
              key={`${resultKey}-${a.rank}`}
              positions={positions}
              pathOptions={{
                stroke: false,
                fillColor: cloudColor,
                fillOpacity: isSel ? 0.82 : 0.60,
                className: 'analog-cloud',
                pmIgnore: true,
              } as L.PathOptions}
              eventHandlers={{ click: () => onSelect(a.rank) }}
            >
              <Tooltip>
                <strong>Rank {a.rank}</strong>
                {a.place_name ? ` — ${a.place_name}` : ''}
                <br />
                {style.label}, match score {score}/100
                <br />
                Approximate climate cell footprint
              </Tooltip>
            </Polygon>
          );
        })}
        {selected && outlinedRequest !== 0 && outlinedRequest === focusRequest && (
          <Rectangle
            bounds={[
              [selected.lat - 1 / 48, selected.lon - 1 / 48],
              [selected.lat + 1 / 48, selected.lon + 1 / 48],
            ]}
            interactive={false}
            pathOptions={{
              fill: false, color: '#175b44', weight: 1.5, dashArray: '7 5',
              lineCap: 'round', className: 'match-focus-outline', pmIgnore: true,
            } as L.PathOptions}
          />
        )}
        <FlyToField field={field} hidden={hidden} />
        <FlyToSelected analog={selected} focusRequest={focusRequest} hidden={hidden} />
        <FitToResult analogs={analogs} resultKey={resultKey} hidden={hidden} />
        <ResizeWhenVisible hidden={hidden} />
      </MapContainer>
      <Legend className="map-legend" />
    </div>
  );
}
