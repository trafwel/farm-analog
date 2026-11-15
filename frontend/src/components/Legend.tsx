import { MATCH_QUALITY_ORDER, MATCH_QUALITY_STYLES } from '../lib/matchQuality';
import { FIELD_COLOR_SWATCH } from './swatches';

export function Legend({ className = '' }: { className?: string }) {
  return (
    <div className={`legend ${className}`} aria-label="Map legend">
      <p className="legend-title">Match quality</p>
      <ul>
        {MATCH_QUALITY_ORDER.map((q) => {
          const s = MATCH_QUALITY_STYLES[q];
          return (
            <li key={q}>
              <span className="swatch dot" style={{ background: s.color }} aria-hidden="true" />
              {s.label} <span className="muted">({s.description})</span>
            </li>
          );
        })}
        <li>
          <span className="swatch square" style={{ background: FIELD_COLOR_SWATCH }} aria-hidden="true" />
          Your field
        </li>
      </ul>
    </div>
  );
}
