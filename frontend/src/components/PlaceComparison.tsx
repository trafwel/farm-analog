import { useState } from 'react';
import type { Analog, Hazards, SoilProfile } from '../types/contract';
import { MATCH_QUALITY_STYLES, matchScore } from '../lib/matchQuality';
import { hazardRows } from '../lib/hazards';
import { ClimateChart } from './ClimateChart';
import { SoilMoistureChart } from './SoilMoistureChart';
import { ScoreRing } from './ScoreRing';

export const NEEDS_LIVE =
  'Crops, topsoil, the monthly climate chart and hazards are fetched for the top 3 matches only. Ranks 4–20 are climate matches; select one of the top 3 for the full comparison.';

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
    <div className="table-scroll">
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
    </div>
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
      <div className="table-scroll">
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
                <td>{r.farm === '—' ? <span title="Data not available for this location">—</span> : r.farm}</td>
                <td>{r.place === '—' ? <span title="Data not available for this location">—</span> : r.place}</td>
                <td>{r.change === '—' ? <span title="Data not available for this location">—</span> : r.change}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted small">
        Heat and frost: PRISM daily, 1995–2014. Heavy rain: NASA GPM IMERG, 2014–2023. Soil water: NASA SMAP
        L4 root zone, 2016–2023. Ground temperature: NASA ECOSTRESS, clear summer afternoons 2018–2025,
        median over cropland within 1 km. Green cover:
        Landsat NDVI, 2019–2023 (below 0.25 counts as bare). Values are for the ~4–10 km grid cell
        around each point, except green cover, which is within 200 m.
        {missing.length > 0 && ` Not available: ${missing.join(', ')}.`}
      </p>
      {!place && (
        <p className="muted small" role="note">
          <strong>Note:</strong> Detailed hazard histories are computed for the top 3 matches only. Ranks 4–20 show dashes because individual hazard monitoring was not computed for this location.
        </p>
      )}
    </>
  );
}

export interface PlaceComparisonProps {
  analog: Analog;
  onShowOnMap?: (rank: number) => void;
  farmSoil: SoilProfile | null | undefined;
  farmHazards: Hazards | null | undefined;
}

/** Everything known about one matching place, side by side with the farm. */
export function PlaceComparison({ analog, farmSoil, farmHazards, onShowOnMap }: PlaceComparisonProps) {
  const [open, setOpen] = useState(true);
  const s = MATCH_QUALITY_STYLES[analog.match_quality];
  const label = analog.place_name ?? `the rank ${analog.rank} place`;
  const hasDetails = analog.climograph || analog.crops?.length || analog.soil || analog.hazards;
  const headingText = `Compare with rank ${analog.rank}${analog.place_name ? `: ${analog.place_name}` : ''}`;
  return (
    <section className="card comparison" aria-labelledby="comparison-heading">
      <div className="card-header">
        <h3 id="comparison-heading">{headingText}</h3>
        <button
          type="button"
          className="collapse-toggle"
          aria-expanded={open}
          aria-controls="comparison-content"
          aria-label={open ? `${headingText}, click to collapse` : `${headingText}, click to expand`}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? 'Collapse' : 'Expand'}
        </button>
      </div>
      <div className="comparison-score">
        <ScoreRing score={matchScore(analog.sigma)} quality={analog.match_quality} size={64} />
        <p className="small">
          <strong>{s.label}</strong> (match score {matchScore(analog.sigma)} out of 100).
          <br />
          Lat {analog.lat.toFixed(3)}, lon {analog.lon.toFixed(3)}.
        </p>
      </div>

      {onShowOnMap && (
        <button type="button" onClick={() => onShowOnMap(analog.rank)}>Show on map</button>
      )}

      {open && (
        <div id="comparison-content">
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
        </div>
      )}
    </section>
  );
}
