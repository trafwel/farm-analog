import { useCallback, useEffect, useRef, useState } from 'react';
import type { Scenario } from './types/contract';
import type { AnalogResultView } from './types/extensions';
import { API_BASE, ApiError, type BillSummary, checkHealth, fetchAnalogs, fetchBillSummary } from './lib/api';
import { DEMO_CASES, type DemoCaseId, getDemoResult } from './lib/fixtures';
import { analyzeStatic, IS_STATIC, savedSummary, TEST_FIELDS, testFieldRing } from './lib/staticDemo';
import { buildAnalogRequest, type LonLat, validatePolygon } from './lib/request';
import { DEFAULT_SCENARIO, SCENARIO_LABELS, SCENARIOS } from './lib/scenario';
import type { PriorityId } from './lib/priorities';
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

const VALID_GOALS: PriorityId[] = ['water', 'erosion', 'organic', 'nitrogen', 'pests'];

function parseInitialState(): { field: LonLat[] | null; scenario: Scenario; goals: PriorityId[] } {
  try {
    const params = new URLSearchParams(window.location.search);
    const scen = params.get('scenario');
    const scenario: Scenario = scen === 'ssp585' ? 'ssp585' : DEFAULT_SCENARIO;
    const goalsParam = params.get('goals');
    const goals: PriorityId[] = goalsParam
      ? (goalsParam.split(',').filter((g) => VALID_GOALS.includes(g as PriorityId)) as PriorityId[])
      : [];
    const fieldParam = params.get('field');
    if (fieldParam) {
      const coords = fieldParam.split(';').map((pt) => {
        const [lonStr, latStr] = pt.split(',');
        const lon = lonStr !== undefined ? parseFloat(lonStr) : NaN;
        const lat = latStr !== undefined ? parseFloat(latStr) : NaN;
        return [lon, lat] as LonLat;
      });
      if (coords.length >= 3 && coords.every(([lon, lat]) => Number.isFinite(lon) && Number.isFinite(lat))) {
        return { field: coords, scenario, goals };
      }
    }
    return { field: null, scenario, goals };
  } catch {
    return { field: null, scenario: DEFAULT_SCENARIO, goals: [] };
  }
}

export default function App() {
  const [initial] = useState(parseInitialState);
  const [field, setField] = useState<LonLat[] | null>(initial.field);
  const [scenario, setScenario] = useState<Scenario>(initial.scenario);
  const [chosenGoals, setChosenGoals] = useState<PriorityId[]>(initial.goals);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<AnalogResultView | null>(null);
  const [demoCase, setDemoCase] = useState<DemoCaseId | null>(null);
  const [selectedRank, setSelectedRank] = useState<number | null>(null);
  const [resultCount, setResultCount] = useState(0);
  const [health, setHealth] = useState<Health>(IS_STATIC ? 'static' : 'checking');
  const [billSummary, setBillSummary] = useState<BillSummary | null>(null);
  const [cancelDrawKey, setCancelDrawKey] = useState(0);
  const [mapFocusRequest, setMapFocusRequest] = useState(0);
  const [panelFull, setPanelFull] = useState(false);

  // Esc leaves full screen.
  useEffect(() => {
    if (!panelFull) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setPanelFull(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [panelFull]);
  const abortRef = useRef<AbortController | null>(null);

  // Sync field, scenario, and rotation goals to URL query params so they survive reload and are shareable
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
    if (chosenGoals.length > 0) {
      params.set('goals', chosenGoals.join(','));
    } else {
      params.delete('goals');
    }
    const newQuery = params.toString();
    const newUrl = newQuery ? `${window.location.pathname}?${newQuery}` : window.location.pathname;
    window.history.replaceState(null, '', newUrl);
  }, [field, scenario, chosenGoals]);

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

  const findAnalogs = async (f: LonLat[] | null = field, s: Scenario = scenario) => {
    if (!f) return;
    setCancelDrawKey((k) => k + 1);
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
        const r = analyzeStatic(body);
        showResult(r, null);
        setBillSummary(savedSummary(r.field_id, r.scenario));
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

  // Bring back results on reload if a field is present in the URL. Runs once, on load only.
  // Deferred, with cleanup, so React's development double-run starts only one analysis.
  useEffect(() => {
    if (!initial.field) return;
    const timer = setTimeout(() => findAnalogs(initial.field, initial.scenario), 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleScenarioChange = (newScenario: Scenario) => {
    setCancelDrawKey((k) => k + 1);
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

  const selectedPreset = TEST_FIELDS.find((preset) => {
    const ring = testFieldRing(preset);
    return field?.length === ring.length && ring.every(([lon, lat], index) => {
      const point = field[index];
      return point && Math.abs(point[0] - lon) < 1e-6 && Math.abs(point[1] - lat) < 1e-6;
    });
  });

  const resultKey = result ? `${result.field_id}-${result.scenario}-${resultCount}` : '';

  return (
    <div className="app">
      <header className="app-header">
        <h1>Farm Forward</h1>
        <p>
          Draw your field to find places in the Pacific Northwest whose climate today is like your field's
          climate around 2050.
        </p>
      </header>

      <main className={`layout${panelFull ? ' panel-full' : ''}`}>
        <div id="field-map" className="map-column" hidden={panelFull}>
          <MapView
            hidden={panelFull}
            focusRequest={mapFocusRequest}
            testFields={IS_STATIC ? TEST_FIELDS : []}
            showDemoCoverage={IS_STATIC}
            field={field}
            onFieldDrawn={onFieldDrawn}
            analogs={result?.analogs ?? []}
            resultKey={resultKey}
            selectedRank={selectedRank}
            onSelect={setSelectedRank}
            cancelSignal={cancelDrawKey}
          />
          <details className="map-help">
            <summary>How to draw a field</summary>
            <p className="muted small">
            Use the tools at the top left of the map to draw your field:
            <br />
            • <strong>Rectangle:</strong> click and drag to draw a box (or click opposite corners).
            <br />
            • <strong>Circle:</strong> click the center, move outward, then click again to set the edge.
            <br />
            • <strong>Polygon:</strong> click each corner, then click the starting corner again (or double-click) to close.
            <br />
            {IS_STATIC && (
              <>
                • <strong>Demo range:</strong> Your field’s center must be inside one of the shaded areas, within 8 km of an example field.
                <br />
              </>
            )}
            Drawing again replaces the field.
            </p>
          </details>
        </div>

        <aside className="panel" id="side-panel">
          <div className="panel-toolbar field-heading">
            <h2 id="controls-heading">Your field</h2>
            <div className="field-heading-actions">
              <span className="small muted" aria-live="polite">
                {field ? 'Field selected' : 'No field selected'}
              </span>
              <button
                type="button"
                className="panel-full-toggle"
                aria-pressed={panelFull}
                aria-controls="side-panel"
                onClick={() => setPanelFull((v) => !v)}
                title={panelFull ? 'Show the map again (Esc)' : 'Hide the map and use the whole page for this panel'}
              >
                <span aria-hidden="true">{panelFull ? '⤡' : '⤢'}</span> {panelFull ? 'Exit full screen' : 'Full screen'}
              </button>
            </div>
          </div>
          <section className="controls" aria-labelledby="controls-heading">
            <p className="example-field">Example Fields</p>
            <div className="button-row">
              <div className="example-buttons">
                {TEST_FIELDS.map((preset) => (
                  <button
                    key={preset.id}
                    aria-pressed={selectedPreset?.id === preset.id}
                    type="button"
                    onClick={() => {
                      setCancelDrawKey((k) => k + 1);
                      onFieldDrawn(testFieldRing(preset));
                    }}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
              <button
                type="button"
                onClick={() => {
                  setCancelDrawKey((k) => k + 1);
                  setField(null);
                  setResult(null);
                  setSelectedRank(null);
                  setBillSummary(null);
                  setError(null);
                }}
                disabled={!field}
              >
                Clear field
              </button>
            </div>

            <div role="group" aria-labelledby="scenario-heading">
              <p id="scenario-heading" className="example-field">Emissions scenario</p>
              <div className="example-buttons scenario-buttons">
                {SCENARIOS.map((option) => (
                  <button
                    key={option}
                    type="button"
                    aria-pressed={scenario === option}
                    onClick={() => {
                      if (scenario !== option) handleScenarioChange(option);
                    }}
                  >
                    {SCENARIO_LABELS[option]}
                  </button>
                ))}
              </div>
            </div>

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
            {!IS_STATIC && (
              <p className={`small health health-${health}`} role="status">
                {HEALTH_TEXT[health]}
              </p>
            )}
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
              onShowOnMap={(rank) => {
                setSelectedRank(rank);
                setPanelFull(false);
                setMapFocusRequest((request) => request + 1);
              }}
              onSelect={setSelectedRank}
              billSummary={billSummary}
              chosenGoals={chosenGoals}
              onGoalsChange={setChosenGoals}
            />
          )}
        </aside>
      </main>
    </div>
  );
}
