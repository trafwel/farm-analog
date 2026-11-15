import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import '@geoman-io/leaflet-geoman-free';
import { CircleMarker, MapContainer, Polygon, Rectangle, TileLayer, Tooltip, useMap } from 'react-leaflet';
import type { TestField } from '../lib/staticDemo';
import type { Analog } from '../types/contract';
import { matchQualityStyle } from '../lib/matchQuality';
import { agreementText } from '../lib/headline';
import type { LatLngLike, LonLat } from '../lib/request';
import { distinctPointCount, latLngsToLonLat } from '../lib/request';
import { Legend } from './Legend';
import { FIELD_COLOR_SWATCH } from './swatches';

export const PALOUSE_CENTER: [number, number] = [46.85, -117.6];
export const PALOUSE_ZOOM = 8;
export const FIELD_COLOR = FIELD_COLOR_SWATCH;

const FIELD_STYLE: L.PathOptions = { color: FIELD_COLOR, fillColor: FIELD_COLOR, fillOpacity: 0.3, weight: 3 };

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
      drawCircle: false,
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
      if (layer instanceof L.Polygon) {
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

    const onDrawStart = (e: { shape: string }) => {
      isDrawingRectangle = e.shape === 'Rectangle';
    };

    const onDrawEnd = () => {
      isDrawingRectangle = false;
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
      if (!isDrawingRectangle || !startLatLng) return;
      const bounds = L.latLngBounds(startLatLng, e.latlng);
      if (!previewRect) {
        previewRect = L.rectangle(bounds, FIELD_STYLE).addTo(map);
      } else {
        previewRect.setBounds(bounds);
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

/** Pan to the selected analog quickly. */
function FlyToSelected({ analog }: { analog: Analog | undefined }) {
  const map = useMap();
  useEffect(() => {
    if (analog) map.flyTo([analog.lat, analog.lon], Math.max(map.getZoom(), 9), { duration: 0.2 });
  }, [map, analog]);
  return null;
}

/** Fit the view to the field plus all analogs whenever a new result arrives. */
function FitToResult({ analogs, field, resultKey }: { analogs: Analog[]; field: LonLat[] | null; resultKey: string }) {
  const map = useMap();
  const lastKey = useRef<string>('');
  useEffect(() => {
    if (!resultKey || resultKey === lastKey.current || analogs.length === 0) return;
    lastKey.current = resultKey;
    const pts: [number, number][] = analogs.map((a) => [a.lat, a.lon]);
    field?.forEach(([lon, lat]) => pts.push([lat, lon]));
    map.fitBounds(L.latLngBounds(pts), { padding: [30, 30], maxZoom: 10 });
  }, [map, analogs, field, resultKey]);
  return null;
}

export interface MapViewProps {
  field: LonLat[] | null;
  onFieldDrawn: (ring: LonLat[]) => void;
  analogs: Analog[];
  resultKey: string;
  selectedRank: number | null;
  onSelect: (rank: number) => void;
  /** Static demo: the test fields that have saved results, outlined so people can find them. */
  testFields?: TestField[];
  cancelSignal?: unknown;
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
        const name = TEST_FIELD_NAMES[t.id] ?? t.label.split(' (')[0]!.split(',')[0];
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

export function MapView({ field, onFieldDrawn, analogs, resultKey, selectedRank, onSelect, testFields = [], cancelSignal }: MapViewProps) {
  const selected = analogs.find((a) => a.rank === selectedRank);
  // Draw the best matches on top.
  const ordered = [...analogs].sort((a, b) => b.rank - a.rank);
  return (
    <div className="map-wrap">
      <MapContainer
        center={PALOUSE_CENTER}
        zoom={PALOUSE_ZOOM}
        minZoom={6}
        maxBounds={[
          [38.0, -127.0],
          [54.0, -110.0],
        ]}
        maxBoundsViscosity={0.75}
        className="map"
        aria-label="Map of your field and its climate analogs"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          noWrap={true}
        />
        <DrawControl onDraw={onFieldDrawn} cancelSignal={cancelSignal} />
        <TestFieldMarkers testFields={testFields} />
        {field && (
          <Polygon
            positions={field.map(([lon, lat]) => [lat, lon] as [number, number])}
            pathOptions={{ ...FIELD_STYLE, pmIgnore: true } as L.PathOptions}
          >
            <Tooltip sticky>Your field</Tooltip>
          </Polygon>
        )}
        {ordered.map((a) => {
          const style = matchQualityStyle(a.match_quality);
          const isSel = a.rank === selectedRank;
          return (
            <CircleMarker
              key={`${resultKey}-${a.rank}`}
              center={[a.lat, a.lon]}
              radius={isSel ? 13 : 8}
              pathOptions={{
                color: isSel ? '#d94801' : '#ffffff',
                weight: isSel ? 4 : 1.5,
                fillColor: style.color,
                fillOpacity: 0.9,
              }}
              eventHandlers={{ click: () => onSelect(a.rank) }}
            >
              <Tooltip>
                <strong>Rank {a.rank}</strong>
                {a.place_name ? ` — ${a.place_name}` : ''}
                <br />
                {style.label}, sigma {a.sigma.toFixed(2)}
                <br />
                {agreementText(a)}
              </Tooltip>
            </CircleMarker>
          );
        })}
        <FlyToSelected analog={selected} />
        <FitToResult analogs={analogs} field={field} resultKey={resultKey} />
      </MapContainer>
      <Legend className="map-legend" />
    </div>
  );
}
