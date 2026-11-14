# How We Build farm-analog

One milestone at a time, explained. Adapted from the team rule of Oct 17 for this project: Python (FastAPI, Earth Engine, numpy, scikit-learn) on the backend, React + Leaflet on the frontend, Gemini as the "Bill" summarizer.

---

## The rules

### 1. One milestone per round

Claude implements **one** milestone (M#) per round. Never two, never "keep going".

Different teammates can run separate Claude sessions on different milestones at the same time (for example, one on M3 and one on M6), as long as their milestones don't touch the same files. Each session still does one milestone per round.

### 2. Explain the thinking while building

For each file: what problem it solves, the options considered, why this approach, and the concept behind it. Plain language first, then the code. Examples for this project:

- Why the delta method instead of using climate model output directly.
- Why sigma dissimilarity instead of plain distance.
- Why sample candidate points once and cache them, instead of querying Earth Engine on every request.
- Why the API returns the top 20 analogs instead of all 20,000 scored points.

### 3. Self-review after every milestone

Before the teach-back, write a review in [REVIEWS.md](REVIEWS.md) covering:

- **Efficiency:** repeated Earth Engine round trips (`getInfo` in loops), re-sampling candidates that should be cached, the same fingerprint computed twice, oversized API payloads, React map layers re-rendering on every state change.
- **Integration:** does it work with every piece it touches (the shared JSON contract, FastAPI, the React app, cached files, other milestones' code, the architecture graph)? **Run it and check**: start the API and the frontend and click through, or run the notebook end to end. Don't assume.
- **Security and privacy:**
  - Field boundaries are farmers' location data: don't log them, don't send coordinates to Gemini (send derived results only), don't store them longer than the request needs.
  - Secrets stay on the server: Earth Engine credentials, `GEMINI_API_KEY`, `NASS_API_KEY`. Never in the React bundle (any `VITE_` variable is public).
  - Untrusted input: validate GeoJSON (valid polygon, size limit, inside the supported area); treat farmer text as data in Gemini prompts (prompt injection); escape anything Gemini returns before rendering it as HTML; sanitize CSV exports.
  - CORS limited to the frontend's origin.
- **Other flaws:** edge cases (a polygon outside the US, a field with no cropland nearby, a novel climate, Earth Engine timeouts), accessibility (map colors readable for color-blind users, keyboard access, text alternatives to the map), error handling, and anything the tests don't cover.

Fix what can be fixed in the same milestone. List the rest as known issues with a reason, and copy every unresolved item into [OPEN_ISSUES.md](OPEN_ISSUES.md), grouped as **fix now / waits for a milestone / team decision / won't fix**. After the milestone, fix the "fix now" group in a separate step and move those items to Resolved.

### 4. Teach-back check before moving on

At the end of the milestone, summarize the key concepts and write 2–4 short questions into [TEACH_BACK.md](TEACH_BACK.md). The team answers there or in chat. **Don't start the next milestone until the team says they understand and asks to continue.** If an answer shows a gap, explain that concept again, differently, first.

Tonight's deadline adaptation: keep each teach-back to about 5 minutes (2 questions). It's still a gate, just a short one.

### 5. Update the architecture graph

At the end of every milestone, update [ARCHITECTURE.md](ARCHITECTURE.md): mark what's now built, add new parts and connections, and add a changelog line. The graph must always match the code on the branch.

### 6. One branch and pull request per milestone

Each milestone lands as its own branch (`m1-farm-today`, `m2-farm-2050`, ...) and pull request, so it can be reviewed on its own. Milestones that depend on earlier ones stack: `m2` branches from `m1`. Merging and pushing happen only when the team says so.

### 7. Git work goes to a helper agent

Commits, pushes, propagating a change up the stacked milestone branches, and opening or updating pull requests are delegated to a subagent with exact instructions: branches, files, commit messages, and what not to touch. This session writes the code and docs, runs the checks, then reviews what the agent did (`git log`, the diff, the pull request) before reporting it as done.

- Never force-push. Never push to `main`.
- Never commit `.env`, API keys, Earth Engine credentials, or anything in `data/` (cached candidates, exports, results).
- Stage files by path (`git add <path>`), never `git add -A` or `git add .`.

### 8. CI is real

`.github/workflows/ci.yml` runs on every pull request:

| Part | Checks |
|---|---|
| Backend (Python) | `ruff check .` (lint), `pytest` (tests) |
| Frontend (React) | `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm build` |

A pull request is ready only when its checks are green. Tests never call live services (Earth Engine, Gemini, NASS): use recorded responses and fixtures.

---

## Milestones

Each milestone is small enough to build, review and teach back in about an hour. The shared JSON contract (M0) lets the backend and frontend streams run in parallel.

| # | Milestone | Builds | Depends on |
|---|---|---|---|
| **M0** | Foundation | `pyproject.toml`, pytest and ruff, CI, the docs in this folder, the **JSON contract** (Pydantic models in `src/farm_analog/schema.py`, with TypeScript types generated from the API's OpenAPI spec), a fake-results fixture | none |
| **M1** | Farm today | PRISM monthly values at a point, the 12-variable seasonal fingerprint, the 30-year year-to-year array; tests on recorded data | M0 |
| **M2** | Farm in 2050 | Delta method with one NEX-GDDP-CMIP6 model (add temperature change, multiply precipitation ratio); tests | M1 |
| **M3** | Candidates | Sample PRISM normals at cropland points across the western US, fingerprint them, cache to Parquet | M1 |
| **M4** | Match | Sigma dissimilarity ranking, novel-climate flag, the "farm today vs. today" self-check | M2, M3 |
| **M5** | API | FastAPI `POST /analogs`: validated GeoJSON in, contract JSON out; fixture fallback | M0, M4 |
| **M6** | Map | React + react-leaflet: draw a field (green), call the API, plot analogs from dark blue (best) to light blue | M0 (fake data), M5 (real) |
| **M7** | Evidence | Crop shares (Cropland Data Layer), soil (SSURGO/gNATSGO) and climograph data for the top analogs | M4 |
| **M8** | Comparison panel | Click an analog: climograph, crop table, soil side by side | M6, M7 |
| **M9** | Bill (Gemini) | Text → key-value parser; plain-language summary of the result JSON only, no reasoning; prompt-injection guardrails | M5 |
| **M10** | Proof | More climate models with an agreement count, standardized-Euclidean baseline, backtest numbers | M4, M7 |

Two streams can run in parallel tonight: **backend** (M1 → M2 → M3 → M4 → M5 → M7 → M10) and **frontend + Bill** (M6 on fake data → M8 → M9), joining at M5.
