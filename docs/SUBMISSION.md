# Space Apps submission (M15)

Text for the NASA Space Apps 2026 project submission page, challenge **Field Shift: Adapting Farms with NASA Data**. Copy each section into the matching field. Bracketed items, such as `[link]`, are for the team to fill in.

Rules this follows (Judging & Awards Guide):
- the demo is either 7 slides at most, title and intro included, or a video of 30 seconds at most;
- everything is in English;
- every outside resource is listed under References;
- the submission must say how SI tools were used.

Deadline: **Sunday 15 November 2026, 11:59 p.m. local time** of the team's Local Event.

---

## Project name

Farm Analog

## High-level project summary

Farm Analog shows a farmer where their field's 2050s climate already exists today, and what farmers there grow. The farmer draws a field on a map.
1. NASA's NEX-GDDP-CMIP6 projections from 8 climate models give the field's climate around 2050.
2. The tool searches 3,351 farmland cells across the inland Northwest for places whose climate *today* matches it.
3. For the best matches, it shows the crop rotations those farmers actually use (USDA Cropland Data Layer, 2016–2023). These are compared with the field's current rotation, with at least three options, each with why, evidence, benefits, risks and gaps.
4. It also shows the hazards those places already live with: heat, frost, extreme rain (NASA GPM IMERG), soil moisture (NASA SMAP) and bare-field months (Landsat).

Every number comes from data, and a plain-language summary and glossary make it readable. It supports the farmer's decision; it doesn't make it.

## Link to final project

- Code: https://github.com/trafwel/farm-analog (PRs #2–#15 build it milestone by milestone)
- Live demo (no install): https://trafwel.github.io/farm-analog/ shows the saved Earth Engine results for the 5 Palouse test fields; other fields need the app running with Earth Engine

## Link to project demo

[link to the team's demo: up to 7 slides or a video of 30 seconds at most]

## Detailed project description

**What it does.** The challenge asks for a decision-support tool that helps farmers explore crop-rotation options for soil health and resilience. It should compare at least three strategies, including the current one, and say for each why it was suggested, the evidence, the benefits, the gaps and the risks. Farm Analog answers with **climate analog mapping**: if a place already has the climate your field is projected to have, what its farmers grow and rotate has already been tried in that climate.

**How it works.**
1. **Your field today:** PRISM monthly climate, 1995–2014, gives 8 numbers (average temperature and total precipitation for each quarter) and how much they vary from year to year.
2. **Your field around 2050:** for each of 8 NEX-GDDP-CMIP6 models, the model's change between 1995–2014 and 2041–2060 is added to the field's real climate (the delta method). The tool runs SSP2-4.5 and SSP5-8.5.
3. **Candidate places:** 3,351 cells of about 4.6 km across the inland Pacific Northwest, each at least 30% cultivated.
4. **Matching:** sigma dissimilarity (Mahony et al., 2017) measures distance in units of the field's own year-to-year swings. Below 1 is a strong match; 4 or more means no real match exists, and the app warns about a "novel climate". Every place is scored under every model, and the tool reports how many models agree.
5. **Evidence:** for the top matches, crops (CDL), topsoil (OpenLandMap) and a monthly climate chart comparing the field today, the field in the 2050s and the matching place today.
6. **Rotation strategies:** 8 years of CDL labels per 30 m pixel show the rotation grown there. The field's current rotation comes first, then the rotations used in the matching places. Benefits and risks come from a fixed crop-traits table.
7. **Hazard outlook:** hot days and frost dates (PRISM daily), heavy-rain days (GPM IMERG), root-zone soil moisture (SMAP) and months with little green cover (Landsat NDVI). Each is compared between the field today and the matching place today.

**What we found (live runs, 5 Palouse test fields).** Under SSP2-4.5 every field's 2050s climate already exists nearby, with strong matches (0.30–0.49σ) in Whitman, Garfield and Walla Walla counties (WA) and Gilliam County (OR), and all 8 models agree. Under SSP5-8.5 the matches weaken (0.69–1.10σ) and only 5–6 of the 8 models agree for the drier fields. The matching places rotate with more fallow, and they have more hot days and a frost-free season about a month longer. For example, the Cook Agronomy Farm at Pullman has 18 hot days a year today against 28 at its best match.

**Is it valid?**
- The self-check passes: a place's own climate matches itself.
- All 8 models agree on the matches under SSP2-4.5.
- We also ran a crop backtest. Places whose 2008–2012 climate matched a cell's 2019–2023 climate grew similar crops only slightly more often than random farmland did (0.529 vs. 0.517 similarity). The cell's own past did much better (0.818). We report this openly: over an 11-year gap, climate alone says little about crop mix in a wheat-dominated region. That's why the tool shows rotations as evidence to discuss, not as predictions.

**Built for farmers.**
- Plain-language summary of every result, written by Gemini or a fixed template; every number Gemini writes is checked against the result in code. The online demo shows summaries written ahead of time with the same check.
- Glossary of the terms used.
- Every chart has a table version for screen readers.
- °C and °F, mm and inches side by side.
- "Check with your county extension agent" on every rotation card.
- Each result says how it was made and what it doesn't know.

**Tools and languages.**
- Python 3.11: pandas, NumPy, SciPy, scikit-learn, Pydantic, FastAPI, Google Earth Engine API.
- TypeScript and React 18 with Leaflet and Geoman.
- Gemini, via google-genai, for the optional plain-language layer.
- GitHub Actions for CI: 186 backend tests and 42 frontend tests.

## Use of Super Intelligence (SI)

- **Software development:** we used Anthropic's Claude (Claude Code) as a coding assistant to write most of the code, tests and documentation. It worked one milestone at a time under written team rules (docs/HOW_WE_BUILD.md). The rules required a self-review per milestone (docs/REVIEWS.md), a list of open issues, teach-back questions the team answers before moving on (docs/TEACH_BACK.md), and CI on every pull request. Team members chose the region, the method, the data and the scope, and reviewed the results.
- **In the app:** "Bill" can use Google Gemini to restate a computed result in plain language and to read a farmer's description of their farm. Gemini never chooses crops or makes up numbers: every number in its text is checked against the result, and a fixed template is used whenever the check fails or no key is set. The online demo shows Gemini summaries of the 10 saved results, written ahead of time with the same check; the app with its server writes them on request.
- The analysis itself (matching, rotations, hazards) is deterministic code, not SI.

## NASA data

- **NEX-GDDP-CMIP6** (NASA Earth Exchange Global Daily Downscaled Projections): 8 models (ACCESS-CM2, CanESM5, EC-Earth3, GFDL-ESM4, MIROC6, MPI-ESM1-2-HR, MRI-ESM2-0, UKESM1-0-LL), monthly climatologies 1995–2014 and 2041–2060, SSP2-4.5 and SSP5-8.5. Earth Engine `NASA/GDDP-CMIP6`. https://www.nccs.nasa.gov/services/data-collections/land-based-products/nex-gddp-cmip6
- **GPM IMERG V07** (Global Precipitation Measurement): half-hourly rain summed to days, 2014–2023, for extreme-rain days. Earth Engine `NASA/GPM_L3/IMERG_V07`. https://gpm.nasa.gov/data/imerg
- **SMAP L4** (Soil Moisture Active Passive), version 8, root-zone soil moisture, 2016–2023. Earth Engine `NASA/SMAP/SPL4SMGP/008`. https://doi.org/10.5067/T5RUATAQREF8
- **Landsat 8 and 9** (NASA/USGS), Collection 2 Level 2 surface reflectance, NDVI 2019–2023, for bare-field months. Earth Engine `LANDSAT/LC08/C02/T1_L2`, `LANDSAT/LC09/C02/T1_L2`.
- **ECOSTRESS** land surface temperature (team importer, Streamlit preview). https://ecostress.jpl.nasa.gov/

## Space agency partner data

None.

## References

**Data**
- PRISM Climate Group, Oregon State University: monthly and daily climate (AN81/AN91), via Earth Engine `OREGONSTATE/PRISM/ANm` and `OREGONSTATE/PRISM/AN81d`. https://prism.oregonstate.edu
- USDA NASS Cropland Data Layer, 2016–2023, via Earth Engine `USDA/NASS/CDL`. https://www.nass.usda.gov/Research_and_Science/Cropland/
- OpenLandMap soil clay, sand and organic carbon (Hengl), via Earth Engine. https://openlandmap.org
- US Census TIGER/Line counties (2018), via Earth Engine `TIGER/2018/Counties`.
- USDA NRCS SSURGO (team importer). https://www.nrcs.usda.gov/resources/data-and-reports/soil-survey-geographic-database-ssurgo
- OpenStreetMap contributors (map tiles). https://www.openstreetmap.org/copyright

**Methods**
- Mahony, C. R., Cannon, A. J., Wang, T., & Aitken, S. N. (2017). A closer look at novel climates: new methods and insights at continental to landscape scales. *Global Change Biology*, 23(9), 3934–3955. (Sigma dissimilarity.)
- IPCC AR6 reference periods (1995–2014, 2041–2060).
- Crop-trait notes: general guidance from WSU Extension dryland cropping-systems publications and USDA NRCS conservation crop rotation guidance.

**Software:** Python, pandas, NumPy, SciPy, scikit-learn, Pydantic, FastAPI, Uvicorn, Shapely, pyproj, Google Earth Engine Python API, google-genai, React, TypeScript, Vite, Leaflet, react-leaflet, Leaflet-Geoman, Vitest, pytest, ruff.

**SI tools:** Anthropic Claude (Claude Code), Google Gemini. See "Use of Super Intelligence (SI)".
