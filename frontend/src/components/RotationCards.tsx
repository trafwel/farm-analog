import { useState } from 'react';
import type { RotationStrategy } from '../types/contract';
import { bestFit, NOT_SCORED, PRIORITIES, type PriorityId, priorityFit, sortByPriorities } from '../lib/priorities';

export const ROTATION_INTRO =
  'Crop rotations seen on farmland whose climate today matches your field’s 2050s climate, next to the rotation your field grows now. They show what already works in that climate; they are not recommendations.';

/** Evidence lines about climate-model agreement; shown under Result Details instead. */
export function isModelAgreementLine(line: string): boolean {
  return /\bof \d+ climate models\b/i.test(line);
}

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

/** Checkboxes for the farmer's priorities (M19). Kept in this component only: not saved,
 * not sent anywhere and not put in the page address. */
function PriorityPicker({ chosen, onChange }: { chosen: PriorityId[]; onChange: (c: PriorityId[]) => void }) {
  const toggle = (id: PriorityId) =>
    onChange(chosen.includes(id) ? chosen.filter((c) => c !== id) : [...chosen, id]);
  return (
    <fieldset className="priorities">
      <legend>What matters most to you? Options are sorted by fit.</legend>
      {PRIORITIES.map((p) => (
        <label key={p.id}>
          <input type="checkbox" checked={chosen.includes(p.id)} onChange={() => toggle(p.id)} /> {p.label}
        </label>
      ))}
      <p className="muted small">{NOT_SCORED}</p>
    </fieldset>
  );
}

export function RotationCards({
  rotations,
  chosen: externalChosen,
  onChosenChange,
}: {
  rotations: RotationStrategy[];
  chosen?: PriorityId[];
  onChosenChange?: (c: PriorityId[]) => void;
}) {
  const [open, setOpen] = useState(true);
  const [internalChosen, setInternalChosen] = useState<PriorityId[]>([]);
  const chosen = externalChosen !== undefined ? externalChosen : internalChosen;
  const setChosen = onChosenChange ?? setInternalChosen;
  const hasTraits = rotations.some((r) => r.traits);
  const shown = sortByPriorities(rotations, chosen);
  const best = bestFit(rotations, chosen);
  const chosenLabels = PRIORITIES.filter((p) => chosen.includes(p.id)).map((p) => p.label);
  return (
    <section className="card" aria-labelledby="rotations-heading">
      <div className="card-header">
        <h3 id="rotations-heading">Rotation options ({rotations.length})</h3>
        <button
          type="button"
          className="collapse-toggle"
          aria-expanded={open}
          aria-controls="rotations-content"
          aria-label={open ? 'Rotation options, click to collapse' : 'Rotation options, click to expand'}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? 'Collapse' : 'Expand'}
        </button>
      </div>
      {open && (
        <div id="rotations-content">
          <p className="muted small">{ROTATION_INTRO}</p>
          {hasTraits && <PriorityPicker chosen={chosen} onChange={setChosen} />}
          <p className="sr-only" aria-live="polite">
            {chosen.length > 0 ? `Options sorted by fit to: ${chosenLabels.join(', ')}. Your current rotation stays first.` : ''}
          </p>
          <ol className="rotation-list">
            {shown.map((r) => {
              const fit = priorityFit(r, chosen);
              return (
                <li key={r.name} className={`rotation${r.current ? ' rotation-current' : ''}`}>
                  <h4>
                    {r.current && <span className="badge">Your field now</span>}
                    {r.name}
                    {best.has(r.name) && <span className="fit">Best fit for your choices</span>}
                  </h4>
                  <p className="rotation-stats small">
                    {pct(r.analog_share)} of analog-area cropland · used in {r.analogs_using} of {r.analogs_checked} analog
                    areas
                    {r.field_share != null && ` · ${pct(r.field_share)} of your field`}
                  </p>
                  <p className="small">{r.why}</p>
                  {fit && (
                    <ul className="fit-reasons small" aria-label="How it fits your priorities">
                      {fit.reasons.map((x) => (
                        <li key={x.label}>
                          <b>{x.label}:</b> {x.text}
                        </li>
                      ))}
                    </ul>
                  )}
                  <details>
                    <summary>Evidence, benefits, risks and gaps</summary>
                    <List title="Evidence" items={r.evidence.filter((e) => !isModelAgreementLine(e))} />
                    <List title="Possible benefits" items={r.benefits} />
                    <List title="Risks" items={r.risks} />
                    <List title="What we don't know" items={r.gaps} />
                  </details>
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </section>
  );
}
