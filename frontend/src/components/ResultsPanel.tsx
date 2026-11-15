import { useState } from 'react';
import type { AnalogResultView } from '../types/extensions';
import { MATCH_QUALITY_STYLES, matchScore } from '../lib/matchQuality';
import { getHeadline } from '../lib/headline';
import { SCENARIO_LABELS } from '../lib/scenario';
import type { BillSummary } from '../lib/api';
import type { PriorityId } from '../lib/priorities';
import { BillSummaryCard } from './BillSummaryCard';
import { FingerprintTable } from './FingerprintTable';
import { Glossary } from './Glossary';
import { PlaceComparison } from './PlaceComparison';
import { RotationCards } from './RotationCards';
import { ScoreRing } from './ScoreRing';
import { ResultDetails } from './ResultDetails';

export const DEMO_BANNER = 'Demo data — not a real analysis';

export interface ResultsPanelProps {
  result: AnalogResultView;
  selectedRank: number | null;
  onShowOnMap?: (rank: number) => void;
  onSelect: (rank: number) => void;
  /** Bill's plain-language summary, when the server provided one. */
  billSummary?: BillSummary | null;
  chosenGoals?: PriorityId[];
  onGoalsChange?: (g: PriorityId[]) => void;
}

export function ResultsPanel({ result, selectedRank, onSelect, onShowOnMap, billSummary, chosenGoals, onGoalsChange }: ResultsPanelProps) {
  const [placesOpen, setPlacesOpen] = useState(true);
  const headline = getHeadline(result);
  const analogs = [...result.analogs].sort((a, b) => a.rank - b.rank);
  const notes = result.notes?.filter((n) => n.trim() !== '') ?? [];
  // The comparison follows the selected place, or the best match when nothing is selected.
  const compared = analogs.find((a) => a.rank === selectedRank) ?? analogs[0];
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

      <dl className="meta">
        <dt>Scenario</dt>
        <dd>{SCENARIO_LABELS[result.scenario]}</dd>
        <dt>Years compared</dt>
        <dd>
          {result.baseline_years.join('–')} → {result.future_years.join('–')}
        </dd>
      </dl>

      {result.rotations && result.rotations.length > 0 && (
        <RotationCards rotations={result.rotations} chosen={chosenGoals} onChosenChange={onGoalsChange} />
      )}

      {compared && (
        <PlaceComparison onShowOnMap={onShowOnMap} analog={compared} farmSoil={result.farm_soil} farmHazards={result.farm_hazards} />
      )}

      <section className="card analog-list-card" aria-labelledby="analog-list-heading">
        <div className="card-header">
          <h3 id="analog-list-heading">Matching places ({analogs.length})</h3>
          <button
            type="button"
            className="collapse-toggle"
            aria-expanded={placesOpen}
            aria-controls="analog-list-content"
            aria-label={placesOpen ? 'Matching places, click to collapse' : 'Matching places, click to expand'}
            onClick={() => setPlacesOpen((o) => !o)}
          >
            {placesOpen ? 'Collapse' : 'Expand'}
          </button>
        </div>
        {placesOpen && (
          <div id="analog-list-content">
            <p className="muted small">Select a place to show it on the map and compare it above.</p>
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
                      <ScoreRing score={matchScore(a.sigma)} quality={a.match_quality} />
                      <span className="analog-text">
                        <strong>
                          Rank {a.rank}
                          {a.place_name ? `: ${a.place_name}` : ''}
                        </strong>
                        <span>{s.label}</span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ol>
          </div>
        )}
      </section>

      {billSummary && <BillSummaryCard summary={billSummary} />}

      <FingerprintTable
        today={result.farm_today}
        future={result.farm_future}
        baselineYears={result.baseline_years}
        futureYears={result.future_years}
      />

      <Glossary />

      <ResultDetails analogs={analogs} models={result.models} notes={notes} rotations={result.rotations} />
    </section>
  );
}
