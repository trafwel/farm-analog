import type { BillSummary } from '../lib/api';

/** Bill's summary as plain text (React escapes it; never rendered as HTML). */
export function BillSummaryCard({ summary }: { summary: BillSummary }) {
  return (
    <section className="card" aria-labelledby="bill-heading">
      <h3 id="bill-heading">In plain words</h3>
      <p className="bill-text">{summary.text}</p>
      <p className="muted small">
        {summary.source === 'gemini'
          ? 'Written by Bill (Gemini) from the numbers above; every number is checked against the result.'
          : 'Built from the numbers above by a fixed template (no AI was used for this text).'}
      </p>
    </section>
  );
}
