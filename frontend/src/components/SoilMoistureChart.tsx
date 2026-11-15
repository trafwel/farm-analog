import { MONTHS, soilWaterPct } from '../lib/hazards';
import { niceTicks } from './ClimateChart';

/** Same colors as the climate chart: green for the field, dark blue for the matching place. */
const SERIES = [
  { key: 'farm', label: 'Your field today', color: '#2f6b3a', dash: '' },
  { key: 'place', label: 'This place today', color: '#08306b', dash: '5 3' },
] as const;

const W = 380;
const H = 150;
const PAD = { left: 34, right: 8, top: 20, bottom: 20 };

type Series = (number | null)[] | null | undefined;

const ok = (v: number | null | undefined): v is number => typeof v === 'number' && Number.isFinite(v);

/** Splits a series at missing months so the line has gaps instead of bridging them. */
export function segments(values: Series): { i: number; v: number }[][] {
  const out: { i: number; v: number }[][] = [];
  let run: { i: number; v: number }[] = [];
  (values ?? []).forEach((v, i) => {
    if (ok(v)) run.push({ i, v });
    else if (run.length) {
      out.push(run);
      run = [];
    }
  });
  if (run.length) out.push(run);
  return out;
}

/**
 * Monthly root-zone soil water (NASA SMAP L4, 2016–2023) at the field and at a matching place,
 * both today. Values arrive as m³/m³ and are shown as percent by volume.
 */
export function SoilMoistureChart({ farm, place, placeLabel }: { farm: Series; place: Series; placeLabel: string }) {
  const data = { farm, place };
  const all = [...(farm ?? []), ...(place ?? [])].filter(ok).map((v) => v * 100);
  if (all.length === 0) return null;
  const ticks = niceTicks(Math.min(...all), Math.max(...all));
  const lo = ticks[0]!;
  const hi = ticks[ticks.length - 1]!;
  const x = (i: number) => PAD.left + (i + 0.5) * ((W - PAD.left - PAD.right) / 12);
  const y = (v: number) => H - PAD.bottom - ((v * 100 - lo) / (hi - lo || 1)) * (H - PAD.bottom - PAD.top);
  const cell = (v: number | null | undefined) => (ok(v) ? soilWaterPct(v) : '—');

  return (
    <figure className="chart">
      <figcaption>Soil water by month (top 1 m): your field today and {placeLabel} today</figcaption>
      <ul className="chart-legend">
        {SERIES.map((s) => (
          <li key={s.key}>
            <svg width="22" height="10" aria-hidden="true">
              <line x1="1" y1="5" x2="21" y2="5" stroke={s.color} strokeWidth="2.5" strokeDasharray={s.dash} />
            </svg>
            {s.label}
          </li>
        ))}
      </ul>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Root-zone soil water by month, in percent by volume">
        <text x={PAD.left} y={8} className="chart-axis-title">Soil water (% by volume)</text>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t / 100)} y2={y(t / 100)} className="chart-grid" />
            <text x={PAD.left - 4} y={y(t / 100) + 3} className="chart-tick" textAnchor="end">{t}</text>
          </g>
        ))}
        {MONTHS.map((m, i) => (
          <text key={m} x={x(i)} y={H - 6} className="chart-tick" textAnchor="middle">{m[0]}</text>
        ))}
        {SERIES.map((s) =>
          segments(data[s.key]).map((seg, k) => (
            <polyline
              key={`${s.key}-${k}`}
              fill="none"
              stroke={s.color}
              strokeWidth="2.2"
              strokeDasharray={s.dash}
              points={seg.map((p) => `${x(p.i)},${y(p.v)}`).join(' ')}
            />
          )),
        )}
      </svg>
      <p className="muted small">
        NASA SMAP Level 4 root-zone soil moisture, 2016–2023 monthly averages, for the ~9 km grid cell around each
        point. Lower means drier soil.
      </p>
      <details className="chart-table">
        <summary>Show these numbers as a table</summary>
        <div className="table-scroll">
          <table className="fp-table">
            <thead>
              <tr>
                <th scope="col">Month</th>
                {SERIES.map((s) => (
                  <th key={s.key} scope="col">{s.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MONTHS.map((m, i) => (
                <tr key={m}>
                  <th scope="row">{m}</th>
                  <td>{cell(farm?.[i])}</td>
                  <td>{cell(place?.[i])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
