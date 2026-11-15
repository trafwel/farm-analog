import type { Analog, Hazards, SoilProfile } from '../types/contract';
import { MATCH_QUALITY_STYLES } from '../lib/matchQuality';
import { agreementText } from '../lib/headline';
import { hazardRows } from '../lib/hazards';
import { ClimateChart } from './ClimateChart';
import { SoilMoistureChart } from './SoilMoistureChart';

export const NEEDS_LIVE =
  'Crops, soil, climate charts and hazards for this place appear when the analysis runs with Earth Engine, or near one of the 5 saved test fields.';

function SoilTable({ farm, place }: { farm: SoilProfile | null | undefined; place: SoilProfile | null | undefined }) {
  const rows: { label: string; key: keyof SoilProfile }[] = [
    { label: 'Clay', key: 'clay_pct' },
    { label: 'Sand', key: 'sand_pct' },
    { label: 'Organic matter', key: 'organic_matter_pct' },
  ];
  const fmt = (v: number | null | undefined) => (typeof v === 'number' ? `${v.toFixed(1)}%` : '—');
  if (!rows.some((r) => farm?.[r.key] != null || place?.[r.key] != null)) return null;
  // The pipeline doesn't fetch the farm's own soil yet; show its column only when it has data.
  const showFarm = rows.some((r) => farm?.[r.key] != null);
  return (
    <table className="fp-table">
      <caption>Topsoil (OpenLandMap, 250 m)</caption>
      <thead>
        <tr>
          <th scope="col"> </th>
          {showFarm && <th scope="col">Your field</th>}
          <th scope="col">This place</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.key}>
            <th scope="row">{r.label}</th>
            {showFarm && <td>{fmt(farm?.[r.key])}</td>}
            <td>{fmt(place?.[r.key])}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function HazardTable({ farm, place, placeLabel }: {
  farm: Hazards | null | undefined;
  place: Hazards | null | undefined;
  placeLabel: string;
}) {
  const rows = hazardRows(farm, place);
  if (rows.length === 0) return null;
  const missing = [...new Set([...(farm?.missing_sources ?? []), ...(place?.missing_sources ?? [])])];
  return (
    <>
      <table className="fp-table">
        <caption>Hazard outlook: your field today vs. {placeLabel} today</caption>
        <thead>
          <tr>
            <th scope="col"> </th>
            <th scope="col">Your field today</th>
            <th scope="col">This place today (a preview of your 2050s)</th>
            <th scope="col">Difference</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <th scope="row">{r.label}</th>
              <td>{r.farm}</td>
              <td>{r.place}</td>
              <td>{r.change}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted small">
        Heat and frost: PRISM daily, 1995–2014. Heavy rain: NASA GPM IMERG, 2014–2023. Soil water: NASA SMAP
        L4 root zone, 2016–2023. Green cover:
        Landsat NDVI, 2019–2023 (below 0.25 counts as bare). Values are for the ~4–10 km grid cell
        around each point, except green cover, which is within 200 m.
        {missing.length > 0 && ` Not available: ${missing.join(', ')}.`}
      </p>
    </>
  );
}

export interface PlaceComparisonProps {
  analog: Analog;
  farmSoil: SoilProfile | null | undefined;
  farmHazards: Hazards | null | undefined;
}

/** Everything known about one matching place, side by side with the farm. */
export function PlaceComparison({ analog, farmSoil, farmHazards }: PlaceComparisonProps) {
  const s = MATCH_QUALITY_STYLES[analog.match_quality];
  const label = analog.place_name ?? `the rank ${analog.rank} place`;
  const hasDetails = analog.climograph || analog.crops?.length || analog.soil || analog.hazards;
  return (
    <section className="card comparison" aria-labelledby="comparison-heading">
      <h3 id="comparison-heading">
        Compare with rank {analog.rank}
        {analog.place_name ? `: ${analog.place_name}` : ''}
      </h3>
      <p className="small">
        {s.label} (sigma {analog.sigma.toFixed(2)}) · {agreementText(analog)}. Lat {analog.lat.toFixed(3)}, lon{' '}
        {analog.lon.toFixed(3)}.
      </p>

      {!hasDetails && <p className="muted small">{NEEDS_LIVE}</p>}

      {analog.climograph && <ClimateChart climograph={analog.climograph} placeLabel={label} />}

      {analog.crops && analog.crops.length > 0 && (
        <div>
          <h4>What grows there (share of cropland, USDA Cropland Data Layer 2019–2023)</h4>
          <ul className="crop-bars">
            {analog.crops.map((c) => (
              <li key={c.crop}>
                <span className="crop-name">{c.crop}</span>
                <span className="crop-bar" aria-hidden="true">
                  <span style={{ width: `${Math.round(c.share * 100)}%` }} />
                </span>
                <span className="crop-share">{Math.round(c.share * 100)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <SoilTable farm={farmSoil} place={analog.soil} />

      <HazardTable farm={farmHazards} place={analog.hazards} placeLabel={label} />

      <SoilMoistureChart
        farm={farmHazards?.soil_moisture_monthly}
        place={analog.hazards?.soil_moisture_monthly}
        placeLabel={label}
      />
    </section>
  );
}
