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
