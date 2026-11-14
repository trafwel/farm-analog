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
- **[M0 rebase → M2] `climate.py` is a first step toward M2, not M2 itself.** It averages one model (ACCESS-CM2) over the whole Palouse box using daily mean temperature (`tas`). M2 needs daily highs and lows (`tasmax`, `tasmin`), the delta method onto PRISM, the farm's own location, and several models. ACCESS-CM2 runs warm (July +4.3°C in the sample), so a single-model result could overstate the shift.
- **[M0 rebase → M7] No tests for the SMAP, ECOSTRESS and climate importers.** Their `validate_request` functions and the CSV/JSON writers can be tested with recorded responses; add tests when M7 wires them into the contract.
- **[M0 rebase → M1] The Palouse box is defined twice** (`PALOUSE_BOUNDS` in `data.py` and `ecostress.py`). Move it to `config.py` when M1 adds the first config-driven region.

## Team decision

- **[M0] Definition of `novel_climate`.** The contract uses "best analog's median sigma ≥ 4". The alternative is "best sigma ≥ 4 for most climate models". Median is simpler to explain; confirm.
- **[M0 rebase] Time periods.** `config.py` says model baseline 1985–2014 and future 2041–2070; `climate.py` uses 1995–2014 and 2041–2060, the standard IPCC AR6 periods (easy to cite). Recommendation: switch `config.py` to the AR6 periods so everything agrees.
- **[M0 rebase] `data.py` now means "SMAP importer".** The plan used `data.py` for shared data loading. Rename it `smap.py`?
- **[M0] Outdated plan documents.** `docs/COMMIT_PLAN.md` and `docs/IMPLEMENTATION_GUIDE.md` (uncommitted, on the old docs branch) describe the Streamlit + Claude plan. Update them to the milestone plan, or delete them? They were left out of M0's commits.
- **[M0] CI speed.** CI installs the full environment for lint and unit tests. Option: a small `environment-ci.yml` with only what tests need. Worth it only if CI time becomes a problem.

## Won't fix

- **[M0] 3-D GeoJSON positions are rejected.** Leaflet drawing produces 2-D positions only; supporting altitude adds complexity for no benefit.

## Resolved

- **[M0]** Streamlit placeholder: the team is actively using `app/app.py` as a local data preview (SMAP and the 2050 comparison). Decision: keep it as a preview until the React app exists (M6).
- **[M0 rebase]** Teammates' new files (`app/app.py`, `climate.py`, `data.py`, `ecostress.py`) failed the lint check M0 added to CI (35 issues). Fixed with a format-only change; see REVIEWS.md.

- **[M0]** Long line in `contract.py` (ruff E501). Fixed in M0.
- **[M0]** SETUP.md's check launched the Streamlit placeholder instead of running the tests. Fixed in M0.
- **[M0]** SETUP.md kept a stale copy of `environment.yml`. Replaced with a pointer in M0.
