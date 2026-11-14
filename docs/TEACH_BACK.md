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

