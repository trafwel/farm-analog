import type { AnalogResultView } from '../types/extensions';
import { MATCH_QUALITY_STYLES } from '../lib/matchQuality';
import { agreementText, getHeadline } from '../lib/headline';
import { SCENARIO_LABELS } from '../lib/scenario';
import { FingerprintTable } from './FingerprintTable';

export const DEMO_BANNER = 'Demo data — not a real analysis';
export const SIGMA_EXPLAINER =
  "Sigma measures how different a place's climate today is from your field's future climate, in units of your field's normal year-to-year swings. Lower sigma means a closer climate match.";

export interface ResultsPanelProps {
  result: AnalogResultView;
  selectedRank: number | null;
  onSelect: (rank: number) => void;
}

export function ResultsPanel({ result, selectedRank, onSelect }: ResultsPanelProps) {
  const headline = getHeadline(result);
  const analogs = [...result.analogs].sort((a, b) => a.rank - b.rank);
  const notes = result.notes?.filter((n) => n.trim() !== '') ?? [];
  return (
    <section className="results" aria-labelledby="results-heading">
      {result.source === 'fixture' && (
        <p className="banner banner-demo" role="note">
          {DEMO_BANNER}
        </p>
      )}
      <h2 id="results-heading">Results</h2>

      {headline.kind === 'novel' ? (
        <div className="banner banner-warning" role="alert">
          <strong>Warning: </strong>
          {headline.text}
        </div>
      ) : (
        <p className="headline">{headline.text}</p>
      )}

      <p className="muted small">{SIGMA_EXPLAINER}</p>

      <dl className="meta">
        <dt>Scenario</dt>
        <dd>{SCENARIO_LABELS[result.scenario]}</dd>
        <dt>Years compared</dt>
        <dd>
          {result.baseline_years.join('–')} → {result.future_years.join('–')}
        </dd>
        <dt>Climate models ({result.models.length})</dt>
        <dd>{result.models.join(', ')}</dd>
      </dl>

      {notes.length > 0 && (
        <div className="notes">
          <h3>About this result</h3>
          <ul>
            {notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      <h3 id="analog-list-heading">Matching places ({analogs.length})</h3>
      <p className="muted small">Select a place to show it on the map.</p>
      <ol className="analog-list" aria-labelledby="analog-list-heading">
        {analogs.map((a) => {
          const s = MATCH_QUALITY_STYLES[a.match_quality];
          const selected = a.rank === selectedRank;
          return (
            <li key={a.rank}>
              <button
                type="button"
                className={`analog-item${selected ? ' selected' : ''}`}
                aria-pressed={selected}
                onClick={() => onSelect(a.rank)}
              >
                <span className="swatch dot" style={{ background: s.color }} aria-hidden="true" />
                <span className="analog-text">
                  <strong>
                    Rank {a.rank}
                    {a.place_name ? `: ${a.place_name}` : ''}
                  </strong>
                  <span>
                    {s.label} (sigma {a.sigma.toFixed(2)}) · {agreementText(a)}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>

      <FingerprintTable
        today={result.farm_today}
        future={result.farm_future}
        baselineYears={result.baseline_years}
        futureYears={result.future_years}
      />
    </section>
  );
}
