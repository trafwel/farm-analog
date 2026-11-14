# Open Issues

Every unresolved item from a milestone review. See rule 3 in [HOW_WE_BUILD.md](HOW_WE_BUILD.md). Each item says which milestone found it and why it's in its group.

## Fix now

_None._ (M0's fixable items were fixed inside M0; see REVIEWS.md.)

## Waits for a milestone

- **[M0 → first PR] CI workflow never run.** It only runs on a pull request. Check it goes green when the M0 pull request is opened.
- **[M0 → M5] No region or area checks on the field.** A valid polygon outside the western US, or one covering a whole state, passes the contract. M5 should reject fields outside `SEARCH_BBOX` and above a maximum area.
- **[M0 → M5] Self-intersecting polygons pass validation.** M5 should check validity (for example with Shapely's `is_valid`) before computing.
- **[M0 → M6] TypeScript generation from `contract/*.schema.json` untested.** Pydantic writes 2020-12 JSON Schema (tuples use `prefixItems`); confirm the chosen generator handles it, or adjust.
- **[M0 → M9] The environment installs the Anthropic SDK, but the spec now uses Gemini.** Swap to the Gemini SDK when Bill is built.
- **[M0 rebase → M1–M4] `search.py` is a working regional prototype of M1–M4, not the full milestones.** It matches the Palouse box's *regional mean* (not a farm), uses quarterly mean temperature (not highs and lows), one model (ACCESS-CM2, which runs warm: July +4.3°C), a sparse 20 km grid over `[-121, 44, -116, 49]`, and no cropland, irrigation or soil filter. Its best match is near Walla Walla (0.50σ), which is plausible. Still needed: farm-level target, `tasmax`/`tasmin`, a cropland mask, several models with an agreement count, output in the `AnalogResult` contract, and tests for `search.py`.
- **[M0 rebase → M3] `search.py` writes its outputs into `data/samples/`, which is committed.** Rerunning it changes tracked files (new timestamps, possibly new rankings). Write to `data/` (ignored) and copy to `data/samples/` deliberately.
- **[M0 rebase → M4] `zip(..., strict=False)` in `search.py`.** Added as an explicit default to satisfy lint without changing behavior. `strict=True` would catch a feature-count mismatch; switch when M4 reworks this code.
- **[M0 rebase → M7] No tests for the SMAP, ECOSTRESS and climate importers.** Their `validate_request` functions and the CSV/JSON writers can be tested with recorded responses; add tests when M7 wires them into the contract.
- **[M0 rebase → M1] The Palouse box is defined twice** (`PALOUSE_BOUNDS` in `data.py` and `ecostress.py`). Move it to `config.py` when M1 adds the first config-driven region.

## Team decision

- **[M0] Definition of `novel_climate`.** The contract uses "best analog's median sigma ≥ 4". The alternative is "best sigma ≥ 4 for most climate models". Median is simpler to explain; confirm.
- **[M0 rebase] Time periods.** `config.py` says model baseline 1985–2014 and future 2041–2070. The team's code (`climate.py`, `search.py`) consistently uses 1995–2014 and 2041–2060, the standard IPCC AR6 periods, and `search.py` also uses PRISM 1995–2014 as the observed reference. Recommendation: switch `config.py` to match the team's code.
- **[M0 rebase] `data.py` now means "SMAP importer".** The plan used `data.py` for shared data loading. Rename it `smap.py`?
- **[M0] Outdated plan documents.** `docs/COMMIT_PLAN.md` and `docs/IMPLEMENTATION_GUIDE.md` (uncommitted, on the old docs branch) describe the Streamlit + Claude plan. Update them to the milestone plan, or delete them? They were left out of M0's commits.
- **[M0] CI speed.** CI installs the full environment for lint and unit tests. Option: a small `environment-ci.yml` with only what tests need. Worth it only if CI time becomes a problem.

## Won't fix

- **[M0] 3-D GeoJSON positions are rejected.** Leaflet drawing produces 2-D positions only; supporting altitude adds complexity for no benefit.

## Resolved

- **[M0]** Streamlit placeholder: the team is actively using `app/app.py` as a local data preview (SMAP and the 2050 comparison). Decision: keep it as a preview until the React app exists (M6).
- **[M0 second rebase]** `README.md` on `main` contained leftover merge-conflict markers (`<<<<<<< Updated upstream` … `>>>>>>> Stashed changes`). Removed the three marker lines; both sections (ECOSTRESS and the analog search) are kept unchanged.
- **[M0 second rebase]** `tests/test_analogs.py` was created on both sides. Kept the team's stronger tests (direct covariance check, missing/constant input checks) and added M0's test that very distant climates stay finite.
- **[M0 rebase]** Teammates' new files (`app/app.py`, `climate.py`, `data.py`, `ecostress.py`) failed the lint check M0 added to CI (35 issues). Fixed with a format-only change; see REVIEWS.md.

- **[M0]** Long line in `contract.py` (ruff E501). Fixed in M0.
- **[M0]** SETUP.md's check launched the Streamlit placeholder instead of running the tests. Fixed in M0.
- **[M0]** SETUP.md kept a stale copy of `environment.yml`. Replaced with a pointer in M0.
