# Architecture

Must always match the code on this branch. See rule 5 in [HOW_WE_BUILD.md](HOW_WE_BUILD.md).

Legend: **built** = exists in code; _planned_ = not yet built (milestone in brackets).

```mermaid
flowchart TD
    PRISM["PRISM monthly (Earth Engine)<br/><b>built [M1, field]</b> · <i>search grid: team prototype</i>"]
    CMIP["NEX-GDDP-CMIP6 (Earth Engine)<br/><b>built [M2, field, 8 models]</b>"]
    CDL["Cropland Data Layer + SSURGO<br/><i>planned [M3, M7]</i>"]
    SMAP["SMAP soil moisture importer (data.py)<br/><b>built (team)</b>"]
    ECO["ECOSTRESS surface temperature importer<br/><b>built (team)</b>"]
    CLIM["climate.py: one-model 2050 regional summary<br/><b>built (team), first step toward M2</b>"]
    PREVIEW["Streamlit local preview (app/app.py)<br/><b>built (team), until M6</b>"]
    SEARCH["search.py: first regional analog search<br/><b>built (team), prototype of M1–M4</b>"]

    FT["Farm today: farm_today.py<br/>fingerprint + year-to-year (20 yrs)<br/><b>built [M1]</b>"]
    FPRINT["Shared 8-value fingerprint: fingerprint.py<br/><b>built [M1]</b>"]
    F50["Farm 2050: future.py<br/>delta method per model + median/range<br/><b>built [M2]</b>"]
    EEH["earthengine.py: field averaging helper<br/><b>built [M2]</b>"]
    CAND["candidates.py: farmland cells, cached Parquet<br/>(falls back to team 20 km cache)<br/><b>built [M3]</b>"]
    SIGMA["sigma_dissimilarity()<br/><b>built</b>"]
    MATCH["match.py: per-model sigma, median, agreement,<br/>baseline, AnalogResult + offline Palouse demo<br/><b>built [M4]</b>"]
    EVID["evidence.py: crops (CDL), soil (OpenLandMap), climograph,<br/>county names for the top 3 (live mode)<br/><b>built [M7]</b>"]

    CONTRACT["JSON contract: schema.py + contract/*.schema.json<br/><b>built [M0]</b>"]
    FIX["Fake results fixture<br/><b>built [M0]</b>"]
    API["api.py + pipeline.py: FastAPI GET /health, POST /analogs<br/>field checks, live or offline-demo mode<br/><b>built [M5]</b>"]
    UI["frontend/: React + Leaflet map, list, fingerprint table<br/><b>built [M6]</b> · <i>comparison panel planned [M8]</i>"]
    BILL["Bill (Gemini): parse + summarize<br/><i>planned [M9]</i>"]
    FARMER(["Farmer"])

    PRISM --> FT
    PRISM --> CAND
    CMIP --> F50
    FT --> F50
    CDL --> CAND
    FT --> MATCH
    F50 --> MATCH
    CAND --> MATCH
    SIGMA --> MATCH
    MATCH --> EVID
    CDL --> EVID
    MATCH --> API
    EEH -. used by .-> FT
    EEH -. used by .-> F50
    FPRINT -. defines .-> FT
    FPRINT -. defines .-> CAND
    FPRINT -. defines .-> CONTRACT
    CMIP --> CLIM
    CLIM --> PREVIEW
    PRISM --> SEARCH
    CLIM --> SEARCH
    SIGMA --> SEARCH
    SEARCH --> PREVIEW
    SMAP --> PREVIEW
    SMAP -. hazards / field view .-> EVID
    ECO -. hazards / field view .-> EVID
    CONTRACT -. defines shape .-> API
    CONTRACT -. types .-> UI
    FIX -. fake data until M5 .-> UI
    FIX -. fake data .-> BILL
    EVID --> API
    API --> UI
    API --> BILL
    BILL --> UI
    FARMER <--> UI
```

**Also built:** conda environment (`environment.yml`), setup guide (`SETUP.md`), project layout (`src/farm_analog/`, `app/`, `notebooks/`), settings (`config.py`, M0), `pyproject.toml` with pytest and ruff (M0), CI for the backend (`.github/workflows/ci.yml`, M0).

Dotted arrows are build-time relationships (shared types and fake data), not runtime data flow.

## Changelog

- 2026-11-14 (M7): Added `evidence.py` (crop shares from CDL, OpenLandMap soil, monthly climographs, county names) attached to the top 3 analogs in live mode; `FarmToday` keeps its monthly table and `FarmFuture` its per-model changes; the live pipeline returns the match even if evidence fails.

- 2026-11-14 (M6): Added `frontend/` (Vite + React + TypeScript, react-leaflet + Geoman drawing, types generated from `contract/`, demo-data fallback, accessible results list) and a frontend CI job.

- 2026-11-14 (M5): Added `pipeline.py` (field checks, live analysis with Earth Engine, offline Palouse demo otherwise) and `api.py` (FastAPI `GET /health`, `POST /analogs`, CORS, privacy-safe caching and errors). Environment gains fastapi, uvicorn, httpx, shapely, pyproj.

- 2026-11-14 (M4): Added `match.py` (sigma per model, median, model agreement, standardized-distance baseline, `AnalogResult` output) and an offline Palouse demo from the team's data that reproduces the team's rankings. Contract gains optional `notes`.

- 2026-11-14 (M3): Added `candidates.py`: farmland PRISM cells in the inland Northwest with the shared fingerprint and cultivated share, fetched in tiles from Earth Engine and cached as Parquet; offline fallback to the team's 20 km cache. Search area set in `config.SEARCH_BBOX`.

- 2026-11-14 (M2): Added `future.py` (per-model delta method at the farm, ensemble median and range, Earth Engine fetch of model climatologies) and `earthengine.py` (shared field averaging). `config.CLIMATE_MODELS` lists 8 models. `search.py` uses the shared delta functions (rankings unchanged).

- 2026-11-14 (M1): Added `fingerprint.py` (one 8-value quarterly definition) and `farm_today.py` (PRISM for a drawn field via Earth Engine, plus offline-tested processing). Contract switched to the 8 values; settings switched to IPCC AR6 periods; the Palouse box moved to `config.py`; `search.py` uses the shared definitions and runs from cache without Earth Engine.

- 2026-11-14 (M0 second rebase): Added the team's `search.py`, a working regional prototype of M1–M4 (PRISM 1995–2014 + ACCESS-CM2 delta + sigma dissimilarity on a 20 km grid), feeding the Streamlit preview.
- 2026-11-14 (M0 rebase): Added the team's SMAP and ECOSTRESS importers, the one-model 2050 summary (`climate.py`) and the Streamlit preview. Importers feed the evidence step later (M7).
- 2026-11-14 (M0): Added the JSON contract (Pydantic models exported to JSON Schema), the fake-results fixture, settings, test and lint setup, and backend CI.
- 2026-11-14: Initial graph. Built: environment setup and `sigma_dissimilarity()`. Everything else planned (M1–M10).
