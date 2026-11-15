# Milestone Reviews

One self-review per milestone, written before the teach-back. See rule 3 in [HOW_WE_BUILD.md](HOW_WE_BUILD.md).

Template:

```
## M# — <name> (<date>)

### Efficiency
### Integration (what was run and checked)
### Security and privacy
### Other flaws
### Fixed in this milestone
### Moved to OPEN_ISSUES.md
```

---

## M0 — Foundation (2026-11-14)

**Built:** `pyproject.toml` (package, pytest, ruff), `environment.yml` additions (pydantic, pytest, ruff, editable install), `config.py` (all periods, thresholds and limits in one place), `schema.py` (the JSON contract as Pydantic models), `contract.py` + `contract/*.schema.json` (JSON Schema export for the frontend), `fixtures.py` + `fixtures/fake_results.json` (fake data), two scripts, 24 tests, backend CI, `docs/CONTRACT.md`.

### Efficiency
- The fixture is 44 KB and the schemas 16 KB: fine to load in the browser and to commit.
- Fixture generation is deterministic and runs in under a second; nothing is computed twice.
- **Issue:** CI installs the full environment (Earth Engine, Jupyter, Streamlit, geospatial stack) just to run lint and unit tests. Cached after the first run, but the first run is slow. Logged in OPEN_ISSUES.

### Integration (what was run and checked)
- Built the real `farm-analog` conda environment from `environment.yml` with mamba: succeeded. This is the first time SETUP.md's steps were actually run.
- SETUP.md import check: passes (including `farm_analog` via the editable install).
- `ruff check .`: passes. `pytest`: 24 passed.
- The committed fixture loads into the contract models, and both committed artifacts (fixture, JSON Schemas) match what the scripts regenerate; tests enforce this.
- The existing `sigma_dissimilarity()` now has tests and still passes.
- **Not checked:** the CI workflow itself (it only runs on a pull request, which isn't opened yet), and generating TypeScript types from the JSON Schemas (the frontend doesn't exist until M6). Both logged.

### Security and privacy
- No secrets added. The fixture has no real farms or people: invented numbers, place names "Example area N", and every result marked `source: "fixture"`.
- The request contract validates untrusted input before any processing: polygon type, closed rings, at least 4 positions, coordinate ranges, finite numbers, a 1,000-vertex limit, `top_n` between 1 and 100, and unknown fields rejected. This blocks malformed or oversized input reaching Earth Engine in M5.
- **Not yet covered:** a field outside the supported area, or a huge valid polygon (for example covering a whole state). Area and region checks belong in M5, where the request is handled. Logged.

### Other flaws
- `Position` accepts only 2 numbers per point. GeoJSON allows an optional third (altitude); Leaflet drawing doesn't produce it, so this is fine for now. Logged as won't fix.
- `novel_climate` is defined as "the best analog's median sigma is 4 or more". Earlier docs said "above 4 for most models". The contract now fixes one definition; the team should confirm it. Logged as a team decision.
- Self-intersecting polygons pass validation. Earth Engine tolerates them, but the field area would be wrong. Logged for M5.

### Fixed in this milestone
- A line over the length limit in `contract.py` (caught by ruff).
- SETUP.md's check now runs `ruff check . && pytest` instead of launching the Streamlit placeholder.
- SETUP.md no longer keeps a second copy of `environment.yml`, which had already drifted from the real file.

### Moved to OPEN_ISSUES.md
CI speed, CI not yet run, TypeScript generation untested, region and area checks, self-intersecting polygons, the novel-climate definition, the Streamlit placeholder and dependencies, the Anthropic SDK vs. Gemini, the outdated plan documents, and 3-D coordinates.


### Addendum: rebase onto the team's new main (2026-11-14)

`main` gained three teammate commits (SMAP and ECOSTRESS importers, a first 2050 climate download, Streamlit preview updates). M0 was rebased onto it with no conflicts; 24 tests still pass.

**Lint fix for the new files.** M0's CI lint check failed on the new files (30 long lines, 1 semicolon statement, 3 `timezone.utc`, 1 import order). Fixed by `ruff check --fix`, `ruff format` on those four files, and splitting long text strings into adjacent pieces (Python joins them, so the text is unchanged).

**Proof it's format-only:** compared each file's syntax tree with the version on `main`. `app/app.py` is identical. `climate.py` and `data.py` differ only by `timezone.utc` → `datetime.UTC`, which are the same object in Python 3.11 (checked). `ecostress.py` additionally differs by the order of two `import` lines inside a function. The Streamlit preview runs with no exceptions and shows all four sections (checked with Streamlit's `AppTest`).

**New open items** (in OPEN_ISSUES.md): `climate.py` vs. what M2 needs, the time-period mismatch, no tests for the importers, the Palouse box defined twice, and `data.py` naming.

### Addendum 2: rebase onto the team's analog search (2026-11-14)

`main` moved again: a first analog search (`search.py`), stronger input checks in `analogs.py`, new tests and an analog section in the Streamlit preview. Replayed M0 onto it, rehearsed first in a throwaway copy:

- **Conflict:** `tests/test_analogs.py` (created on both sides). Merged: the team's tests plus M0's finite-distance test.
- **Format-only lint fix redone** for `app/app.py`, `analogs.py`, `climate.py`, `data.py`, `ecostress.py`, `search.py` and `tests/test_analogs.py`, replacing the earlier format commit (which conflicted with the new app code). One URL line is exempted with `# noqa: E501`.
- **Proof it's format-only:** a syntax-tree comparison against the team's versions, allowing only `timezone.utc` → `datetime.UTC` (same object), import order, and `zip(..., strict=False)` (the default). All seven files are identical under those rules. The checker was itself tested: a one-number change to a test file is correctly flagged.
- **Found on `main`:** leftover merge-conflict markers in `README.md`. Removed (marker lines only).
- **Checks:** `ruff check .` passes; `pytest` passes (25 tests: 3 analog tests + 22 contract and fixture tests).

## M1 — Farm today (2026-11-14)

**Team decisions going in:** M0 understanding confirmed in chat; use the team's 8-value quarterly fingerprint; use IPCC AR6 periods (1995–2014 → 2041–2060).

**Built:** `fingerprint.py` (the one fingerprint definition, contract conversion), `farm_today.py` (PRISM for a drawn field via Earth Engine, then offline-testable processing into the normal fingerprint and 20 yearly fingerprints), contract switched to 8 values (`tmean_*`, `ppt_*`) and monthly `tmean` for the climograph, fixture and JSON Schemas regenerated, `config.py` on AR6 periods with PRISM settings and the Palouse box, `search.py` refactored to use all of these, 20 new tests (44 total).

### Efficiency
- `fetch_prism_monthly` makes one Earth Engine request for all 240 months (a mapped list, one `getInfo`), not one per month.
- `search.py` now skips Earth Engine login entirely when its cache exists. Before, every run logged in even though nothing was downloaded.
- The fingerprint is computed in one pass per year; nothing is computed twice.

### Integration (what was run and checked)
- `ruff check .` passes; `pytest`: 44 passed.
- **Regression:** `test_search.py` reruns the team's search from the committed cache into a temp folder; the 784 rankings and the summary (except its timestamp) match the committed files exactly. The refactor changed no results.
- The feature names and order match the team's cache (test), so the cache and committed CSV keep working.
- The fixture still loads and passes the contract's consistency rules; JSON Schemas regenerated; drift tests pass.
- Streamlit preview: runs with no exceptions, all 5 sections render (AppTest).
- `tests/test_schema.py` was touched by the formatter only (syntax trees identical).
- **Not run:** the live Earth Engine download for a field. There are no Earth Engine credentials on this machine. Logged for a teammate who has them.
- **Breaks M9:** Bill's summarizer reads the old field names. Logged; M9 updates after M1 merges.

### Security and privacy
- The field polygon goes only to Earth Engine (needed to compute its climate) and is not logged or written to disk by `farm_today.py`.
- `farm_today_for_field` takes a validated `PolygonGeometry` (closed rings, coordinate ranges, vertex limit from M0), never raw input.
- No new secrets; `EE_PROJECT` still comes from `.env`.

### Other flaws
- **Fields smaller than a PRISM cell** (most fields) take the value of the cell under their center. That's reported as `support = "centroid_cell"` rather than hidden. Field-level detail beyond ~4 km isn't possible with PRISM.
- **"Today" means 1995–2014**, not the last few years. That's the AR6 convention the team chose; the UI should say "recent decades", not "now".
- **Mean temperature only:** the 8-value fingerprint drops highs and lows, so frost and heat extremes aren't in the match. Hazards (M7) should cover extremes separately.
- **A field spanning very different cells** (rare for a field) gets one averaged fingerprint.

### Fixed in this milestone
- Time periods and fingerprint definitions now agree across settings, contract and code (two team-decision items resolved).
- The Palouse box is defined once.
- `search.py` can run offline from its cache and write to a chosen folder.

### Moved to OPEN_ISSUES.md
Live Earth Engine test for fields, Bill's summarizer field names (M9), two different search areas (M3), the delta applied to the regional mean instead of the farm (M2).

## M2 — Farm in 2050 (2026-11-14)

**Team decisions going in:** M1 understanding confirmed in chat; order chosen as M2 → M3 → M4, one per round.

**Built:** `future.py` (quarterly change per model, delta method onto the farm's normal fingerprint, `FarmFuture` with per-model futures plus median, low and high; Earth Engine fetch of a model's monthly climatology at the field), `earthengine.py` (login, field polygon, field averaging with the center-cell fall-back, now shared with M1), `config.CLIMATE_MODELS` (8 models spanning cooler- to warmer-running), `search.py` switched to the shared delta functions, 12 new tests (56 total).

### Efficiency
- One Earth Engine request per model for both periods (24 monthly values in a single `getInfo`), plus one count check per period.
- Each model's change is computed once and reused for every candidate in M4, not per candidate.
- The M1 field-averaging code moved into `earthengine.py` instead of being copied into M2.

### Integration (what was run and checked)
- `ruff check .` passes; `pytest`: 56 passed.
- **Regression:** `search.py` now uses `quarterly_change` + `apply_delta`; its test still reproduces all 784 committed rankings exactly, so the shared delta matches the team's original calculation.
- **Real data:** on the team's ACCESS-CM2 sample, the quarterly change is +1.65 / +2.14 / +4.04 / +2.26 °C and rain ×1.11 / ×1.15 / ×0.79 / ×1.11 (a test checks this against a hand calculation).
- Streamlit preview: runs, all 5 sections (AppTest).
- **Not run:** the live model download (no Earth Engine credentials here), and whether all 8 models exist with an `ssp245` run in Earth Engine. Logged.

### Security and privacy
- The field polygon goes only to Earth Engine; nothing is logged or written to disk.
- Inputs are the validated `PolygonGeometry`; model names come from `config`, not user input, so they can't be used to inject filters.

### Other flaws
- **Model grid cells are about 25 km**, so the *change* is effectively regional even for a field. That's expected: the field-level detail comes from PRISM (M1); the models supply only the change.
- **`farm_future_for_field` catches every exception per model** so one bad model doesn't stop the run. The reason is kept in `failed_models` and should be shown to the team, not silently dropped.
- **Model temperature is daily mean air temperature (`tas`), PRISM's is `tmean`.** The delta method uses only the model's change, which limits the effect of the difference.

### Fixed in this milestone
- The future is built at the farm, per model, rather than only for the regional mean with one model.
- Field averaging is shared code.

### Moved to OPEN_ISSUES.md
Live model download and model availability (Earth Engine), the ensemble range in the contract (M8), `search.py` still on the regional prototype (M4).

## M3 — Candidates (2026-11-14)

**Context:** built while the team was away (they asked for M3–M7 in one go). Search area set to the recommended default (inland Northwest, ~4 km, farmland only); logged as a team decision to confirm.

**Built:** `candidates.py` (validation, farmland filter, Parquet cache with provenance, offline fallback to the team's 784-cell cache, tiled Earth Engine fetch of PRISM fingerprints plus Cropland Data Layer cultivated share), config for the search area and farmland threshold, 12 new tests (68 total).

### Efficiency
- Built once and cached; the API never re-queries Earth Engine for candidates.
- One Earth Engine request per 1° tile (25 tiles for the inland Northwest).
- The farmland share is computed by averaging 30 m CDL into each PRISM cell on Earth Engine, not downloaded at 30 m.

### Integration (what was run and checked)
- `ruff check .` passes; `pytest`: 68 passed.
- The team's committed cache converts cleanly: 784 cells, fingerprint columns in the shared order.
- Save/load round trip with provenance JSON; fallback note when the cache is missing.
- **Not run:** the Earth Engine fetch (no credentials here). Logged.

### Security and privacy
- No farm data is involved: candidates are public climate and land-cover grids.
- The cache lives in `data/` (ignored by git).

### Other flaws
- No irrigation filter yet (logged for M7).
- The fallback grid isn't farmland-filtered; results say so in their notes (M4).
- 30% cultivated is a judgment call; it's one setting in `config.py`.

### Moved to OPEN_ISSUES.md
Confirm the search area, build the candidate cache with Earth Engine, add an irrigation filter.

## M4 — Match (2026-11-14)

**Built:** `match.py` (sigma per model, median, `models_agree`, standardized-distance baseline, ranking, `to_result` in the contract, `palouse_demo` offline from the team's data), optional `notes` in `AnalogResult` (fixture and JSON Schemas regenerated), 5 new tests (73 total).

### Efficiency
- The farm's year-to-year statistics are fit once per model; all candidates are scored in one vectorized call per model.
- The full ranked table stays on the server; only the top `top_n` go into the result.

### Integration (what was run and checked)
- `ruff check .` passes; `pytest`: 73 passed.
- **Regression:** with ACCESS-CM2 on the team's cached data, M4's sigma and baseline scores equal the team's committed `palouse_analog_candidates.csv` for all 784 cells (relative tolerance 1e-12), in the same order.
- Demo result: best matches near Walla Walla (0.50σ) and Lewiston–Clarkston (0.69σ); 6 strong, 18 good, 122 weak, 638 none.
- The result round-trips through JSON and passes all contract consistency rules.

### Security and privacy
- No new inputs; matching uses already-validated data.

### Other flaws
- One model offline means `models_agree` is 0 or 1 in the demo; meaningful agreement needs the live 8-model run.
- No place names yet; no latitude check (no effect in the inland Northwest).
- The demo target is the Palouse-wide average, not a drawn field; the notes say so.

### Moved to OPEN_ISSUES.md
Place names (M7/M8), latitude check (M10), retiring `search.py` (team decision).

## M5 — API (2026-11-14)

**Built:** `pipeline.py` (mode selection, field checks with Shapely and ellipsoidal area via pyproj, live analysis chaining M1 → M2 → M3 → M4, offline Palouse demo), `api.py` (FastAPI `GET /health`, `POST /analogs`, CORS limited to `FRONTEND_ORIGINS`, in-memory cache keyed by a field hash, 400/422/503 errors), settings for the supported region and maximum field area, environment additions, 14 new tests (87 total).

### Efficiency
- Repeat requests for the same field, scenario and size are served from an in-memory cache (64 entries).
- Candidates are loaded from the cache file, not recomputed.
- Live requests are still heavy (about 10 Earth Engine jobs); logged with rate limiting.

### Integration (what was run and checked)
- `ruff check .` passes; `pytest`: 87 passed (FastAPI TestClient).
- **Started the real server** (uvicorn) and called it over HTTP: `/health` reports offline-demo mode; a Colfax field returns 3 analogs (0.50, 0.69, 0.82σ, all strong); OpenAPI lists both endpoints; the server log contains no coordinates.
- The response validates against the contract and round-trips through JSON.
- **Not run:** live mode with Earth Engine (no credentials here).

### Security and privacy
- Request bodies and coordinates are never logged (test checks the log); failures log only the exception type.
- 503 responses don't include internal error text (test).
- CORS allows only the configured frontend origin (test).
- Input limits: contract validation (vertex count, ranges), plus validity, region and area checks.
- No secrets in the API; `EE_PROJECT` comes from the server's environment.

### Other flaws
- No rate limiting yet (logged).
- The offline demo answers with the Palouse-wide result for any Palouse field, so two Palouse fields get the same analogs; the notes say the target is the regional average.
- The cache is per process and unbounded in time; fine for a demo server.

### Moved to OPEN_ISSUES.md
Rate limiting, live end-to-end test.

## M6 — Map (2026-11-14)

**Built:** `frontend/` — Vite + React 18 + TypeScript; react-leaflet with Geoman drawing (polygon or rectangle; the field shows in green; "Use example field" for keyboard and demo use); scenario select; `POST /analogs` client with plain-language errors (400 reasons, 422 field messages, network failure); demo-data fallback from the fixture with a banner; analogs as blue markers by match quality with a legend; an accessible results list; novel-climate warning; today-vs-future fingerprint table in °C/°F and mm/inches; result notes; server status from `/health`. Types generated from `contract/` (with a `prefixItems` fix). 30 frontend tests, including one that fails if the bundled demo fixture drifts from `fixtures/fake_results.json` (it already had: the copy predated M4's `notes` field, so it was refreshed). CI frontend job (install, types-up-to-date check, typecheck, lint, test, build). SETUP.md gains "Run the app". Drafted by a helper agent from a written brief, then reviewed, moved into the repo and tested end to end here.

### Efficiency
- One request per search; an in-flight search is aborted if a new one starts.
- Bundle is ~600 kB (173 kB gzipped), mostly Leaflet and Geoman; code-splitting logged for M8.

### Integration (what was run and checked)
- `pnpm install --frozen-lockfile`, `gen:types` (from the repo's real `contract/`, now including `notes`), `typecheck`, `lint`, `test` (30 passed), `build`: all pass.
- **End to end in a browser** against the real API (offline mode) and the Vite dev server: example field → Find analogs → 20 real analogs on the map between Walla Walla, Lewiston and Pullman, headline "Best match: rank 1, strong match", notes shown, server online, no console errors. Switching to high emissions shows the API's refusal ("The offline demo only covers SSP2-4.5").
- **Bug found and fixed** in that test: stale results stayed visible under an error. Now cleared at the start of each search and when the field changes; re-tested in the browser.
- The CI frontend job is new and has not run on GitHub yet (it runs on the next pull request).

### Security and privacy
- No secrets in the frontend; `VITE_API_BASE` is only the API's address.
- The field is sent only to the configured API.
- API responses get a runtime shape check before display; server text is rendered as text (React escapes it), never as HTML.

### Other flaws
- Drawing needs a mouse (example field is the keyboard route); the legend can cover markers; bundle size. Logged for M8.
- Clicking an analog doesn't open a comparison panel yet (M8).

### Moved to OPEN_ISSUES.md
Map polish and comparison panel (M8); whether to retire the Streamlit preview (team decision).

## M7 — Evidence (2026-11-14)

**Built:** `evidence.py` — pure functions (crop shares of cropland with small crops grouped, OpenLandMap soil conversion with range checks, monthly normals, the farm's future months from each model's change with the median, attaching evidence to a result, county place names) and an Earth Engine fetch for the top 3 analogs (CDL 2019–2023 within 2 km, topsoil clay/sand/organic carbon, monthly PRISM normals, TIGER county). `FarmToday.monthly` and `FarmFuture.changes` added (both optional, no behavior change). Live pipeline attaches evidence and falls back to the bare match with a note; offline results note that evidence needs Earth Engine. 10 new tests (97 total), including two that run the whole live pipeline with fakes built from real data.

### Efficiency
- Evidence only for the top 3 analogs. Soil, county and each month's normals are fetched for all 3 points in one request each; CDL is one request per year (5).
- Monthly futures reuse the per-model changes already computed in M2.

### Integration (what was run and checked)
- `ruff check .` passes; `pytest`: 97 passed.
- **Live wiring tested offline:** with Earth Engine replaced by fakes (real Palouse PRISM years, the team's real ACCESS-CM2 change, real candidates), `pipeline.analyze` in live mode returns 20 analogs with place name, crops, soil and climograph on the top 3; reports a skipped model and the centroid-cell caveat; and survives an evidence timeout with a note.
- Enriched results still pass every contract rule.
- **Not run:** the real Earth Engine fetches (no credentials). The organic-carbon unit needs checking against the catalog.

### Security and privacy
- Only analog locations (public places, not the farm) are sent for evidence.
- Failures surface only the exception type in the note, not internal messages.

### Other flaws
- Soil comes from OpenLandMap (250 m, modelled) rather than SSURGO; logged as a team decision.
- No irrigation filter yet: crops at an irrigated analog may not suit a dryland farm (open since M3).
- The frontend doesn't display the evidence yet (M8).

### Moved to OPEN_ISSUES.md
Live evidence test, organic-carbon unit check, soil source decision, showing evidence in the UI (M8).

---

## M9 — Bill (Gemini) (2026-11-14)

**Built:** `src/farm_analog/assistant/`:
- `llm.py`: the `LLM` protocol and `GeminiLLM`, the only file that imports the `google-genai` SDK.
- `guard.py`: the prompt-injection guard.
- `parser.py`: farmer text → `FarmProfile` via Gemini structured output, validated with Pydantic.
- `summarizer.py`: a summary input of derived values only, the grounding check, a template fallback, and notices written by code.

`POST /bill/parse` and `POST /bill/summary` in `api.py`. Settings in `config.py` (`GEMINI_MODEL = "gemini-3.5-flash-lite"`, minimal thinking, 20 s timeout, text and summary limits). `google-genai` is added to `environment.yml` and installed in the env, and `GEMINI_API_KEY=` is in `.env.example`. 49 new tests in `tests/test_assistant_*.py`, all using fake clients (`tests/assistant_fakes.py`); 146 tests in all. The frontend is unchanged (team instruction: M8 skipped, UI left as it was).

**Rebased onto M7.** The summarizer now reads the 8-value fingerprint: each quarter's average temperature (`tmean_jfm` ...) and precipitation (`ppt_jfm` ...), today, future and change. It also passes the result's own `notes` to Gemini as caveats, and uses `place_name` and `crops` when M7 supplies them.

### Efficiency
- One Gemini call per farmer message and one per new result. The summary input is about 2.2 KB (roughly 600 tokens): derived values for the top 5 analogs, not the full result.
- Summaries are cached in memory by a SHA-256 of the result JSON (64 entries, the same limit as `/analogs`). A template fallback caused by a Gemini failure is not cached, so the next request tries again.
- Thinking is set to minimal: Bill restates, so reasoning tokens would be wasted (and against the rule).

### Integration (what was run and checked)
- `ruff check .` passes. `pytest` gives 146 passed, with no network: the fakes replace both the `LLM` protocol and the `genai.Client`, and `/analogs` runs in offline-demo mode.
- Each of the 5 M9 commits was checked on its own: the settings and package commits with the 97 M1–M7 tests, the test commit with 135, the API commit with 146.
- End to end through the API: `POST /analogs` (offline Palouse demo) → `POST /bill/summary` gives a template summary with the quarterly temperatures, the precipitation change and the 5 closest cells, and no demo notice (the result is `computed`). On the fixtures, `fake-colfax` gets the demo notice, and `fake-lind` gets the demo and no-match notices.
- Contract unchanged: `contract/*.schema.json` doesn't mention `ParseResult` or `BillSummary` (a test checks this), so the frontend's generated types and CI's types-in-sync check are untouched. Bill's models appear only in the API's OpenAPI schema.
- `cdl.py` (the team's CDL importer on `main`) isn't on the M1–M7 stack, which was built on an older M0. No M9 commit touches it. A test merge of `m9-bill` with `m0-foundation` keeps it.
- **Not checked:** a live Gemini call. There's no `GEMINI_API_KEY` in `.env`, so the model id and the `MINIMAL` thinking level are unverified. If either is rejected, every summary falls back to the template. That's safe, but Bill's prose never appears.

### Security and privacy
- **Location privacy:** the summary input carries no polygon and no coordinates (farm or analog). A test checks for `lon`/`lat`/`coordinates` keys and for the analogs' coordinate values. The endpoints never log the request; a test checks the logs for farmer text and analog coordinates.
- **Secrets:** `GEMINI_API_KEY` is read on the server only, once at startup. Nothing reaches the frontend bundle.
- **Prompt injection, farmer text:** the text is cleaned (Unicode-normalized; control characters and `farmer_text` look-alike tags removed), capped at 2,000 characters (and at 10,000 by the endpoint), and wrapped in a block with a random id. The reply must match a strict schema. Farmer text never reaches the summarizer.
- **Prompt injection, result text:** `POST /bill/summary` accepts an `AnalogResult` from the browser, so place names, crop names and notes are untrusted too. They're cleaned and capped (80, 40 and 300 characters), the prompt says they're data, and the grounding check still applies. The worst case: a client changes the wording of its own summary.
- **No leaks through errors:** SDK exceptions are reduced to the error type and status code, and the chained exception is dropped. Parser errors never echo the reply.
- **Data use:** on Gemini's free tier, Google may use prompts to improve its products. Logged as a team decision.

### Other flaws
- **The grounding check checks numbers, not claims.** For example, "a strong match" for a weak one passes. Whole numbers within 0.5 of any input value pass, spelled-out numbers aren't checked, and the advice filter is a word list. The demo and no-match warnings are written by code, so they can't be dropped. Logged.
- **No rate limit on Bill's endpoints,** like `/analogs` (M5). Each uncached summary or parse is a paid call. Logged with M5's item.
- `/bill/parse` without a key returns `ok: false` with a clear message. It doesn't fall back to any rule-based parsing.

### Fixed in this milestone
- The parser prompt first asked Gemini to convert hectares to acres, which is arithmetic. Now any size that isn't in acres goes to `unparsed_notes` as written.
- The number pattern first skipped digits attached to letters ("SSP2", "37bu"). Now every digit run is checked.
- Template wording: "(none match)" became "(no real match)", and "1 climate model projects" is now singular.
- [M1 → M9] Old fingerprint names: switched to `tmean_*` / `ppt_*` during the rebase.
- [M9 → M5] Bill wasn't reachable from the app: the two endpoints, startup setup and summary cache are now built.

### Moved to OPEN_ISSUES.md
The live Gemini check, wiring the UI to Bill (and rendering his text as plain text), Bill's models in the contract (deferred), rate limiting, how strict grounding should be, and free-tier data use.

---

## M10 — Proof (2026-11-14)

_M8 (comparison panel) was skipped for now at the user's request: no UI changes in this round._

**Built:** `proof.py` with three checks.
- **Self-check:** match the farm today against every place today; its own area should come out as a strong match.
- **Sigma vs. baseline:** Spearman correlation and top-20 overlap between the sigma ranking and the plain standardized distance, plus model agreement on the top analogs.
- **Backtest:** analogs for each test cell's 2019–2023 climate among every cell's 2008–2012 climate; crop-mix similarity (1 − Bray–Curtis) of those analogs' 2008–2012 crops with the test cell's 2019–2023 crops, against random farmland cells and against "nothing changed". Cells within 25 km are excluded so an analog can't just be a neighbor.

Also: the day-length check (`candidates.near_latitude`, `config.MAX_LATITUDE_DIFF_DEG` = 5°) in the live pipeline, with a note when places are skipped. `python -m farm_analog.proof` writes `data/proof/proof.json` (ignored by git). 8 new tests (155 total, on top of M9).

The "more climate models with an agreement count" and "standardized-Euclidean baseline" parts of M10 were already built in M2 and M4; M10 measures them.

### Results on the team's data (offline Palouse demo)
- **Self-check passes.** Of 784 cells, the best match for the Palouse today is a Palouse cell (≈0σ). All 28 Palouse cells are good matches (median 0.16σ; 82% strong); elsewhere the median is 3.2σ.
- **Sigma barely differs from the plain baseline here:** Spearman 0.997, and 17 of the top 20 are the same. With one model and a small regional grid, the PCA whitening changes little. Sigma's advantage (correlated variables, the farm's own variability) is expected to show more on the full farmland grid with 8 models; re-measure live before claiming it.
- **Model agreement** is trivially 1/1 offline (one model). The live run reports it for 8.
- **Backtest not run** (needs Earth Engine). Its arithmetic is tested with a synthetic grid where crops follow climate: analogs score 1.0, "nothing changed" scores 0.

### Efficiency
- The backtest fetches crops only for the cells it needs (test cells, their analogs and random draws), in chunks of 500 points, instead of for every cell.
- The two candidate fetches (then and now) reuse M3's tiled `fetch_candidates`.

### Integration (what was run and checked)
- `ruff check .` passes; `pytest`: 155 passed. `python -m farm_analog.proof` runs offline and prints the numbers above.
- The live pipeline test now also checks that far-latitude places are skipped with a note.
- **Not run:** the backtest and the live model-agreement numbers (no Earth Engine credentials).

### Security and privacy
- The proof uses only candidate cells (public places), never a farmer's field.

### Other flaws
- The backtest periods are short (5 years each, because CDL starts in 2008 here) and only 11 years apart, so climate shifted little; "nothing changed" may beat the analogs. That would be an honest result, not a bug: report all three numbers.
- The test cells' own year-to-year variation comes from 1995–2014, not from the "then" period (too short for 8 features).
- Crop mix is measured within half a cell (2 km) of each cell center, not over the whole 4 km cell.

### Moved to OPEN_ISSUES.md
Run the backtest live; re-measure sigma vs. baseline with 8 models; the comparison panel (M8) is still to do.

---

## M11 — Live run + saved demo (2026-11-15)

**Built:** the first live run with Earth Engine (project in `.env`, never committed).
- **Candidate cache:** 3,351 farmland cells (~4.6 km PRISM cells, at least 30% cultivated, CDL 2019–2023) in `data/candidates/` (gitignored).
- **`saved.py`:** runs the 5 test fields live for both scenarios and saves each result to `data/samples/live_<field>_<scenario>.json`, committed. In offline mode, a field within 8 km of a test field gets that saved result, with a first note saying whose field it was computed for. Other Palouse fields still get the regional demo.
- **`config.TEST_FIELDS`:** the 5 fields, moved onto cropland. 4 of the 5 guide points were towns or station buildings (0–26% cultivated within 250 m). Each moved to the nearest spot, within about 1 km, that was ≥97% cultivated in 2016–2023.
- **Offline demo pinned:** `candidates.team_candidates()` keeps the offline Palouse demo, and its regression tests, on the team's grid even when the 4 km cache exists.
- **`config.PRISM_DATASET_TYPES`:** Earth Engine labels PRISM from 2021 on `AN91`, and the backtest needs 2019–2023.

**Bugs the live run found** (none were catchable offline):
1. `reduce_field` negated a server-side Boolean.
2. The CDL mean had no projection.
3. CDL class names arrive as one comma-separated string.
4. Candidates were sampled at 4 km on a 4.6 km grid, so some cells appeared twice.
5. PRISM's 2021+ months were filtered out.

Fixes 1–4 were made and committed by the parallel session (`883d184`, `afe6be2`); fix 5 is here.

### Live results (5 test fields, ~400 m squares, 8 models)

| Field | Jul–Sep °C, today → 2041–2060 (SSP2-4.5) | Best matches, SSP2-4.5 | Best, SSP5-8.5 |
|---|---|---|---|
| Cook (Pullman) | 17.7 → 20.3 | Whitman Co. WA 0.30σ, Garfield 0.35, 0.37 (8/8) | Whitman 0.71 (8/8) |
| Colfax | 18.3 → 21.0 | Whitman 0.31, Walla Walla 0.35, 0.38 (8/8) | Walla Walla 0.69 (8/8) |
| LaCrosse | 20.0 → 22.6 | Garfield 0.49, 0.50, Walla Walla 0.57 (8/8) | Garfield 1.09 (5/8) |
| Lind | 20.0 → 22.6 | Gilliam Co. OR 0.48, 0.51, Sherman Co. OR 0.56 (8/8) | Gilliam 1.10 (5/8) |
| Dayton | 19.6 → 22.3 | Walla Walla 0.36, 0.37, 0.39 (8/8) | Walla Walla 1.02 (6/8) |

- **The analogs stay in the inland Northwest,** answering the spec's first open question. Lind's go south across the Columbia into Oregon. Under SSP5-8.5 the matches weaken to "good" and fewer models agree, as expected.
- **Cross-check:** the parallel session ran the same fields at slightly different points (1 km squares) and got the same counties and sigmas within about 0.03.
- **Backtest, live** (200 test cells, 2008–2012 → 2019–2023, neighbors within 25 km excluded): crop-mix similarity is 0.529 for analog areas, 0.517 for random farmland and 0.818 for the cell's own past. Analogs beat random cells in 57% of test cells. **Weak.** Over 11 years, climate alone says little about crop mix in a wheat-dominated region. A place's own past says much more, as the M10 review expected.

### Efficiency
- Building the cache takes about 2.5 minutes (25 one-degree tiles). One field takes 30–70 s for M1–M4, about 10 s for evidence, about 5 s for rotations and about 35 s for hazards. The 10 saved results took about 25 minutes in all.
- Offline mode reads one ~30 kB JSON file per request.

### Integration (what was run and checked)
- `ruff check .` passes, and `pytest` passes: 186 tests.
- Frontend: types regenerated, typecheck, lint and 30 tests pass. Only the generated types and the demo-data copy changed.
- New tests:
  - saved results: nearest test field, radius, missing scenario;
  - the API serving a saved result for both scenarios;
  - the regional demo for fields away from the test fields;
  - the pipeline's rotation and hazard steps, with fakes, including both failing.
- `python -m farm_analog.proof` was run live; its numbers are above.

### Security and privacy
- `.env` (the Earth Engine project) stays gitignored.
- Saved results describe the team's own test points, not any farmer's field.

### Other flaws
- Saved results go stale when the pipeline changes. Rerun `python -m farm_analog.saved`; the date is recorded in `data/samples/live_results.json`.
- Sigma vs. the plain baseline hasn't been re-measured on a live 8-model table yet.

### Moved to OPEN_ISSUES.md
The weak backtest, the live sigma-vs-baseline check, saved results going stale, Owen's new importers on `main`, and the organic-carbon step size.

---

## M12 — Rotation strategies (2026-11-15)

**Built:** `rotations.py`. Cropland Data Layer crops for 2016–2023 are sampled at 400 random 30 m pixels in the field and in a 2 km circle around each of the top 5 analogs.
- Each pixel's sequence becomes a rotation: a repeating 1–4-year cycle, or a "flexible mix" of its main crops.
- **`strategies`:** puts the field's current rotation first, then the analog areas' rotations used on ≥10% of an area's cropland, then rarer ones (labelled thin evidence) to reach at least 3.
- Each strategy carries why, evidence (share of analog cropland, analog areas using it, model agreement), benefits and risks (from a fixed crop-traits table), and gaps, ending with "check with your county extension agent".
- All text is written by code; no LLM is involved.
- The contract gains `RotationStrategy` and `AnalogResult.rotations`.

### What the live results show
- **Lind:** grows a flexible wheat–fallow mix; its Oregon analogs grow winter wheat → fallow on 94–95% of cropland.
- **Colfax:** its current winter wheat → barley → pulses rotation appears in none of its analog areas. They use flexible fallow mixes and winter wheat → spring wheat → pulses.
- **Cook and Dayton:** the analog areas lean toward rotations with fallow.

The drier 2050s analogs rotate with more fallow. This is an observed pattern, not advice.

### Efficiency
- One batched sample per area (6 requests), about 5 s per field.

### Integration
- 9 rotation tests: crop groups; cycles across start years and gap years; flexible mixes; shares; current-first ordering; rare fill-ins; contract validity.
- Live check on all 10 saved results; each has 3–4 strategies.

### Bugs found and fixed during the live check
- A gap year shifted the cycle's order ("Winter wheat → Winter wheat").
- Wheat-twice cycles read "Winter wheat → Fallow → Winter wheat".
- Lind had only 2 strategies.

### Other flaws
- CDL label errors, only 8 years of history, and general (not local) crop traits; see OPEN_ISSUES.
- Earth Engine's seeded sampling isn't exactly repeatable, so shares can move a point or two between runs.

---

## M13 — Hazards and field conditions (2026-11-15)

**Built:** `hazards.py`, written by a helper agent from a brief and then reviewed and integrated here.
- Pure functions: heat days, frost dates, extreme-rain days, monthly soil moisture, bare months, `compare`.
- Earth Engine fetchers, each failing on its own, run in parallel:
  - PRISM daily tmax/tmin, 1995–2014;
  - NASA GPM IMERG V07, 2014–2023, as UTC daily sums;
  - NASA SMAP L4 root-zone moisture, 2016–2023;
  - Landsat 8/9 NDVI within 200 m, 2019–2023.
- `add_hazards` attaches `farm_hazards` and `hazards` to the top 3 analogs. Only source names (not error text) go into the result.
- The contract gains `Hazards`.

### What the live results show (SSP2-4.5, farm today vs. its best analog)

| Field | Heat days > 32 °C per year | Frost-free days | Farm's bare months (NDVI < 0.25) |
|---|---|---|---|
| Cook | 18 → 28 | 150 → 186 | Jan–Mar, Aug–Dec |
| Colfax | 23 → 31 | 155 → 191 | Sep–Oct |
| LaCrosse | 37 → 42 | 165 → 199 | Jul–Nov |
| Lind | 32 → 32 | 164 → 192 | most of the year (wheat–fallow) |
| Dayton | 27 → 37 | 172 → 211 | Sep–Oct |

### Efficiency
- About 35 s per field: 18 Earth Engine requests in parallel.
- IMERG and SMAP were split by year and by quarter to stay under Earth Engine's memory limit.

### Integration
- 14 hazard tests (11 from the helper agent, 3 for the contract adapter).
- Pipeline tests with faked fetchers.
- Live on all 10 saved results; no source failed.

### Other flaws
- Different periods per source, coarse grids, the deprecated `AN81d` asset, UTC days for IMERG, and a fixed NDVI threshold; see OPEN_ISSUES.
- The UI doesn't show hazards or rotations yet (M8).

### Moved to OPEN_ISSUES.md
All of the above, plus showing rotations and hazards in the UI (M8).

---

## M8 — Comparison panel, rotation cards and hazard outlook (2026-11-15)

**Built:** the frontend now shows what M7, M12 and M13 compute. Below the headline and caveats, the results panel has:
- **Rotation options** (`RotationCards`): one card per strategy, with the field's current rotation first and marked "Your field now". Each card gives its share of analog-area cropland and how many analog areas use it. Why, evidence, benefits, risks and gaps open on request. The intro states plainly that these are observed practice, not recommendations.
- **Compare with this place** (`PlaceComparison`): the selected match, or rank 1 by default, with:
  - a monthly climate chart (`ClimateChart`): temperature lines and precipitation bars for the field today, the field in the 2050s, and the place today, plus a table version;
  - its crop shares as bars;
  - its topsoil;
  - a hazard outlook table: hot days, frost-free season, last and first frost, heavy-rain days, wettest day and bare months, the field today against the place today, with differences and sources.
- **In plain words** (`BillSummaryCard`): Bill's summary from `POST /bill/summary`, fetched after each result and shown as plain text, with a label saying whether a template or Gemini wrote it. It's optional: a failure just leaves it out.
- **Words used here** (`Glossary`): analog, sigma, model agreement, SSP2-4.5 and SSP5-8.5, NDVI, frost-free season, fallow and nitrogen-fixing, plus a closing reminder to check with local experts.

Pure helpers in `lib/hazards.ts`: day of year to a date, month ranges, hazard comparison rows. The charts are hand-written SVG; no new dependencies.

### Integration (what was run and checked)
- Frontend: typecheck, lint, 39 tests (9 new) and build pass. A new test renders the real saved Cook result (`data/samples/live_cook_ssp245.json`) and checks:
  - rotation cards with the current rotation first;
  - the comparison following the selection;
  - the hazard numbers (18 → 28 hot days);
  - the fallback text for places without details;
  - Bill's text staying plain text;
  - demo data hiding the new sections.
- Backend unchanged: 186 tests pass.
- **In the browser** (offline API serving the saved Colfax result for the example field), all sections render with no console errors:
  - rotation cards: the current rotation, winter wheat → barley → pulses, appears in none of the analog areas;
  - the chart: Whitman County's climate today follows the field's 2050s line;
  - the hazard outlook: 23 → 31 hot days, frost-free season +36 days.
- No horizontal scrolling at phone width (375 px).

### Fixed during the browser check
- The temperature chart's gridlines stopped below the summer peak (20 vs. 21 °C). Gridlines now always cover the data, with a test.
- Bill's long summary pushed the rotation cards far down. It now sits below the match list.

### Other flaws
- The farm's own soil isn't fetched yet (`evidence.add_evidence` passes no `farm_soil`), so the soil table shows only the place.
- The JavaScript bundle is ~620 kB, mostly Leaflet and Geoman; code-splitting is still open from M6.
- The panel is long. Collapsible sections or tabs would help on phones.

### Moved to OPEN_ISSUES.md
The farm's own soil, the panel length on phones, and the uncertainty band (still open from M2).

---

## M15 — Submission package (2026-11-15)

**Built:** `docs/SUBMISSION.md`, the text for each field of the Space Apps project form: project name, summary, detailed description, use of SI, NASA data with links, partner data (none) and references. It follows the Judging & Awards Guide's rules: a demo of at most 7 slides or a 30-second video, English throughout, every outside resource referenced, and a description of how SI tools were used. The demo itself is left to the team.

**Checked:** every number in the summary comes from the saved live results, the M11 review or the proof output.

**For the team before submitting (see OPEN_ISSUES):** make the demo, add its link and any deployed link, read SUBMISSION.md once, and submit before 11:59 p.m. local time.

---

## M16 — SMAP soil moisture on screen (2026-11-15)

**Built:** the 12 monthly SMAP root-zone soil-moisture values that M13 already saves for the field and each top match are now shown. Frontend only; no Earth Engine run and no contract change.
- **Hazard table row:** "Soil water in the driest month (top 1 m, % by volume)", e.g. Colfax 18.9% (Sep) vs. Whitman County 21.1% (Sep), +2.2 points. Helpers `driestMonth` and `soilWaterPct` in `lib/hazards.ts`.
- **Chart** (`SoilMoistureChart`): soil water by month, field vs. the selected match, same colors as the climate chart, gaps for missing months instead of bridging them, and a table version.
- **Source note** under the hazard table and a glossary entry saying it's a ~9 km grid-cell average, not a reading from the field.

### Why these choices
- **Driest month, not the yearly mean:** late-summer soil water is what limits a spring or double crop in dryland wheat country; a yearly mean hides it.
- **Percent by volume and "points":** m³/m³ is unreadable to most farmers; a change of 0.022 m³/m³ is "+2.2 points", not "+12%", which would be a relative change.

### Integration (what was run and checked)
- Frontend: typecheck, lint, build, and 45 tests (3 new: driest month, row formatting, one-sided data; plus the saved Cook result now checks the row and the chart).
- In the browser (offline API, saved Colfax result): the row and the chart render, no console errors, and no horizontal scrolling at 375 px. Fixed during the check: the top tick label crowded the axis title (more top padding).
- The online demo uses the same components and the same saved files, so it shows them too once deployed.

### What the numbers say (all 10 saved results, driest month)
The best match's soil is wetter than or about the same as the field's in 8 of 10 cases (e.g. LaCrosse 16.9% vs. Garfield 21.3%). Warmer matches don't mean drier soil here: soil water isn't part of the match, and SMAP's ~9 km cell blends land cover, soil texture and terrain. The app shows it as context, not as a forecast.

### Security, efficiency, other flaws
- No new data leaves the browser; no new dependency; the chart is ~100 lines of SVG.
- **Open:** SMAP is a 9 km model-assisted product (L4 assimilates satellite data into a land model), so a field on a ridge and one in a draw get the same number. Listed in OPEN_ISSUES.

---

## M19 — Farmer priorities (2026-11-15)

**Built:** the farmer picks what matters most (save water, cut erosion, build organic matter, add nitrogen, break pest and disease cycles), and the rotation options re-sort by how well their crops fit. The field's current rotation always stays first.
- **Backend** (`rotations.py`): `traits_summary` turns a rotation's crops into the share of its years with each trait from the fixed `TRAITS` table (nitrogen fixing, heavy residue, little residue, fallow, low or high water use, a non-cereal break crop). A new `RotationTraits` model sits on `RotationStrategy.traits` (optional, so older results still validate). Contract JSON Schema and TypeScript types regenerated.
- **Saved results:** `python -m farm_analog.saved --traits-only` adds the traits to the 10 saved files offline. The diff adds `traits` blocks only; nothing else in the files changed.
- **Frontend** (`lib/priorities.ts`, `RotationCards`): checkboxes, a score per priority from 0 to 1, the average for the chosen ones, sorting, a plain reason per priority ("nitrogen-fixing crop in 1 of 3 years"), a "Best fit for your choices" badge, and a screen-reader announcement when the order changes.

### Why these choices
- **Traits computed in the backend, scored in the frontend:** the table has one home (`TRAITS`); the browser only does arithmetic, so it works in the online demo with no server.
- **No absolute "good fit" label.** The first version labeled every option "Poor fit" for "Add nitrogen" (one pulse crop in three years scores 0.33). That's a solid nitrogen rotation in dryland wheat, so a fixed scale misleads. The badge now compares the options with each other, and only when one actually beats another.
- **No income option:** nothing in the data measures markets or prices, and the page says so instead of guessing.
- **Priorities stay in the page.** They're not saved, sent or added to the page address.

### Integration (what was run and checked)
- Backend: ruff and 188 tests (2 new: trait shares per year, strategies carry traits and old results get them). Frontend: typecheck, lint, build and 53 tests (7 new for scoring, sorting, the badge and flexible mixes; plus the saved Colfax result re-sorting when "Add nitrogen" is ticked).
- In the browser (offline API, saved Colfax result): ticking "Cut erosion" and "Add nitrogen" puts winter wheat → spring wheat → pulses right after the current rotation; both get the badge; the fallow rotations drop to the end. No console errors.

### What the numbers say
For Colfax, the field's current rotation is already the best fit for erosion and nitrogen. The matching places lean on fallow, which helps water but costs soil cover. That's the real trade-off the tool should surface: what fits the 2050s climate isn't automatically what fits the farmer's soil goals.

### Other flaws
- A flexible mix counts each of its 3 main crops as one year; the real frequencies vary.
- Scores rest on the general `TRAITS` table, which still needs a WSU Extension read (open since M12).
- Erosion uses crop residue only; tillage, slope and timing matter as much in the Palouse and aren't measured.
- Typed priorities ("I want to save water") through Bill's parser would need the server, so they're left for later.

---

## M18 — Plain-language summaries in the online demo (2026-11-15)

**Built:** the online demo now shows Bill's summary for each of the 10 saved results.
- **Gemini retry** (cherry-picked from `bill-retry`): temporary 500/503/504 errors are retried twice; timeouts and quota errors aren't.
- **More facts for Bill** (`summarizer.summary_input`): the field's current rotation against the matching places' rotations (how many areas use it), and the best match's hot days, frost-free season and driest-month soil water next to the field's. All computed in code; differences use the same rounded-values rule as the hazard table. The template got matching lines ("used in 0 of 5 matching areas"; "31 days a year above 32°C (this field: 23, +8)").
- **Prompt:** a fixed order (best match with its quality word and model agreement, then rotations, hazards, a short climate line, caveats), and "never call a good match strong". Unnamed places are "an unnamed place", not "Match 4".
- **Saved summaries:** `python -m farm_analog.saved --summaries` writes `data/samples/summaries/live_<field>_<scenario>.json` (text, source, notices, model, date) through the same number check as `POST /bill/summary`.
- **Frontend:** in static mode the app loads the saved summary for the matched test field and scenario; the card says it was written ahead of time, by which model, on which date, and that every number was checked.

### What was checked by hand
All 10 summaries came back from Gemini and passed the number check, which only proves each number appears somewhere in the input. So the riskiest claims were traced to the input: hot-day and frost-free pairs (field vs. match), rotation shares and area counts, model agreement, and "good" vs. "strong" for the SSP5-8.5 matches (Dayton 6/8, Lind 5/8, LaCrosse 5/8, all "good"). All matched. The first run had two problems, fixed before saving: places without a county read "Match 4", and most summaries buried the best match under season-by-season numbers (LaCrosse SSP5-8.5 never said its matches were only "good"). One loose phrase remains: Lind SSP5-8.5 says the "projections" are based on the farmland cells.

### Integration
- Backend: ruff, 197 tests (new: summary facts from a saved result, the generator falling back on an unchecked number).
- Frontend: typecheck, lint, 55 tests (new: a summary exists for every test field and scenario and names the best match; the saved-summary label). Built with `VITE_STATIC=1` like `pages.yml` and checked in the browser: Lind shows its summary; switching to SSP5-8.5 swaps it ("5 of 8 … good match"); no console errors.

### Security and privacy
- Gemini gets derived numbers, place and crop names only; no coordinates, no farmer text. The key stays in `.env` on the machine that runs `--summaries`; nothing secret is in the bundle.
- The text is rendered as plain text (React escapes it).
- Free-tier prompts may be used by Google; here they hold only public-data summaries of the 5 test fields.

### Open
Summaries must be regenerated after any rerun; the number check doesn't verify pairings or wording (see OPEN_ISSUES).

---

## M17 — ECOSTRESS afternoon ground temperature (2026-11-15)

**Built:** NASA ECOSTRESS is now part of the hazard outlook, read in Earth Engine (`NASA/ECOSTRESS/L2T_LSTE/V2`) instead of the team's download script.
- **What's measured** (`hazards.fetch_surface_temperature`): for the field and each top match, clear-sky (cloud mask 0) passes from June to August, 2018–2025, between 18 and 23 UTC (11 am–4 pm Pacific daylight time), averaged over cultivated pixels (USDA CDL, 2019–2023) within 1 km, keeping passes with at least 20 such pixels.
- **Reported** (`hazards.surface_temperature`, pure and tested): the median for June and for July–August, and the number of distinct passes. Overlapping map tiles deliver the same pass twice; repeated times count once.
- **Contract:** `Hazards` gains `surface_temp_june_c`, `surface_temp_julaug_c`, `surface_passes` (optional). Schema and types regenerated.
- **Shown:** two hazard-table rows ("June, crops growing" and "July–August, mostly after harvest"), the source note, and a glossary entry saying it's the surface, not the air. Bill gets both numbers, and the template adds the July–August one.

### Why these choices
- **A probe first.** At Colfax and Whitman County, June medians were the same (37.0 vs. 36.9 °C), while July–August differed by about 4 °C. Most July–August readings are stubble and fallow after harvest, so one summer number would mostly measure bare ground. Splitting June from July–August keeps the crop-growing signal visible.
- **Cropland within 1 km, not the point.** A match's location is the center of a ~4.6 km cell; a small circle there can land on a road or a draw. The same mask defines the candidate cells.
- **No NDVI filter:** the ECOSTRESS NDVI product (STARS) doesn't pair one-to-one with the temperature passes, so it would need a time join. Left for later.

### Integration (what was run and checked)
- Backend: ruff, 199 tests (2 new: June vs. July–August with repeated passes; the fields reaching `compare` and the contract). Frontend: typecheck, lint, 56 tests (1 new).
- **Live:** the fetch for Colfax and its top 3 matches took 26 s, in parallel with the other hazard sources.
- **Rerun:** all 10 saved results rerun live in 12 minutes, no missing sources, 87–99 passes per field. Matches, sigmas, climate and the other hazards are unchanged; ranks 4–20 now have county names (from the place-name change on `main`); three Cook and Dayton rotation shares moved by up to 1 point (pixel sampling).
- **Summaries:** regenerated; all 10 from Gemini; every ground-temperature pair checked by hand against the data, plus the quality words for SSP5-8.5.
- **Browser** (static build, as deployed): both rows show (Colfax June 37.0 → 37.6 °C, July–August 40.3 → 44.2 °C), ranks 4–20 named, glossary entry present, no console errors, no horizontal scroll at 375 px.

### What the numbers say
After harvest the matches run hotter than the fields in most cases (Colfax +3.9 °C, Cook +4.7, Dayton +4.4); for the drier fields the difference is small (LaCrosse +0.3, Lind +0.1), since they're already mostly fallow and stubble. In June it's mixed: Dayton's match is 5.2 °C hotter, Colfax's about the same.

### Security, efficiency, other flaws
- No new secrets: Earth Engine runs under the existing project. One more server-side request per analysis, run in parallel.
- Open (in OPEN_ISSUES): surface vs. air, land cover on the day, varying pass times, 2018 start, and the 1 km circle as a sample of the place.
