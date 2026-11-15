import { useCallback, useEffect, useRef, useState } from 'react';
import type { Scenario } from './types/contract';
import type { AnalogResultView } from './types/extensions';
import { API_BASE, ApiError, type BillSummary, checkHealth, fetchAnalogs, fetchBillSummary } from './lib/api';
import { DEMO_CASES, type DemoCaseId, getDemoResult } from './lib/fixtures';
import { buildAnalogRequest, EXAMPLE_FIELD, type LonLat, validatePolygon } from './lib/request';
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

function parseInitialState(): { field: LonLat[] | null; scenario: Scenario } {
  try {
    const params = new URLSearchParams(window.location.search);
    const scen = params.get('scenario');
    const scenario: Scenario = scen === 'ssp585' ? 'ssp585' : DEFAULT_SCENARIO;
    const fieldParam = params.get('field');
    if (fieldParam) {
      const coords = fieldParam.split(';').map((pt) => {
        const [lonStr, latStr] = pt.split(',');
        const lon = lonStr !== undefined ? parseFloat(lonStr) : NaN;
        const lat = latStr !== undefined ? parseFloat(latStr) : NaN;
        return [lon, lat] as LonLat;
      });
      if (coords.length >= 3 && coords.every(([lon, lat]) => Number.isFinite(lon) && Number.isFinite(lat))) {
        return { field: coords, scenario };
      }
    }
    return { field: null, scenario };
  } catch {
    return { field: null, scenario: DEFAULT_SCENARIO };
  }
}

export default function App() {
  const [initial] = useState(parseInitialState);
  const [field, setField] = useState<LonLat[] | null>(initial.field);
  const [scenario, setScenario] = useState<Scenario>(initial.scenario);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<AnalogResultView | null>(null);
  const [demoCase, setDemoCase] = useState<DemoCaseId | null>(null);
  const [selectedRank, setSelectedRank] = useState<number | null>(null);
  const [resultCount, setResultCount] = useState(0);
  const [health, setHealth] = useState<Health>(IS_STATIC ? 'static' : 'checking');
  const [billSummary, setBillSummary] = useState<BillSummary | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Sync field and scenario to URL query params so they survive reload and are shareable
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (field && field.length > 0) {
      params.set('field', field.map(([lon, lat]) => `${lon.toFixed(4)},${lat.toFixed(4)}`).join(';'));
    } else {
      params.delete('field');
    }
    if (scenario !== DEFAULT_SCENARIO) {
      params.set('scenario', scenario);
    } else {
      params.delete('scenario');
    }
    const newQuery = params.toString();
    const newUrl = newQuery ? `${window.location.pathname}?${newQuery}` : window.location.pathname;
    window.history.replaceState(null, '', newUrl);
  }, [field, scenario]);

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
    const validationError = validatePolygon(ring);
    if (validationError) {
      setError(new ApiError('validation', validationError));
      setField(null);
      setResult(null);
      setSelectedRank(null);
      setBillSummary(null);
      return;
    }
    setField(ring);
    setError(null);
    // Results belong to the previous field; don't leave them looking current.
    setResult(null);
    setSelectedRank(null);
    setBillSummary(null);
  }, []);

  const useExampleField = () => onFieldDrawn(EXAMPLE_FIELD);

  const findAnalogs = async (f: LonLat[] | null = field, s: Scenario = scenario) => {
    if (!f) return;
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
      const body = buildAnalogRequest(f, s);
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

  const handleScenarioChange = (newScenario: Scenario) => {
    setScenario(newScenario);
    // If a result is currently showing, re-run with the new scenario automatically
    if (result && field) {
      findAnalogs(field, newScenario);
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
            cancelSignal={field ? field.map((p) => p.join(',')).join(';') : `none-${loading}-${demoCase}`}
          />
          <p className="muted small">
            Use the tools at the top left of the map to draw your field:
            <br />
            • <strong>Rectangle:</strong> click and drag to draw a box (or click opposite corners).
            <br />
            • <strong>Polygon:</strong> click each corner, then click the starting corner again (or double-click) to close.
            <br />
            {IS_STATIC && (
              <>
                • <strong>Demo range:</strong> must be within 8 km of one of the 5 test fields (green boxes on the map).
                <br />
              </>
            )}
            Drawing again replaces the field. No mouse? Use “Use example field”.
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
              <button type="button" onClick={() => { setField(null); setResult(null); setSelectedRank(null); setBillSummary(null); setError(null); }} disabled={!field}>
                Clear field
              </button>
            </div>

            <label htmlFor="scenario">Emissions scenario</label>
            <select id="scenario" value={scenario} onChange={(e) => handleScenarioChange(e.target.value as Scenario)}>
              {SCENARIOS.map((s) => (
                <option key={s} value={s}>
                  {SCENARIO_LABELS[s]}
                </option>
              ))}
            </select>

            <button
              type="button"
              className="primary"
              onClick={() => findAnalogs()}
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
