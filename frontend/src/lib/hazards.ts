import type { Hazards } from '../types/contract';

export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

/** Day of year (1–365, non-leap) to a date like "May 7". */
export function doyToDate(doy: number): string {
  let day = Math.round(doy);
  for (let m = 0; m < 12; m++) {
    const n = DAYS_IN_MONTH[m]!;
    if (day <= n) return `${MONTHS[m]} ${Math.max(day, 1)}`;
    day -= n;
  }
  return 'Dec 31';
}

/** Month numbers (1–12) as ranges, e.g. [1,2,3,8,9,10] → "Jan–Mar, Aug–Oct". */
export function formatMonths(months: number[] | null | undefined): string {
  if (!months || months.length === 0) return 'none';
  const sorted = [...new Set(months)].sort((a, b) => a - b);
  const parts: string[] = [];
  let start = sorted[0]!;
  let prev = start;
  for (const m of [...sorted.slice(1), Infinity]) {
    if (m === prev + 1) {
      prev = m;
      continue;
    }
    parts.push(start === prev ? MONTHS[start - 1]! : `${MONTHS[start - 1]}–${MONTHS[prev - 1]}`);
    start = m;
    prev = m;
  }
  return parts.join(', ');
}

/** Volumetric soil water (m³/m³) as percent by volume, one decimal: 0.166 → "16.6%". */
export function soilWaterPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

/** The driest month (lowest value) in a 12-month series, skipping missing months. */
export function driestMonth(values: (number | null)[] | null | undefined): { month: number; value: number } | null {
  let best: { month: number; value: number } | null = null;
  (values ?? []).forEach((v, i) => {
    if (typeof v === 'number' && Number.isFinite(v) && (best === null || v < best.value)) best = { month: i + 1, value: v };
  });
  return best;
}

export interface HazardRow {
  id: string;
  label: string;
  farm: string;
  place: string;
  change: string;
}

function num(v: number | null | undefined): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}

function signed(n: number, unit: string): string {
  const r = Math.round(n);
  return `${r > 0 ? '+' : ''}${r}${unit}`;
}

/**
 * Rows comparing the farm's hazards today with a place's hazards today (the place's today
 * previews the farm's future). A row appears only when at least one side has a value.
 */
export function hazardRows(farm: Hazards | null | undefined, place: Hazards | null | undefined): HazardRow[] {
  const f = farm ?? ({} as Partial<Hazards>);
  const p = place ?? ({} as Partial<Hazards>);
  const rows: HazardRow[] = [];
  const add = (id: string, label: string, a: number | null | undefined, b: number | null | undefined,
    fmt: (v: number) => string, change: (a: number, b: number) => string) => {
    if (!num(a) && !num(b)) return;
    rows.push({
      id,
      label,
      farm: num(a) ? fmt(a) : '—',
      place: num(b) ? fmt(b) : '—',
      change: num(a) && num(b) ? change(a, b) : '—',
    });
  };
  const days = (v: number) => `${Math.round(v)} days`;
  add('heat', 'Hot days above 32 °C (90 °F) per year', f.heat_days, p.heat_days, days,
    (a, b) => signed(Math.round(b) - Math.round(a), ' days'));
  add('ffd', 'Frost-free season', f.frost_free_days, p.frost_free_days, days,
    (a, b) => signed(Math.round(b) - Math.round(a), ' days'));
  add('spring', 'Last spring frost (average)', f.last_spring_frost_doy, p.last_spring_frost_doy, doyToDate,
    (a, b) => { const d = Math.round(b) - Math.round(a); return d === 0 ? 'same' : `${Math.abs(d)} days ${d < 0 ? 'earlier' : 'later'}`; });
  add('fall', 'First fall frost (average)', f.first_fall_frost_doy, p.first_fall_frost_doy, doyToDate,
    (a, b) => { const d = Math.round(b) - Math.round(a); return d === 0 ? 'same' : `${Math.abs(d)} days ${d < 0 ? 'earlier' : 'later'}`; });
  add('rain', 'Days with 25 mm (1 in) of rain or more, per year', f.extreme_rain_days, p.extreme_rain_days,
    (v) => v.toFixed(1), (a, b) => `${b - a > 0 ? '+' : ''}${(b - a).toFixed(1)}`);
  add('wettest', 'Wettest day of the year (average)', f.max_1day_rain_mm, p.max_1day_rain_mm,
    (v) => `${Math.round(v)} mm`, (a, b) => signed(b - a, ' mm'));
  const fd = driestMonth(f.soil_moisture_monthly);
  const pd = driestMonth(p.soil_moisture_monthly);
  if (fd || pd) {
    const fmt = (d: { month: number; value: number } | null) =>
      d ? `${soilWaterPct(d.value)} (${MONTHS[d.month - 1]})` : '—';
    const diff = fd && pd ? Math.round((pd.value - fd.value) * 1000) / 10 : null;
    rows.push({
      id: 'soil',
      label: 'Soil water in the driest month (top 1 m, % by volume)',
      farm: fmt(fd),
      place: fmt(pd),
      change: diff === null ? '—' : diff === 0 ? 'same' : `${diff > 0 ? '+' : ''}${diff.toFixed(1)} points`,
    });
  }
  if (f.bare_months || p.bare_months) {
    rows.push({
      id: 'bare',
      label: 'Months with little green cover (bare soil risk)',
      farm: f.bare_months ? formatMonths(f.bare_months) : '—',
      place: p.bare_months ? formatMonths(p.bare_months) : '—',
      change: '',
    });
  }
  return rows;
}
