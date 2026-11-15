# Farm Analog

[![ci](https://github.com/trafwel/farm-analog/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/trafwel/farm-analog/actions/workflows/ci.yml) **[Try the online demo](https://trafwel.github.io/farm-analog/)** (no install: real Earth Engine results saved for 5 Palouse test fields)

**Your field's 2050s climate already exists somewhere today. Farm Analog finds it, and shows the crop rotations farmers there grow and the hazards they already face.**

NASA Space Apps Challenge 2026 · *Field Shift: Adapting Farms with NASA Data* · Region: the Palouse, eastern Washington.

## What it does

1. **Draw your field** on the map.
2. **Your field today:** PRISM monthly climate (1995–2014), summarized as 8 numbers (average temperature and total precipitation per season) plus how much they vary from year to year.
3. **Your field around 2050:** each of 8 NASA NEX-GDDP-CMIP6 climate models' change (2041–2060 vs. 1995–2014) is added to your field's real climate. Both SSP2-4.5 (moderate) and SSP5-8.5 (high emissions) are available.
4. **Matching places:** 3,351 farmland cells (~4.6 km, USDA Cropland Data Layer) across the inland Northwest are scored with sigma dissimilarity (Mahony et al., 2017) under every model. Below 1 is a strong match; 4 or more means no real match (a "novel climate").
5. **Rotation options:** what the matching places actually grew from 2016 to 2023, read pixel by pixel from the Cropland Data Layer. Your field's current rotation comes first, with at least three options in all, each with why, evidence, benefits, risks and gaps.
6. **Hazard outlook:** hot days and frost dates (PRISM daily), heavy-rain days (NASA GPM IMERG), soil moisture (NASA SMAP), afternoon ground temperature at 70 m (NASA ECOSTRESS) and bare-field months (Landsat NDVI). Each compares your field today with the matching place today.
7. **Plain words:** a template summary (or Gemini, when a key is set; every number is checked), a glossary, and a reminder to check with your county extension agent.

The tool supports a farmer's decision; it doesn't make it.

## What we found (5 Palouse test fields, live with Earth Engine)

| Field | Summer °C, today → 2050s (SSP2-4.5) | Best matches today | Under SSP5-8.5 |
|---|---|---|---|
| Cook Farm (Pullman) | 17.7 → 20.3 | Whitman Co., WA, 0.30σ (8/8 models) | 0.71σ (8/8) |
| Colfax | 18.3 → 21.0 | Whitman / Walla Walla, 0.31σ (8/8) | 0.69σ (8/8) |
| LaCrosse | 20.0 → 22.6 | Garfield Co., WA, 0.49σ (8/8) | 1.09σ (5/8) |
| Lind | 20.0 → 22.6 | Gilliam Co., OR, 0.48σ (8/8) | 1.10σ (5/8) |
| Dayton | 19.6 → 22.3 | Walla Walla Co., WA, 0.36σ (8/8) | 1.02σ (6/8) |

- **Climate:** the matching places have more hot days and a frost-free season about a month longer than the fields today.
- **Rotations:** the matching places rotate with more fallow.
- **Limit:** a crop backtest (2008–2012 → 2019–2023) shows that climate alone predicts crop mix only slightly better than random farmland (similarity 0.53 vs. 0.52). That's why rotations are shown as evidence to discuss, not predictions. Details: [docs/REVIEWS.md](docs/REVIEWS.md).

## Run it

**Online:** https://trafwel.github.io/farm-analog/ runs in the browser with no server. Pick a test field under "Try a test field", or draw near one of the green squares, and press Find analogs. It serves the saved Earth Engine results for the 5 test fields. Anything else gets a clear "not covered" message.

**Locally:**

Setup (conda environment, Earth Engine login) is in [SETUP.md](SETUP.md). Then:

```bash
FARM_ANALOG_OFFLINE=1 uvicorn farm_analog.api:app --port 8000   # works without Earth Engine
cd frontend && pnpm install && pnpm dev                          # http://localhost:5173
```

Without Earth Engine, a field drawn near one of the 5 test fields gets that field's saved live result (`data/samples/live_*.json`). Other Palouse fields get a regional demo. With `EE_PROJECT` set in `.env`, every field is analyzed live.

**Checks:** `ruff check .`, `pytest` (199 tests), and in `frontend/`: `pnpm typecheck`, `pnpm lint`, `pnpm test` (60 tests). CI runs all of them on every pull request.

## How it's built

- **Backend** (`src/farm_analog/`): Python 3.11, pandas/NumPy/SciPy/scikit-learn, Pydantic, FastAPI, the Google Earth Engine API. Each module's docstring ends with a "Data flow" note: what it reads, what it produces and who uses it.
- **Frontend** (`frontend/`): React 18 + TypeScript, Leaflet and Geoman. Its types are generated from the JSON contract in `contract/`.
- **Docs** (`docs/`):
  - [ARCHITECTURE.md](docs/ARCHITECTURE.md): the pipeline graph;
  - [REVIEWS.md](docs/REVIEWS.md): a self-review per milestone;
  - [OPEN_ISSUES.md](docs/OPEN_ISSUES.md);
  - [TEACH_BACK.md](docs/TEACH_BACK.md);
  - [HOW_WE_BUILD.md](docs/HOW_WE_BUILD.md): the team's build rules;
  - [SUBMISSION.md](docs/SUBMISSION.md): the Space Apps submission text, including NASA data, references and how SI tools were used.

## Data importers

These team scripts download and summarize individual datasets for the Palouse. Small samples are committed in `data/samples/`.

### Import NASA SMAP soil moisture

A small, real Palouse sample is included in `data/samples/`: July 1–7, 2025,
with 56 three-hour readings of regional surface and root-zone moisture.
The CSV and matching provenance JSON can be used without Earth Engine sign-in.
Only small CSV/JSON samples are allowed through Git's data ignore rules;
bulk downloads remain ignored.

The importer downloads SMAP L4 v8 surface (0–5 cm) and root-zone (0–100 cm)
soil moisture, averaged over an approximate Washington Palouse bounding box.
It saves a CSV and provenance JSON in `data/smap/` (gitignored).

Activate the environment described in SETUP.md, set `EE_PROJECT` in `.env`,
then run:

```bash
earthengine authenticate
PYTHONPATH=src python -m farm_analog.data --start 2025-07-01 --end 2025-07-08
```

The end date is exclusive. Override the region with
`--bounds WEST SOUTH EAST NORTH`; requests are limited to 366 days.
The default is a historical one-week sample, not live conditions.

Each row represents a three-hour timestamp, with regional mean moisture in
m³/m³ and valid-pixel counts. Missing values remain empty. SMAP L4 combines
satellite observations with a land model on a native 9 km grid; Earth Engine
reprojects it and lists approximately 11 km pixels. These are regional estimates,
not measurements of individual fields or projections for 2050.

Source: [NASA SMAP L4 v8 on Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/NASA_SMAP_SPL4SMGP_008).
DOI: [10.5067/T5RUATAQREF8](https://doi.org/10.5067/T5RUATAQREF8).

### First 2050 climate comparison

Run `PYTHONPATH=src python -m farm_analog.climate` after Earth Engine setup.
This downloads monthly Palouse summaries for ACCESS-CM2: a 1995–2014 historical
model baseline and a 2041–2060 projection under SSP2-4.5. Small CSV/JSON outputs
are saved in `data/samples/`. This first prototype uses one model, not an ensemble.
The baseline is modeled climate, not observed weather. Temperature is converted
from kelvin to Celsius; precipitation flux is integrated into mean monthly totals
in millimetres. Both periods must contain complete, unique daily timestamps.

### Import NASA ECOSTRESS land surface temperature

A matching Palouse sample is included in `data/samples/`: July 1–7, 2025,
with 30 rows covering 11 ECOSTRESS overpasses. The CSV and provenance JSON
can be used without an Earthdata login.

The importer searches NASA CMR for ECOSTRESS L2T LSTE v002 tiles (70 m,
MGRS-tiled), downloads each tile's LST and cloud-mask GeoTIFFs from LP DAAC,
and clips them to the same approximate Palouse bounding box as SMAP.
It saves a CSV and provenance JSON in `data/ecostress/`, with raw GeoTIFFs
cached in `data/ecostress/raw/` (all gitignored).

Create a free [NASA Earthdata account](https://urs.earthdata.nasa.gov/users/new),
then add it to `~/.netrc` (`%USERPROFILE%\_netrc` on Windows):

```
machine urs.earthdata.nasa.gov login YOUR_USERNAME password YOUR_PASSWORD
```

Then run:

```bash
PYTHONPATH=src python -m farm_analog.ecostress --start 2025-07-01 --end 2025-07-08
```

The end date is exclusive. Override the region with
`--bounds WEST SOUTH EAST NORTH`; requests are limited to 31 days.

Each row is one MGRS tile at one overpass, with clear-sky LST mean, standard
deviation, minimum and maximum in kelvin, plus valid, cloud-flagged and total
pixel counts. Tiles with no clear pixels keep empty LST values. Adjacent tiles
overlap, so do not sum counts across tiles. The ISS orbit gives irregular
overpass times; every pass in the sample week was at night (local time).
LST is land surface skin temperature, not air temperature.

Source: [ECOSTRESS L2T LSTE v002 at LP DAAC](https://lpdaac.usgs.gov/products/eco_l2t_lstev002/).
DOI: [10.5067/ECOSTRESS/ECO_L2T_LSTE.002](https://doi.org/10.5067/ECOSTRESS/ECO_L2T_LSTE.002).

### First Pacific Northwest analog search

Run `PYTHONPATH=src python -m farm_analog.search` after downloading the climate
comparison. The search caches PRISM inputs, candidate rankings, and method metadata
in `data/samples/`. Source: PRISM Group, Oregon State University,
`OREGONSTATE/PRISM/ANm`, AN81 monthly grids.

This prototype compares eight features: mean monthly temperature and total
precipitation in Jan–Mar, Apr–Jun, Jul–Sep, and Oct–Dec. It applies ACCESS-CM2
2041–2060 versus 1995–2014 changes to the observed PRISM 1995–2014 baseline,
additively for temperature and multiplicatively for precipitation. It ranks
sampled PRISM cells in the inland Pacific Northwest using covariance-adjusted
sigma dissimilarity, with standardized Euclidean distance as a second score.

This is a sparse 20-km search grid, not a continuous or field-level search.
The target is a regional mean; candidates are sampled PRISM cells. The reference
period is historical, not current weather. One model, no soil/cropland filtering,
no backtest, and no crop recommendations yet. The Streamlit page is a local preview;
the specified Next.js/FastAPI interface remains to be built.

Check the scoring with `PYTHONPATH=src python -m unittest discover -s tests`.

### Import USDA Cropland Data Layer (CDL)

A matching Palouse sample is included in `data/samples/`: the 2025 CDL, with
40 crop and land-cover classes. The CSV and provenance JSON can be used without
downloading the national file.

The importer downloads the national 30 m CDL release zip from USDA NASS
(about 1.9 GB for 2025), reads only the Palouse window, and counts pixels whose
centers fall inside the same approximate bounding box as SMAP and ECOSTRESS.
NASS throttles each connection, so the zip downloads in 8 parallel, resumable
segments; expect roughly 15–90 minutes. It is cached in `data/cdl/raw/`, and the
CSV and provenance JSON are saved in `data/cdl/` (all gitignored). To download the
zip yourself, save it as `data/cdl/raw/{YEAR}_30m_cdls.zip`. No login is needed.

```bash
PYTHONPATH=src python -m farm_analog.cdl --year 2025
```

Years from 2008 onward are supported. Override the region with
`--bounds WEST SOUTH EAST NORTH`.

Each row is one CDL class with its code, name, pixel count, acres, hectares,
and percent of mapped pixels; background/no-data (code 0) is excluded.
The same data is browsable in [CropScape](https://nassgeodata.gmu.edu/CropScape/),
but its web service is often slow or unavailable, so the importer uses the
release file. CDL is a classified satellite product: per-class accuracy varies,
and pixel-counted acreage is not an official NASS acreage estimate.

Source: [USDA NASS Cropland Data Layer](https://www.nass.usda.gov/Research_and_Science/Cropland/Release/index.php).

### Import USDA NRCS SSURGO soils

A matching Palouse sample is included in `data/samples/`: all 422 SSURGO map
units intersecting the box (8 soil survey areas in WA and ID), with acreage and
key soil attributes. No login is needed.

The importer queries USDA's [Soil Data Access](https://sdmdataaccess.nrcs.usda.gov/)
service. Polygons are clipped to the box and measured on the server, in a 4×4
grid of sub-boxes so each query stays under SDA's time limit (about 2 minutes total).
It saves a CSV and provenance JSON in `data/ssurgo/` (gitignored).

```bash
PYTHONPATH=src python -m farm_analog.ssurgo
```

Override the region with `--bounds WEST SOUTH EAST NORTH` (up to 4 square degrees).

Each row is one map unit: name, acres, percent of the box, dominant component,
farmland class, drainage class, non-irrigated capability class, hydrologic group,
available water storage (0–100 cm), slope, and minimum depth to water table and
bedrock. Attributes are SDA map-unit aggregates (`muaggatt`), not point
measurements; empty values mean SDA has no value.

Source: [USDA NRCS SSURGO](https://www.nrcs.usda.gov/resources/data-and-reports/soil-survey-geographic-database-ssurgo).

### Multi-model NEX-GDDP-CMIP6 climate comparison

A sample is included in `data/samples/`: the same monthly 1995–2014 baseline vs
2041–2060 SSP2-4.5 table as the Earth Engine climate comparison, for 8 models
(ACCESS-CM2, CanESM5, EC-Earth3, GFDL-ESM4, MIROC6, MPI-ESM1-2-HR, MRI-ESM2-0,
NorESM2-MM) plus an unweighted `ensemble_mean`. No login is needed.

The importer uses the NASA NCCS THREDDS NetCDF Subset Service, which returns
only the Palouse 0.25° cells (~50 KB per model-variable-year instead of ~245 MB).
The 8-model run makes 640 requests and takes about 25 minutes; subsets are
cached in `data/nexgddp/raw/` and the CSV and JSON go in `data/nexgddp/` (gitignored).

```bash
PYTHONPATH=src python -m farm_analog.nexgddp
PYTHONPATH=src python -m farm_analog.nexgddp --models ACCESS-CM2 MIROC6
```

Columns match `palouse_climate_ACCESS-CM2_ssp245_2050.csv`. For ACCESS-CM2 the two
pipelines agree within 0.07 °C and ~1% precipitation; the small gap is from edge
cells (this uses cells whose centers fall in the box). In this sample the
ensemble warms 2.1 °C annually and 2.2 °C in June–August; ACCESS-CM2 is near the
warm end (+3.6 °C June–August), so single-model results likely overstate warming.
One ensemble member per model; bias-corrected, statistically downscaled output.

Source: [NASA NEX-GDDP-CMIP6](https://www.nccs.nasa.gov/services/data-collections/land-based-products/nex-gddp-cmip6).
DOI: [10.7917/OFSG3345](https://doi.org/10.7917/OFSG3345).

### Import NASA GPM IMERG precipitation

A sample is included in `data/samples/`: daily precipitation for the 2025 water
year (October 1, 2024 – September 30, 2025, 365 rows). The CSV and provenance
JSON can be used without an Earthdata login.

The importer fetches only the Palouse 0.1° cells of the IMERG V07 Final Run daily
product through GES DISC OPeNDAP (~40 KB per day instead of a 31 MB global file).
A year takes about 12 minutes. Subsets are cached in `data/imerg/raw/` and the CSV
and JSON go in `data/imerg/` (gitignored).

Use the same Earthdata `netrc` entry as ECOSTRESS, and also approve the
**NASA GESDISC DATA ARCHIVE** application in your Earthdata profile
(Applications → Authorized Apps). Then run:

```bash
PYTHONPATH=src python -m farm_analog.imerg --start 2024-10-01 --end 2025-10-01
```

The end date is exclusive; requests are limited to 366 days. Override the region
with `--bounds WEST SOUTH EAST NORTH`. Final Run data lag about 3.5 months.

Each row is one UTC day with regional mean and maximum precipitation (mm/day),
mean random error, mean liquid-precipitation probability, and valid-cell count.
IMERG is a satellite-gauge merged estimate, not station data; snowfall retrievals
are less reliable than rain.

Source: [GPM IMERG Final Run daily V07 at GES DISC](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary).
DOI: [10.5067/GPM/IMERGDF/DAY/07](https://doi.org/10.5067/GPM/IMERGDF/DAY/07).
