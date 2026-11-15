import { useEffect, useRef } from 'react';
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

/** Adds Geoman's polygon-drawing control. Every new drawing replaces the field. */
function DrawControl({ onDraw }: { onDraw: (ring: LonLat[]) => void }) {
  const map = useMap();
  const onDrawRef = useRef(onDraw);
  useEffect(() => {
    onDrawRef.current = onDraw;
  }, [onDraw]);

  useEffect(() => {
    map.pm.setGlobalOptions({
      pathOptions: FIELD_STYLE,
      templineStyle: { color: FIELD_COLOR },
      hintlineStyle: { color: FIELD_COLOR, dashArray: '5,5' },
      continueDrawing: false,
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
      const layer = e.layer;
      if (layer instanceof L.Polygon) {
        const rings = layer.getLatLngs() as LatLngLike[][];
        const outer = rings[0];
        const ring = outer ? latLngsToLonLat(outer) : [];
        // Ignore zero-area shapes (e.g. a rectangle made by a single click).
        if (distinctPointCount(ring) >= 3) onDrawRef.current(ring);
      }
      // The field is rendered from React state, so drop Geoman's own copy.
      map.removeLayer(layer);
    };
    map.on('pm:create', handleCreate);
    return () => {
      map.off('pm:create', handleCreate);
      map.pm.removeControls();
    };
  }, [map]);
  return null;
}

/** Pan to the selected analog. */
function FlyToSelected({ analog }: { analog: Analog | undefined }) {
  const map = useMap();
  useEffect(() => {
    if (analog) map.flyTo([analog.lat, analog.lon], Math.max(map.getZoom(), 9), { duration: 0.6 });
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
}

export function MapView({ field, onFieldDrawn, analogs, resultKey, selectedRank, onSelect, testFields = [] }: MapViewProps) {
  const selected = analogs.find((a) => a.rank === selectedRank);
  // Draw the best matches on top.
  const ordered = [...analogs].sort((a, b) => b.rank - a.rank);
  return (
    <div className="map-wrap">
      <MapContainer center={PALOUSE_CENTER} zoom={PALOUSE_ZOOM} className="map" aria-label="Map of your field and its climate analogs">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <DrawControl onDraw={onFieldDrawn} />
        {testFields.map((t) => (
          <Rectangle
            key={t.id}
            bounds={[
              [t.lat - 0.02, t.lon - 0.027],
              [t.lat + 0.02, t.lon + 0.027],
            ]}
            pathOptions={{ color: FIELD_COLOR, weight: 3, fillColor: FIELD_COLOR, fillOpacity: 0.25, pmIgnore: true } as L.PathOptions}
          >
            <Tooltip permanent direction="top" offset={[0, -6]}>
              {t.label.split(' (')[0]}
            </Tooltip>
          </Rectangle>
        ))}
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
