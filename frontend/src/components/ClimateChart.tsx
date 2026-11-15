import type { Climograph } from '../types/contract';
import { MONTHS } from '../lib/hazards';
import { cToF, mmToInches } from '../lib/units';

/** The three series, in drawing order. Colors: the app's green (farm), its dark blue (analog)
 * and an orange that stays distinct for color-blind viewers (farm in the future). */
export const SERIES = [
  { key: 'farm_today', label: 'Your field today', color: '#2f6b3a', dash: '' },
  { key: 'farm_future', label: 'Your field, 2050s', color: '#c2410c', dash: '5 3' },
  { key: 'analog_today', label: 'This place today', color: '#08306b', dash: '' },
] as const;

const W = 380;
const H = 150;
const PAD = { left: 34, right: 8, top: 10, bottom: 20 };

function scale(min: number, max: number, lo: number, hi: number) {
  return (v: number) => hi - ((v - min) / (max - min || 1)) * (hi - lo);
}

/** Gridline values in steps of 5 (or a multiple), starting at or below ``min`` and ending at
 * or above ``max``, so every point sits inside the gridlines. */
export function niceTicks(min: number, max: number, count = 5): number[] {
  const step = Math.max(5, Math.ceil((max - min) / count / 5) * 5);
  const start = Math.floor(min / step) * step;
  const end = Math.ceil(max / step) * step;
  const out = [];
  for (let v = start; v <= end + 1e-9; v += step) out.push(v);
  return out;
}

export function ClimateChart({ climograph, placeLabel }: { climograph: Climograph; placeLabel: string }) {
  const x = (i: number) => PAD.left + (i + 0.5) * ((W - PAD.left - PAD.right) / 12);
  const temps = SERIES.flatMap((s) => climograph[s.key].tmean);
  const tTicks = niceTicks(Math.min(...temps, 0), Math.max(...temps));
  const tMin = tTicks[0]!;
  const tMax = tTicks[tTicks.length - 1]!;
  const yT = scale(tMin, tMax, PAD.top, H - PAD.bottom);
  const rain = SERIES.flatMap((s) => climograph[s.key].ppt);
  const pTicks = niceTicks(0, Math.max(...rain, 10));
  const pMax = pTicks[pTicks.length - 1]!;
  const yP = scale(0, pMax, PAD.top, H - PAD.bottom);
  const band = (W - PAD.left - PAD.right) / 12;
  const barW = band / 4;

  return (
    <figure className="chart">
      <figcaption>
        Monthly climate: your field today, your field in the 2050s, and {placeLabel} today
      </figcaption>
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

      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Average temperature by month, in degrees Celsius">
        <text x={PAD.left} y={8} className="chart-axis-title">Average temperature (°C)</text>
        {tTicks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={yT(t)} y2={yT(t)} className="chart-grid" />
            <text x={PAD.left - 4} y={yT(t) + 3} className="chart-tick" textAnchor="end">{t}</text>
          </g>
        ))}
        {MONTHS.map((m, i) => (
          <text key={m} x={x(i)} y={H - 6} className="chart-tick" textAnchor="middle">{m[0]}</text>
        ))}
        {SERIES.map((s) => (
          <polyline
            key={s.key}
            fill="none"
            stroke={s.color}
            strokeWidth="2.2"
            strokeDasharray={s.dash}
            points={climograph[s.key].tmean.map((v, i) => `${x(i)},${yT(v)}`).join(' ')}
          />
        ))}
      </svg>

      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Total precipitation by month, in millimetres">
        <text x={PAD.left} y={8} className="chart-axis-title">Precipitation (mm)</text>
        {pTicks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={yP(t)} y2={yP(t)} className="chart-grid" />
            <text x={PAD.left - 4} y={yP(t) + 3} className="chart-tick" textAnchor="end">{t}</text>
          </g>
        ))}
        {MONTHS.map((m, i) => (
          <text key={m} x={x(i)} y={H - 6} className="chart-tick" textAnchor="middle">{m[0]}</text>
        ))}
        {SERIES.map((s, k) =>
          climograph[s.key].ppt.map((v, i) => (
            <rect
              key={`${s.key}-${i}`}
              x={x(i) - 1.5 * barW + k * barW}
              y={yP(v)}
              width={barW - 0.5}
              height={Math.max(0, H - PAD.bottom - yP(v))}
              fill={s.color}
              opacity={s.key === 'farm_future' ? 0.75 : 0.9}
            />
          )),
        )}
      </svg>

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
                  {SERIES.map((s) => {
                    const t = climograph[s.key].tmean[i]!;
                    const p = climograph[s.key].ppt[i]!;
                    return (
                      <td key={s.key}>
                        {t.toFixed(1)} °C ({cToF(t).toFixed(0)} °F), {p.toFixed(0)} mm ({mmToInches(p).toFixed(1)} in)
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
