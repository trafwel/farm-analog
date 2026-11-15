import { useState } from 'react';
import { MATCH_QUALITY_ORDER, MATCH_QUALITY_STYLES } from '../lib/matchQuality';
import { FIELD_COLOR_SWATCH } from './swatches';

export function Legend({ className = '' }: { className?: string }) {
  const [open, setOpen] = useState(true);
  return (
    <div className={`legend ${className}`} aria-label="Map legend">
      <div className="legend-header" onClick={() => setOpen((o) => !o)} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && setOpen((o) => !o)}>
        <span className="legend-title">Match quality</span>
        <button
          type="button"
          className="legend-toggle"
          aria-label={open ? 'Collapse legend' : 'Expand legend'}
          aria-expanded={open}
          onClick={(e) => {
            e.stopPropagation();
            setOpen((o) => !o);
          }}
        >
          {open ? '−' : '+'}
        </button>
      </div>
      {open && (
        <ul>
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
