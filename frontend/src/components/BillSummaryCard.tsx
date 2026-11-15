import { useState } from 'react';
import type { BillSummary } from '../lib/api';

/** Where the text came from, in plain words. */
export function sourceLine(s: BillSummary): string {
  if (s.source === 'template') return 'Built from the numbers above by a fixed template (no AI was used for this text).';
  if (s.generated) {
    return `Written ahead of time by Bill (Gemini${s.model ? `, ${s.model}` : ''}) for this test field on ${s.generated}. Every number was checked against the result.`;
  }
  return 'Written by Bill (Gemini) from the numbers above; every number is checked against the result.';
}

/** Bill's summary as plain text (React escapes it; never rendered as HTML). */
export function BillSummaryCard({ summary }: { summary: BillSummary }) {
  const [open, setOpen] = useState(true);
  return (
    <section className="card" aria-labelledby="bill-heading">
      <div className="card-header">
        <h3 id="bill-heading">In plain words</h3>
        <button
          type="button"
          className="collapse-toggle"
          aria-expanded={open}
          aria-controls="bill-content"
          aria-label={open ? 'In plain words, click to collapse' : 'In plain words, click to expand'}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? 'Collapse' : 'Expand'}
        </button>
      </div>
      {open && (
        <div id="bill-content">
          <p className="bill-text">{summary.text}</p>
          <p className="muted small">{sourceLine(summary)}</p>
        </div>
      )}
    </section>
  );
}
