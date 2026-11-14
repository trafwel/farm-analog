# Open Issues

Every unresolved item from a milestone review. See rule 3 in [HOW_WE_BUILD.md](HOW_WE_BUILD.md). Each item says which milestone found it and why it's in its group.

## Fix now

- **[M9] Live Gemini call not run.** No `GEMINI_API_KEY` in `.env`. As soon as a key exists, call `POST /bill/summary` on `fake-colfax` and `POST /bill/parse` once each, to confirm the model id `gemini-3.5-flash-lite` and thinking level `MINIMAL` are accepted. Until then, a rejected setting would silently send every summary to the template.

## Waits for a milestone

- **[M9 → M8 / UI] The frontend doesn't call Bill yet** (team instruction: leave the UI as it is for now). When it does, render `text` and `notices` as plain text, never as HTML (no `dangerouslySetInnerHTML`), and show the notices prominently.
- **[M9 → M8 / UI] Bill's models are deliberately not in the contract.** `ParseResult` and `BillSummary` live in `assistant/` and appear only in the API's OpenAPI schema, so `contract/*.schema.json` and the frontend's generated types are unchanged (a test checks this). When the UI uses Bill, add them to `contract.MODELS` and regenerate the types in the same change.

- **[M7 → team member with Earth Engine] Evidence untested live.** Crops (CDL), soil (OpenLandMap), monthly PRISM normals and county names are fetched for the top 3 analogs in live mode only. Run once on the test fields and check the numbers look sensible.
- **[M7 → before demo] Check the OpenLandMap organic-carbon unit.** The code assumes the catalog's "x 5 g/kg" storage unit (`evidence.OLM_OC_UNIT_G_PER_KG`); confirm on the catalog page, or organic matter will be off by that factor.
- **[M7 → M8] The map doesn't show the evidence yet.** Crops, soil and climographs are in the API response; M8's comparison panel displays them.

- **[M6 → M8] Map polish:** the legend can cover markers in the bottom-right corner; drawing needs a mouse ("Use example field" is the keyboard route); the JavaScript bundle is ~600 kB (Leaflet + Geoman), so consider code-splitting the map.
- **[M6 → M8] Comparison panel.** Clicking an analog highlights it but doesn't yet show its climograph, crops and soil side by side (M7 supplies the data; M8 shows it).

- **[M5 → deployment] No rate limiting.** Each live request runs about 10 Earth Engine jobs. M9 adds two more paid endpoints (`/bill/parse`; `/bill/summary` for uncached results). Before a public deployment, add a per-client limit so one user can't exhaust the team's Earth Engine quota.
- **[M5 → team member with Earth Engine] Live mode untested end to end.** With `EE_PROJECT` set, `POST /analogs` runs M1 + M2 + M4 for real; run it once on the 5 test fields.

- **[M4 → M10] The latitude (day-length) check isn't applied.** Within the inland Northwest every candidate is within 3° of the Palouse, so it has no effect yet; add it if the search area grows.

- **[M3 → team member with Earth Engine] Build the candidate cache.** Run `python -m farm_analog.candidates` once to create `data/candidates/candidates.parquet` (~4 km farmland cells). Until then the app uses the team's 20 km grid, which isn't filtered to farmland, and says so in the result notes.
- **[M3 → M7] No irrigation filter yet.** Irrigated farmland can look like a match on climate while its crops depend on irrigation. Add an irrigated-lands mask (for example LANID) to the candidate build.

- **[M0 → first PR] CI workflow never run.** It only runs on a pull request. Check it goes green when the M0 pull request is opened.
- **[M0 → M9] The environment installs the Anthropic SDK, but the spec now uses Gemini.** Swap to the Gemini SDK when Bill is built. (M9: `google-genai` added; removing `anthropic` is tracked separately.)
- **[M0 rebase → M1–M4] `search.py` is a working regional prototype of M1–M4, not the full milestones.** It matches the Palouse box's *regional mean* (not a farm), uses quarterly mean temperature (not highs and lows), one model (ACCESS-CM2, which runs warm: July +4.3°C), a sparse 20 km grid over `[-121, 44, -116, 49]`, and no cropland, irrigation or soil filter. Its best match is near Walla Walla (0.50σ), which is plausible. Still needed: farm-level target, `tasmax`/`tasmin`, a cropland mask, several models with an agreement count, output in the `AnalogResult` contract, and tests for `search.py`.
- **[M0 rebase → M3] `search.py` writes its outputs into `data/samples/`, which is committed.** Rerunning it changes tracked files (new timestamps, possibly new rankings). Write to `data/` (ignored) and copy to `data/samples/` deliberately.
- **[M1 → team member with Earth Engine] The live field download is untested.** `fetch_prism_monthly` / `farm_today_for_field` couldn't run here (no Earth Engine credentials on this machine). Run it once on the 5 test fields; check `support` (most fields will report `centroid_cell`, since a field is smaller than a ~4 km PRISM cell) and that the normal fingerprint is close to the regional values in `palouse_analog_summary.json`.
- **[M2 → team member with Earth Engine] The model download is untested live,** like M1's PRISM download (no credentials here). Run `farm_future_for_field` on the 5 test fields and check that all 8 models in `config.CLIMATE_MODELS` exist in `NASA/GDDP-CMIP6` with an `ssp245` run; any that don't are reported in `failed_models` instead of stopping the run.
- **[M2 → M8] The contract carries only the ensemble median future** (`AnalogResult.farm_future`). The low-high range across models (`FarmFuture.low` / `.high`) should reach the frontend for the climograph's uncertainty band; add it to the contract in M8.
- **[M0 rebase → M7] No tests for the SMAP, ECOSTRESS and climate importers.** Their `validate_request` functions and the CSV/JSON writers can be tested with recorded responses; add tests when M7 wires them into the contract.

## Team decision

- **[M9] Gemini free tier vs. paid.** On the free tier Google may use prompts to improve its products, and `/bill/parse` sends the farmer's own words. Recommendation: a paid key for any real farmer use.
- **[M9] How strict should the grounding check be?** It checks numbers, not claims (a weak match called "strong" passes). Whole numbers within 0.5 of any input value pass, and spelled-out numbers and unlisted advice phrasings aren't caught. Options: per-field number matching, checking match-quality words against each place, or always showing the template and using Gemini only for a one-line intro.

- **[M7] Soil source.** Evidence uses OpenLandMap (global, 250 m, in Earth Engine) for clay, sand and organic matter, because SSURGO/gNATSGO isn't in the Earth Engine catalog. SSURGO is more detailed for US farms; switch if someone can provide it as an Earth Engine asset.

- **[M6] Retire the Streamlit preview?** The React app now covers the analog map. `app/app.py` still shows SMAP and the 2050 charts, which React doesn't (yet). Keep both for now, or move those charts into React (M8)?

- **[M4] Retire `search.py`?** `match.py` now does everything it did (and reproduces its rankings exactly), per model and in the contract format. Keep `search.py` as the team's reference script, or delete it once everyone has switched?

- **[M3] Confirm the search area.** Built with the recommended default while the team was away: the inland Northwest (`-121, 44, -116, 49`) at ~4 km, farmland only (≥30% cultivated in the Cropland Data Layer, 2019–2023). The western US would need an Earth Engine export to Drive.

- **[M0] Definition of `novel_climate`.** The contract uses "best analog's median sigma ≥ 4". The alternative is "best sigma ≥ 4 for most climate models". Median is simpler to explain; confirm.
- **[M0 rebase] `data.py` now means "SMAP importer".** The plan used `data.py` for shared data loading. Rename it `smap.py`?
- **[M0] Outdated plan documents.** `docs/COMMIT_PLAN.md` and `docs/IMPLEMENTATION_GUIDE.md` (uncommitted, on the old docs branch) describe the Streamlit + Claude plan. Update them to the milestone plan, or delete them? They were left out of M0's commits.
- **[M0] CI speed.** CI installs the full environment for lint and unit tests. Option: a small `environment-ci.yml` with only what tests need. Worth it only if CI time becomes a problem.

## Won't fix

- **[M0] 3-D GeoJSON positions are rejected.** Leaflet drawing produces 2-D positions only; supporting altitude adds complexity for no benefit.

## Resolved

- **[M9]** [M1 → M9] Bill reads the 8-value fingerprint (`tmean_*`, `ppt_*`): each quarter's average temperature and precipitation, today, future and change.
- **[M9]** [M9 → M5] Bill is reachable from the API: `POST /bill/parse` and `POST /bill/summary`. Gemini is set up once at startup (template only without a key), and summaries are cached by result hash.
- **[M9]** The parser no longer converts units (that would be arithmetic), and the grounding check now reads digits attached to letters.

- **[M7]** Place names: in live mode each top analog gets its county ("Walla Walla County, WA") from US Census TIGER boundaries.
- **[M7]** Evidence never costs the match: if fetching crops, soil or climate details fails, the result is returned without them and a note says so (tested).

- **[M6]** TypeScript types are generated from the repo's `contract/` JSON Schema. The generator didn't understand Pydantic's `prefixItems` tuples (it produced `[unknown, unknown]`); `frontend/scripts/gen-types.mjs` rewrites them first and fails if any `unknown` tuple remains. CI checks the committed types are up to date.
- **[M6]** Found and fixed during the end-to-end test: after a refused request (for example a scenario the offline demo doesn't cover), the previous results stayed on screen under the error, looking like results for the new settings. Results are now cleared when a new search starts or the field changes.

- **[M5]** Field checks deferred from M0: the API rejects self-crossing outlines, fields outside the contiguous US, and fields over 50 km², each with a plain-language reason (HTTP 400).
- **[M5]** Without Earth Engine, the API serves the real offline Palouse result only for Palouse fields and SSP2-4.5, and refuses anything else instead of faking it.

- **[M4]** Matching against the farm's future across every model: `match.py` scores each model separately, reports the median and how many models agree, keeps the standardized-distance baseline, and produces the contract's `AnalogResult` (with a new optional `notes` field for caveats).
- **[M0]** `zip(..., strict=False)` in `search.py`: no longer on the main path; `match.py` uses `strict=True`.

- **[M3]** One search area, in `config.SEARCH_BBOX`, used by the candidate builder.

- **[M2]** The future climate is now built at the farm, per model: `future.py` applies each model's quarterly change (temperature added, precipitation multiplied) to the farm's present-day fingerprint. `search.py` uses the same functions; its regression test confirms identical rankings.
- **[M2]** Earth Engine field averaging (with the fall-back to the cell under the field's center) is written once, in `earthengine.py`, and shared by M1 and M2.

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
