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

## Team decision

- **[M0] Definition of `novel_climate`.** The contract uses "best analog's median sigma ≥ 4". The alternative is "best sigma ≥ 4 for most climate models". Median is simpler to explain; confirm.
- **[M0] Streamlit placeholder.** `app/app.py` and the `streamlit`/`leafmap` dependencies are left over from the earlier plan; the spec is now React + FastAPI. Remove them (and update SETUP.md's layout section), or keep them for quick notebook-style demos?
- **[M0] Outdated plan documents.** `docs/COMMIT_PLAN.md` and `docs/IMPLEMENTATION_GUIDE.md` (uncommitted, on the old docs branch) describe the Streamlit + Claude plan. Update them to the milestone plan, or delete them? They were left out of M0's commits.
- **[M0] CI speed.** CI installs the full environment for lint and unit tests. Option: a small `environment-ci.yml` with only what tests need. Worth it only if CI time becomes a problem.

## Won't fix

- **[M0] 3-D GeoJSON positions are rejected.** Leaflet drawing produces 2-D positions only; supporting altitude adds complexity for no benefit.

## Resolved

- **[M0]** Long line in `contract.py` (ruff E501). Fixed in M0.
- **[M0]** SETUP.md's check launched the Streamlit placeholder instead of running the tests. Fixed in M0.
- **[M0]** SETUP.md kept a stale copy of `environment.yml`. Replaced with a pointer in M0.
