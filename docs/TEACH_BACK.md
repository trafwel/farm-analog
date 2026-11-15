# Teach-Back

Key concepts and 2–4 questions after each milestone. Answer here or in chat; the next milestone starts only when the team says they understand. See rule 4 in [HOW_WE_BUILD.md](HOW_WE_BUILD.md).

Template:

```
## M# — <name>

**Key concepts**
- ...

**Questions**
1. ...
   - Answer:
```

---

## M0 — Foundation

_Team confirmed understanding in chat on 2026-11-14 and asked to continue to M1._

**Key concepts**
- **A contract before code.** `schema.py` defines exactly what the backend returns. Backend and frontend build against it in parallel, and the frontend can work on fake data today.
- **One source of truth, exported.** The Pydantic models are the source; `contract/*.schema.json` is generated from them; the frontend's TypeScript types will be generated from that. A test fails if the generated files fall behind.
- **Validate at the edge.** Untrusted input (the drawn polygon) is checked before anything expensive happens.
- **Consistency rules in the contract.** `match_quality` must agree with `sigma`, analogs must be sorted, and `novel_climate` must agree with the best sigma, so a bug can't produce a result that contradicts itself.
- **Deterministic fake data.** A fixed random seed means regenerating the fixture gives the identical file, so it can be tested like code.

**Questions**
1. The frontend developer wants to rename `sigma` to `score`. Which files have to change, and what tells you if you forgot one?
   - Answer:
2. Why does the contract reject unknown fields instead of ignoring them?
   - Answer:
3. An analog arrives with `sigma: 1.5` and `match_quality: "strong"`. What happens, and why is that better than letting it through?
   - Answer:
4. Why is every fake result marked `source: "fixture"`?
   - Answer:

## M1 — Farm today

_Team confirmed understanding in chat on 2026-11-14 and chose to do M2 next._

**Key concepts**
- **One definition of the fingerprint.** `fingerprint.py` defines the 8 values once; the farm, the candidate places, the future climate and the contract all use it. Before M1, the contract and the team's search disagreed (12 vs. 8 values).
- **Why 8 values and not 12.** Sigma dissimilarity learns how the values vary *together* from the reference years. With 20 years, estimating that for 12 values is shaky; 8 is comfortably fewer than 20.
- **Same reference years everywhere.** PRISM and the climate models both use 1995–2014 (IPCC AR6), so the model's change is measured over exactly the years it's added to.
- **Network code apart from logic.** `fetch_prism_monthly` is the only part that talks to Earth Engine; everything after it is plain Python on records, so it's tested offline.
- **Small fields, big cells.** A PRISM cell is about 4 km across, bigger than most fields, so a field usually takes the value of the cell under its center (`support = "centroid_cell"`).
- **Regression test.** `test_search.py` reruns the team's search from its cache and checks the rankings are identical, so the refactor provably changed nothing.

**Questions**
1. Why does `farm_today` refuse to work with only 8 years of data?
   - Answer:
2. If someone changes `QUARTERS` to meteorological seasons (Dec–Feb, ...), which committed files would stop matching, and which test would catch it?
   - Answer:
3. A farmer draws a 40-acre field. Where does its "today" climate actually come from, and what does `support` tell you?
   - Answer:

## M2 — Farm in 2050

_Team asked to continue to M3 in chat on 2026-11-14._

**Key concepts**
- **The delta method.** Climate models are biased, so we use only their *change* (future minus reference) and apply it to the farm's real PRISM climate: add it for temperature, multiply by the ratio for precipitation.
- **Why a ratio for rain.** Adding "−20 mm" to a place that only gets 10 mm would give negative rain; multiplying by 0.8 can't.
- **One future per model, not one blended model.** Each model's change keeps its own pattern; M4 matches each separately and counts how many agree. The headline future is the *median* model, which one extreme model can't drag around the way it can drag an average.
- **Robust to model calendars.** Some models use 360- or 365-day years, so the code checks for "about enough days" and converts daily rain to monthly totals with a fixed days-per-month table.
- **A failing model doesn't sink the run.** It's recorded in `failed_models`; at least 3 must succeed.

**Questions**
1. A model says the Palouse's Jul–Sep rain goes from 36 mm to 29 mm. What future rain does the farm get if its own Jul–Sep normal is 50 mm, and why not 43 mm?
   - Answer:
2. Why is the headline future the median of the models rather than their average?
   - Answer:
3. ACCESS-CM2 warms Jul–Sep by about 4 °C. Should we drop it as an outlier? What would change in M4 if we did?
   - Answer:

## M3 — Candidates

_Built while the team was away (asked to do M3–M7 in one go); the teach-back gate is waived for this batch, but please answer before the next milestones._

**Key concepts**
- **Candidates are the same for every farm**, so they're computed once and cached, not per request.
- **Farmland only.** A cell counts if at least 30% of it is "cultivated" in the Cropland Data Layer (2019–2023). An analog in a forest or a city would be useless to a farmer.
- **Tiles keep downloads small.** Earth Engine allows about 5,000 features per direct download, so the search area is fetched in 1° tiles.
- **Honest fallback.** Without the cache, the app uses the team's 20 km grid and says it isn't farmland-filtered.

**Questions**
1. Why compute candidates once instead of for each farm?
   - Answer:
2. What could go wrong if we didn't filter to farmland?
   - Answer:

## M4 — Match

_Built in the same away batch as M3–M7._

**Key concepts**
- **One score per model, then the median.** Each model's version of the farm's future is matched separately; the headline is the middle model's score, and `models_agree` says how many models call the place a good analog (below 2σ).
- **A baseline to beat.** Plain standardized distance is computed beside sigma dissimilarity, so we can show the more careful method changes the ranking.
- **Regression against the team's work.** With one model on the team's data, M4 reproduces the team's 784 rankings exactly, so the new code is provably the same method.
- **Notes travel with the result.** Caveats (regional demo, one model, unfiltered grid) are part of the contract, so the app and Bill can't drop them.

**Questions**
1. A place has median sigma 1.8 but only 3 of 8 models agree. How should the app describe it?
   - Answer:
2. Why match each model separately instead of matching against the average future?
   - Answer:

