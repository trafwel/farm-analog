import type { SeasonalFingerprint } from '../types/contract';
import { formatPrecip, formatPrecipChange, formatTemp, formatTempChange } from '../lib/units';

type Quarter = 'jfm' | 'amj' | 'jas' | 'ond';
const QUARTERS: { key: Quarter; label: string }[] = [
  { key: 'jfm', label: 'Jan–Mar' },
  { key: 'amj', label: 'Apr–Jun' },
  { key: 'jas', label: 'Jul–Sep' },
  { key: 'ond', label: 'Oct–Dec' },
];

export interface FingerprintTableProps {
  today: SeasonalFingerprint;
  future: SeasonalFingerprint;
  baselineYears: [number, number];
  futureYears: [number, number];
}

export function FingerprintTable({ today, future, baselineYears, futureYears }: FingerprintTableProps) {
  const rows = [
    ...QUARTERS.map((q) => {
      const k = `tmean_${q.key}` as const;
      return {
        id: k,
        label: `${q.label} average temperature`,
        now: formatTemp(today[k]),
        then: formatTemp(future[k]),
        change: formatTempChange(future[k] - today[k]),
      };
    }),
    ...QUARTERS.map((q) => {
      const k = `ppt_${q.key}` as const;
      return {
        id: k,
        label: `${q.label} total precipitation`,
        now: formatPrecip(today[k]),
        then: formatPrecip(future[k]),
        change: formatPrecipChange(future[k] - today[k]),
      };
    }),
  ];
  return (
    <div className="table-scroll">
      <table className="fp-table">
        <caption>Your field's climate fingerprint: today vs. future</caption>
        <thead>
          <tr>
            <th scope="col">Season</th>
            <th scope="col">
              Today
              <br />
              <span className="muted">{baselineYears.join('–')}</span>
            </th>
            <th scope="col">
              Future
              <br />
              <span className="muted">{futureYears.join('–')}</span>
            </th>
            <th scope="col">Change</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <th scope="row">{r.label}</th>
              <td>{r.now}</td>
              <td>{r.then}</td>
              <td>{r.change}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
