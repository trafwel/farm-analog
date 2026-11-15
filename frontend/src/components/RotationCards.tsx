import type { RotationStrategy } from '../types/contract';

export const ROTATION_INTRO =
  'Crop rotations seen on farmland whose climate today matches your field’s 2050s climate, next to the rotation your field grows now. They show what already works in that climate; they are not recommendations.';

function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

function List({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <>
      <h5>{title}</h5>
      <ul>
        {items.map((t, i) => (
          <li key={i}>{t}</li>
        ))}
      </ul>
    </>
  );
}

export function RotationCards({ rotations }: { rotations: RotationStrategy[] }) {
  return (
    <section className="card" aria-labelledby="rotations-heading">
      <h3 id="rotations-heading">Rotation options ({rotations.length})</h3>
      <p className="muted small">{ROTATION_INTRO}</p>
      <ol className="rotation-list">
        {rotations.map((r) => (
          <li key={r.name} className={`rotation${r.current ? ' rotation-current' : ''}`}>
            <h4>
              {r.current && <span className="badge">Your field now</span>}
              {r.name}
            </h4>
            <p className="rotation-stats small">
              {pct(r.analog_share)} of analog-area cropland · used in {r.analogs_using} of {r.analogs_checked} analog
              areas
              {r.field_share != null && ` · ${pct(r.field_share)} of your field`}
            </p>
            <p className="small">{r.why}</p>
            <details>
              <summary>Evidence, benefits, risks and gaps</summary>
              <List title="Evidence" items={r.evidence} />
              <List title="Possible benefits" items={r.benefits} />
              <List title="Risks" items={r.risks} />
              <List title="What we don't know" items={r.gaps} />
            </details>
          </li>
        ))}
      </ol>
    </section>
  );
}
