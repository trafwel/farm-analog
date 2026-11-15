import { useState } from 'react';
import { MATCH_QUALITY_ORDER, MATCH_QUALITY_STYLES } from '../lib/matchQuality';
import { FIELD_COLOR_SWATCH } from './swatches';

export function Legend({ className = '' }: { className?: string }) {
  const [open, setOpen] = useState(true);
  return (
    <div className={`legend ${className}`} aria-label="Map legend">
      <button
        type="button"
        className="legend-header"
        aria-expanded={open}
        aria-controls="legend-list"
        aria-label={open ? 'Match quality legend, click to collapse' : 'Match quality legend, click to expand'}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="legend-title">Match quality</span>
        <span className="legend-toggle-icon" aria-hidden="true">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <ul id="legend-list">
          <li className="match-gradient-key">
            <span>50</span><span className="match-gradient" aria-hidden="true" /><span>100</span>
          </li>
          {MATCH_QUALITY_ORDER.map((q) => {
            const s = MATCH_QUALITY_STYLES[q];
            return (
              <li key={q}>
                <span className="swatch dot" style={{ background: s.color }} aria-hidden="true" />
                <span>{s.label} <span className="muted">({s.description})</span></span>
              </li>
            );
          })}
          <li>
            <span className="swatch square" style={{ background: FIELD_COLOR_SWATCH }} aria-hidden="true" />
            <span>Your field</span>
          </li>
        </ul>
      )}
    </div>
  );
}
