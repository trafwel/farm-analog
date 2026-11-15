# Open Issues

Every unresolved item from a milestone review. See rule 3 in [HOW_WE_BUILD.md](HOW_WE_BUILD.md). Each item says which milestone found it and why it's in its group.

## Fix now


## Waits for a milestone

- **[M15 → team, before 11:59 p.m. tonight] Submit.**
  1. Make the demo: up to 7 slides, or a video of 30 seconds at most.
  2. Paste each section of `docs/SUBMISSION.md` into the project form, adding the demo link and a deployed link if there is one.
  3. Check that every team member is registered for the same Local Event.
  4. Tick both confirmation boxes.

- **[M19] Priorities rest on general crop traits.** Scores come from `rotations.TRAITS` (not yet reviewed by WSU Extension), a flexible mix counts each main crop as one year, and erosion uses residue only (no tillage or slope). Typed priorities via Bill's parser need the server.

- **[M8] The farm's own soil isn't fetched.** `evidence.add_evidence` never passes `farm_soil`, so the comparison's soil table shows only the matching place. Add the field's center as one more point in `fetch_evidence`, then rerun `python -m farm_analog.saved`.
- **[M8] The results panel is long on phones.** Rotation cards, comparison, list, summary, fingerprint and glossary stack in one column. Consider collapsing sections or using tabs.

- **[M11] The backtest is weak, and that's the honest result.** Live, over 200 test cells: analog areas' 2008–2012 crop mix matched the test cell's 2019–2023 crop mix with similarity 0.529, random farmland cells 0.517, and the cell's own past 0.818; analogs beat random cells in 57% of cells. Over an 11-year gap, climate alone says little about crop mix in a wheat-dominated region. Present it as a limit, not a validation, and consider the alternative design under Team decision (M10).
- **[M11 → live run] Sigma vs. the plain baseline, live.** Still only measured offline (Spearman 0.997). `proof.rank_agreement` on a live 8-model match table would settle it; the live tables aren't saved yet.
- **[M11] Saved results go stale.** `data/samples/live_*.json` were last computed on 2026-11-15 (M17 rerun). Rerun `python -m farm_analog.saved` after any change to the pipeline, the candidate cache, or the test-field points, then `--summaries`. A rerun can shift rotation shares by about a point (Earth Engine samples pixels).
- **[M12] Rotations come from 8 years of 30 m CDL labels.** CDL misclassifies some pixels (pulses vs. spring grains in particular), and 8 years show at most two cycles of a 4-year rotation. Many pixels have no clean cycle and are grouped as "flexible mixes". Treat shares as rough.
- **[M12] Crop-traits text is general agronomy,** not local research. Have someone at WSU Extension (or a farmer on the team's contact list) read `rotations.TRAITS` before the demo.
- **[M13] Hazard periods differ by source:** PRISM 1995–2014, IMERG 2014–2023, SMAP 2016–2023, Landsat 2019–2023. Coarse grids (PRISM ~4 km, IMERG ~10 km, SMAP ~9 km) are read at the point; only NDVI is field-scale.
- **[M13] `OREGONSTATE/PRISM/AN81d` is deprecated** in Earth Engine (superseded by `OREGONSTATE/PRISM/ANd`). It still serves 1995–2014. Switch `hazards.PRISM_DAILY_COLLECTION` and check the band names before the asset goes away.
- **[M13] IMERG days are UTC days,** so a storm can be split across two days; extreme-rain counts may be slightly low.
- **[M13] Bare months use a fixed NDVI threshold (0.25)** on a 200 m circle that includes field edges; in wheat–fallow areas half the years are fallow, pulling medians down.

- **[M9 → M8 / UI] Bill's models are deliberately not in the contract.** `ParseResult` and `BillSummary` live in `assistant/` and appear only in the API's OpenAPI schema, so `contract/*.schema.json` and the frontend's generated types are unchanged (a test checks this). When the UI uses Bill, add them to `contract.MODELS` and regenerate the types in the same change.


- **[M6] JavaScript bundle size:** ~630 kB (Leaflet + Geoman); consider code-splitting the map. (The legend overlap was fixed on `main` with the compact legend.)

- **[M5 → deployment] No rate limiting.** Each live request runs about 10 Earth Engine jobs. M9 adds two more paid endpoints (`/bill/parse`; `/bill/summary` for uncached results). Before a public deployment, add a per-client limit so one user can't exhaust the team's Earth Engine quota.

- **[M3 → M7] No irrigation filter yet.** Irrigated farmland can look like a match on climate while its crops depend on irrigation. Add an irrigated-lands mask (for example LANID) to the candidate build.

- **[M0 → M9] The environment installs the Anthropic SDK, but the spec now uses Gemini.** Swap to the Gemini SDK when Bill is built. (M9: `google-genai` added; removing `anthropic` is tracked separately.)
- **[M0 rebase → M1–M4] `search.py` is a working regional prototype of M1–M4, not the full milestones.** It matches the Palouse box's *regional mean* (not a farm), uses quarterly mean temperature (not highs and lows), one model (ACCESS-CM2, which runs warm: July +4.3°C), a sparse 20 km grid over `[-121, 44, -116, 49]`, and no cropland, irrigation or soil filter. Its best match is near Walla Walla (0.50σ), which is plausible. Still needed: farm-level target, `tasmax`/`tasmin`, a cropland mask, several models with an agreement count, output in the `AnalogResult` contract, and tests for `search.py`.
- **[M0 rebase → M3] `search.py` writes its outputs into `data/samples/`, which is committed.** Rerunning it changes tracked files (new timestamps, possibly new rankings). Write to `data/` (ignored) and copy to `data/samples/` deliberately.
- **[M2 → M8] The contract carries only the ensemble median future** (`AnalogResult.farm_future`). The low-high range across models (`FarmFuture.low` / `.high`) should reach the frontend for the climograph's uncertainty band; add it to the contract in M8.
- **[M0 rebase → M7] No tests for the SMAP, ECOSTRESS and climate importers.** Their `validate_request` functions and the CSV/JSON writers can be tested with recorded responses; add tests when M7 wires them into the contract.

- **[M18] Saved summaries go stale.** `data/samples/summaries/` describes the saved results as of 2026-11-15. After any rerun (M17 ECOSTRESS, M21 soil) run `python -m farm_analog.saved --summaries` and read all 10 again before committing.
- **[M18] The number check doesn't check pairings or wording.** It confirms every number appears in the input, not that it's attached to the right thing, and not quality words. All 10 saved summaries were checked by hand against the input (pairs, shares, model counts, "good" vs. "strong"); one loose phrase remains (after the M17 rerun: LaCrosse SSP5-8.5 says the "climate model projections" are based on the farmland cells, where the candidates are).

- **[M17] Ground temperature is the surface, not the air, and reflects what was growing.** ECOSTRESS reads the crop, stubble or bare soil on each pass; July–August is mostly after harvest, and wheat–fallow land reads hotter than continuous crop. June and July–August are shown apart for that reason. Passes come at varying times inside 11 am–4 pm, and the data start in 2018, not 1995 like the climate baseline. The 1 km cropland circle is a sample of the place, not the farmer's field.

## Team decision

- **[Fix pass] Pushes straight to `main`.** Two direct pushes (`0f8c081`/#19 merge, `978f9c8`) broke CI on `main` today; the second also stopped the online demo from deploying until fixed. Recommendation: protect `main` so changes go through a pull request with green CI.
- **[Fix pass] The page address holds the field and the priorities, and reloading reruns the analysis.** Field corners are farm location data (HOW_WE_BUILD: don't store them longer than needed); in the URL they land in browser history and shared links. In live mode, every opened link also starts Earth Engine jobs, with no rate limit yet. Options: keep (shareable links), keep only in the online demo, or drop the field from the URL.

- **[M16] Soil water is context, not part of the match.** In 8 of 10 saved results the best match's driest-month soil is wetter than or about the same as the field's, because SMAP is a ~9 km land-model product and soil water isn't in the climate fingerprint. Options: keep it as context (current), add a note when the match is wetter, or add a soil-water term to matching (changes every result and needs a rerun).

- **[M11] OpenLandMap organic carbon is stored in 5 g/kg steps,** so organic matter can only be about 1.7, 2.6, 3.4 or 4.3%. Coarse, not wrong; another reason to weigh SSURGO (Owen's new `ssurgo.py` on `main`) for soil.
- **[M11] Owen's importers on `main` (SSURGO, an 8-model NEX-GDDP ensemble, GPM IMERG daily)** are merged but unused by the pipeline. Decide whether `hazards.py` should reuse `imerg.py` and whether soil should switch to `ssurgo.py`.

- **[M9] Gemini free tier vs. paid.** On the free tier Google may use prompts to improve its products, and `/bill/parse` sends the farmer's own words. Recommendation: a paid key for any real farmer use.
- **[M9] How strict should the grounding check be?** It checks numbers, not claims (a weak match called "strong" passes). Whole numbers within 0.5 of any input value pass, and spelled-out numbers and unlisted advice phrasings aren't caught. Options: per-field number matching, checking match-quality words against each place, or always showing the template and using Gemini only for a one-line intro.
- **[M10] Backtest periods.** 2008–2012 vs. 2019–2023 (CDL starts in 2008 in the inland Northwest). The gap is short, so climate changed little. Alternatives: compare places farther apart in climate today instead of over time, or accept the short gap and report "nothing changed" alongside.

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

- **[Fix pass]** [M7 → team member with Earth Engine] Evidence ran live on the 5 test fields (M11): crops, soil, monthly normals and county names look sensible.
- **[Fix pass]** [M7 → before demo] Checked on live values (M11): organic matter comes out 1.7–4.3%, plausible for Palouse topsoil, so the ×5 g/kg unit is right.
- **[Fix pass]** [M7 → M8] M8 shows crops, soil and the climate chart in the comparison panel.
- **[Fix pass]** [M6 → M8] M8 built it.
- **[Fix pass]** [M5 → team member with Earth Engine] Run live on all 5 test fields (M11), and again for M17.
- **[Fix pass]** [M3 → team member with Earth Engine] Built (M11): 3,351 farmland cells.
- **[Fix pass]** [M0 → first PR] CI has run on every pull request since #2.
- **[Fix pass]** [M1 → team member with Earth Engine] Ran live (M11). Earth Engine area-weights partial cells, so `support` reads "field_mean" even for small fields; the "centroid_cell" fallback only fires when a field returns nothing.
- **[Fix pass]** [M2 → team member with Earth Engine] Ran live (M11): all 8 models have SSP2-4.5 and SSP5-8.5 runs.
- **[Fix pass]** [M10 → live run] Merged into the M11 item of the same name (one open item, not two).
- **[M18]** [M9] Live Gemini check: `gemini-3.5-flash-lite` with thinking level `MINIMAL` is accepted (the `bill-retry` check, and 10 summaries written on 2026-11-15). Temporary 500/503/504 errors are now retried twice.
- **[M18]** [M9 → UI] The frontend shows Bill's summary as plain text: from `POST /bill/summary` with a server, and from saved summaries in the online demo.

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
