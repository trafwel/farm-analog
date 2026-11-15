import { useState } from 'react';
import type { BillSummary } from '../lib/api';

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
        </div>
      )}
    </section>
  );
}
