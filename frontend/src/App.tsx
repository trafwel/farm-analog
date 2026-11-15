import { useCallback, useEffect, useRef, useState } from 'react';
import type { Scenario } from './types/contract';
import type { AnalogResultView } from './types/extensions';
import { API_BASE, ApiError, type BillSummary, checkHealth, fetchAnalogs, fetchBillSummary } from './lib/api';
import { DEMO_CASES, type DemoCaseId, getDemoResult } from './lib/fixtures';
import { buildAnalogRequest, EXAMPLE_FIELD, type LonLat } from './lib/request';
import { analyzeStatic, IS_STATIC, TEST_FIELDS, testFieldRing } from './lib/staticDemo';
import { DEFAULT_SCENARIO, SCENARIO_LABELS, SCENARIOS } from './lib/scenario';
import { MapView } from './components/MapView';
import { ResultsPanel } from './components/ResultsPanel';

type Health = 'checking' | 'online' | 'offline' | 'static';

const HEALTH_TEXT: Record<Health, string> = {
  checking: 'Checking the analysis server…',
  online: 'Analysis server is online.',
  offline: 'Analysis server is not reachable. You can still view demo data.',
  static:
    'Online demo: real Earth Engine results saved for 5 Palouse test fields. No server needed.',
};

export default function App() {
  const [field, setField] = useState<LonLat[] | null>(null);
  const [scenario, setScenario] = useState<Scenario>(DEFAULT_SCENARIO);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<AnalogResultView | null>(null);
  const [demoCase, setDemoCase] = useState<DemoCaseId | null>(null);
  const [selectedRank, setSelectedRank] = useState<number | null>(null);
  const [resultCount, setResultCount] = useState(0);
  const [health, setHealth] = useState<Health>(IS_STATIC ? 'static' : 'checking');
  const [billSummary, setBillSummary] = useState<BillSummary | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (IS_STATIC) return;
    let live = true;
    checkHealth().then((ok) => live && setHealth(ok ? 'online' : 'offline'));
    return () => {
      live = false;
    };
  }, []);

  const showResult = useCallback((r: AnalogResultView, demo: DemoCaseId | null) => {
    setResult(r);
    setBillSummary(null);
    setDemoCase(demo);
    setSelectedRank(null);
    setResultCount((n) => n + 1);
  }, []);

  const onFieldDrawn = useCallback((ring: LonLat[]) => {
    setField(ring);
    setError(null);
    // Results belong to the previous field; don't leave them looking current.
    setResult(null);
    setSelectedRank(null);
    setBillSummary(null);
  }, []);

  const useExampleField = () => onFieldDrawn(EXAMPLE_FIELD);

  const findAnalogs = async () => {
    if (!field) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setError(null);
    // Clear the previous answer so an error (or a different scenario) is never shown next to
    // results that were computed for other settings.
    setResult(null);
    setSelectedRank(null);
    try {
      const body = buildAnalogRequest(field, scenario);
      if (IS_STATIC) {
        showResult(analyzeStatic(body), null);
        return;
      }
      const r = await fetchAnalogs(body, { signal: ctrl.signal });
      showResult(r, null);
      // Bill's summary is optional and arrives after the result; a newer search cancels it.
      fetchBillSummary(r, { signal: ctrl.signal }).then((b) => {
        if (abortRef.current === ctrl) setBillSummary(b);
      });
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      setError(err instanceof ApiError ? err : new ApiError('bad_response', (err as Error).message));
    } finally {
      if (abortRef.current === ctrl) setLoading(false);
    }
  };

  const showDemo = (id: DemoCaseId) => {
    setError(null);
    showResult(getDemoResult(id), id);
  };

  const resultKey = result ? `${result.field_id}-${result.scenario}-${resultCount}` : '';

  return (
    <div className="app">
      <header className="app-header">
        <h1>Farm Analog</h1>
        <p>
          Draw your field to find places in the Pacific Northwest whose climate <em>today</em> is like your field's
          climate around 2050.
        </p>
      </header>

      <main className="layout">
        <div className="map-column">
          <MapView
            testFields={IS_STATIC ? TEST_FIELDS : []}
            field={field}
            onFieldDrawn={onFieldDrawn}
            analogs={result?.analogs ?? []}
            resultKey={resultKey}
            selectedRank={selectedRank}
            onSelect={setSelectedRank}
          />
          <p className="muted small">
            Use the polygon or rectangle tool at the top left of the map to draw your field. Drawing again replaces it.
            No mouse? Use “Use example field”.
          </p>
        </div>

        <aside className="panel">
          <section className="controls" aria-labelledby="controls-heading">
            <h2 id="controls-heading">Your field</h2>
            <p className="small" aria-live="polite">
              {field ? `Field set (${field.length} corners).` : 'No field yet: draw one on the map or use the example.'}
            </p>
            <div className="button-row">
              <button type="button" onClick={useExampleField}>
                Use example field
              </button>
              {IS_STATIC && (
                <select
                  aria-label="Try a test field"
                  value=""
                  onChange={(e) => {
                    const f = TEST_FIELDS.find((t) => t.id === e.target.value);
                    if (f) onFieldDrawn(testFieldRing(f));
                  }}
                >
                  <option value="">Try a test field…</option>
                  {TEST_FIELDS.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.label}
                    </option>
                  ))}
                </select>
              )}
              <button type="button" onClick={() => setField(null)} disabled={!field}>
                Clear field
              </button>
            </div>

            <label htmlFor="scenario">Emissions scenario</label>
            <select id="scenario" value={scenario} onChange={(e) => setScenario(e.target.value as Scenario)}>
              {SCENARIOS.map((s) => (
                <option key={s} value={s}>
                  {SCENARIO_LABELS[s]}
                </option>
              ))}
            </select>

            <button
              type="button"
              className="primary"
              onClick={findAnalogs}
              disabled={!field || loading}
              aria-describedby={!field ? 'find-hint' : undefined}
            >
              {loading ? 'Finding analogs…' : 'Find analogs'}
            </button>
            {!field && (
              <p id="find-hint" className="muted small">
                Set a field first.
              </p>
            )}
            <p className={`small health health-${health}`} role="status">
              {HEALTH_TEXT[health]}
            </p>
          </section>

          {error && (
            <div className="banner banner-error" role="alert">
              <p>
                <strong>{error.message}</strong>
              </p>
              {error.details.length > 0 && (
                <ul>
                  {error.details.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              )}
              {!IS_STATIC && error.kind === 'network' && (
                <p className="small">Is the backend running at {API_BASE}? You can look at demo data instead.</p>
              )}
              {!IS_STATIC && (
                <button type="button" onClick={() => showDemo('fake-colfax')}>
                  Show demo data
                </button>
              )}
            </div>
          )}

          {!IS_STATIC && !error && !result && (
            <p className="small">
              No server handy?{' '}
              <button type="button" className="link" onClick={() => showDemo('fake-colfax')}>
                Show demo data
              </button>
            </p>
          )}

          {demoCase && (
            <fieldset className="demo-toggle">
              <legend>Demo example</legend>
              {DEMO_CASES.map((c) => (
                <label key={c.id}>
                  <input
                    type="radio"
                    name="demo-case"
                    value={c.id}
                    checked={demoCase === c.id}
                    onChange={() => showDemo(c.id)}
                  />
                  {c.label}
                </label>
              ))}
            </fieldset>
          )}

          {result && (
            <ResultsPanel
              result={result}
              selectedRank={selectedRank}
              onSelect={setSelectedRank}
              billSummary={billSummary}
            />
          )}
        </aside>
      </main>
    </div>
  );
}
