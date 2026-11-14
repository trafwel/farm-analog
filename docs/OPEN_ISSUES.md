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
- **[M1 → team member with Earth Engine] The live field download is untested.** `fetch_prism_monthly` / `farm_today_for_field` couldn't run here (no Earth Engine credentials on this machine). Run it once on the 5 test fields; check `support` (most fields will report `centroid_cell`, since a field is smaller than a ~4 km PRISM cell) and that the normal fingerprint is close to the regional values in `palouse_analog_summary.json`.
- **[M1 → M9] Bill's summarizer reads the old fingerprint names** (`tmax_djf`, `tmin_djf`, ...) in `src/farm_analog/assistant/summarizer.py` on `m9-bill`. After M1 merges, M9 must rebase onto it and switch to `tmean_jfm`... / `ppt_jfm`... (temperature becomes one average instead of high and low).
- **[M1 → M3] Two search areas.** `config.SEARCH_BBOX` is the western US (`-125, 31, -100, 49`); the team's `search.py` uses the inland Northwest (`-121, 44, -116, 49`). M3 decides which and uses `config` for it.
- **[M1 → M2] `search.py` applies the climate-model change to the regional mean, not to the farm.** M2 should apply the delta to `FarmToday.normal` for the drawn field.
- **[M0 rebase → M7] No tests for the SMAP, ECOSTRESS and climate importers.** Their `validate_request` functions and the CSV/JSON writers can be tested with recorded responses; add tests when M7 wires them into the contract.

## Team decision

- **[M0] Definition of `novel_climate`.** The contract uses "best analog's median sigma ≥ 4". The alternative is "best sigma ≥ 4 for most climate models". Median is simpler to explain; confirm.
- **[M0 rebase] `data.py` now means "SMAP importer".** The plan used `data.py` for shared data loading. Rename it `smap.py`?
- **[M0] Outdated plan documents.** `docs/COMMIT_PLAN.md` and `docs/IMPLEMENTATION_GUIDE.md` (uncommitted, on the old docs branch) describe the Streamlit + Claude plan. Update them to the milestone plan, or delete them? They were left out of M0's commits.
- **[M0] CI speed.** CI installs the full environment for lint and unit tests. Option: a small `environment-ci.yml` with only what tests need. Worth it only if CI time becomes a problem.

## Won't fix

- **[M0] 3-D GeoJSON positions are rejected.** Leaflet drawing produces 2-D positions only; supporting altitude adds complexity for no benefit.

## Resolved

- **[M1]** Time periods: team chose the IPCC AR6 periods. `config.py` now uses 1995–2014 (PRISM reference and model baseline) and 2041–2060 (future), matching the team's code.
- **[M1]** Fingerprint: team chose the 8-value quarterly fingerprint (mean temperature and precipitation per calendar quarter) used by `search.py`. One shared definition in `fingerprint.py`; the contract, fixture and JSON Schemas updated to match.
- **[M1]** The Palouse box is now defined once, in `config.py`; `data.py` and `ecostress.py` import it.
- **[M1]** `search.py` no longer logs in to Earth Engine when its cache exists, and can write its outputs to another folder (`run(data_dir, output_dir)`). A regression test reruns it from the committed cache and checks the rankings are unchanged. (Partly addresses the "writes into data/samples" item: the default still writes there.)

- **[M0]** Streamlit placeholder: the team is actively using `app/app.py` as a local data preview (SMAP and the 2050 comparison). Decision: keep it as a preview until the React app exists (M6).
- **[M0 second rebase]** `README.md` on `main` contained leftover merge-conflict markers (`<<<<<<< Updated upstream` … `>>>>>>> Stashed changes`). Removed the three marker lines; both sections (ECOSTRESS and the analog search) are kept unchanged.
- **[M0 second rebase]** `tests/test_analogs.py` was created on both sides. Kept the team's stronger tests (direct covariance check, missing/constant input checks) and added M0's test that very distant climates stay finite.
- **[M0 rebase]** Teammates' new files (`app/app.py`, `climate.py`, `data.py`, `ecostress.py`) failed the lint check M0 added to CI (35 issues). Fixed with a format-only change; see REVIEWS.md.

- **[M0]** Long line in `contract.py` (ruff E501). Fixed in M0.
- **[M0]** SETUP.md's check launched the Streamlit placeholder instead of running the tests. Fixed in M0.
- **[M0]** SETUP.md kept a stale copy of `environment.yml`. Replaced with a pointer in M0.
