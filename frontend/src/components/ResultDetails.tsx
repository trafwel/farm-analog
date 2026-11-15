import type { Analog, RotationStrategy } from '../types/contract';
import { agreementText } from '../lib/headline';
import { MATCH_QUALITY_ORDER, MATCH_QUALITY_STYLES, matchScore } from '../lib/matchQuality';
import { isModelAgreementLine } from './RotationCards';

/** Sigma range behind each score band (backend thresholds: 1, 2, 4). */
const SIGMA_RANGES = {
  strong: 'sigma below 1',
  good: 'sigma 1 to 2',
  weak: 'sigma 2 to 4',
  none: 'sigma 4 or more',
} as const;

export const RESULT_DETAILS_TITLE = 'Result Details';

export const SCORE_METHOD =
  'The match score is a rescaled sigma dissimilarity (Mahony et al., 2017): how different a place’s climate today is from your field’s projected climate, in units of your field’s normal year-to-year swings. Sigma 0 scores 100, and the score falls in straight lines to 85 at sigma 1, 70 at sigma 2, 50 at sigma 4 and 0 at sigma 8. Each place’s sigma is the median across the climate models.';

export const STATISTICAL_TERMS: { term: string; meaning: string }[] = [
  {
    term: 'Sigma',
    meaning:
      'How different two climates are, measured in your field’s normal year-to-year swings. Below 1 is like an ordinary year at your field; 4 or more means no real match.',
  },
  {
    term: 'Climate models agreeing',
    meaning:
      'We run several NASA-downscaled climate models (NEX-GDDP-CMIP6). A place counts as agreed by a model when it is a good match (sigma below 2) under that model’s future.',
  },
];

export interface ResultDetailsProps {
  analogs: Analog[];
  models: string[];
  /** The result's caveat notes ("About this result"). */
  notes: string[];
  rotations?: RotationStrategy[] | null;
}

/** Caveats and the numbers behind the match scores, collapsed by default at the end of the results. */
export function ResultDetails({ analogs, models, notes, rotations }: ResultDetailsProps) {
  const rotationAgreement = (rotations ?? []).flatMap((r) =>
    r.evidence.filter(isModelAgreementLine).map((line) => ({ name: r.name, line })),
  );
  return (
    <details className="card result-details">
      <summary>{RESULT_DETAILS_TITLE}</summary>

      {notes.length > 0 && (
        <div className="notes">
          <h4>About this result</h4>
          <ul>
            {notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      <h4>How the match score works</h4>
      <p className="small">{SCORE_METHOD}</p>
      <ul className="small score-bands">
        {MATCH_QUALITY_ORDER.map((q) => (
          <li key={q}>
            <strong>{MATCH_QUALITY_STYLES[q].label}</strong>: {MATCH_QUALITY_STYLES[q].description} ({SIGMA_RANGES[q]})
          </li>
        ))}
      </ul>

      {analogs.length > 0 && (
        <div className="table-scroll">
          <table className="fp-table stat-table">
            <caption>Sigma and model agreement for each matching place</caption>
            <thead>
              <tr>
                <th scope="col">Rank</th>
                <th scope="col">Place</th>
                <th scope="col">Score</th>
                <th scope="col">Sigma</th>
                <th scope="col">Climate models agreeing</th>
              </tr>
            </thead>
            <tbody>
              {analogs.map((a) => (
                <tr key={a.rank}>
                  <th scope="row">{a.rank}</th>
                  <td>{a.place_name ?? '—'}</td>
                  <td>{matchScore(a.sigma)}</td>
                  <td>{a.sigma.toFixed(2)}</td>
                  <td>{agreementText(a)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {rotationAgreement.length > 0 && (
        <>
          <h4>Model agreement for the rotation options</h4>
          <ul className="small">
            {rotationAgreement.map(({ name, line }, i) => (
              <li key={i}>
                <strong>{name}:</strong> {line}
              </li>
            ))}
          </ul>
        </>
      )}

      <h4>Climate models ({models.length})</h4>
      <p className="small">{models.join(', ')}</p>

      <dl className="glossary">
        {STATISTICAL_TERMS.map((g) => (
          <div key={g.term}>
            <dt>{g.term}</dt>
            <dd>{g.meaning}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
