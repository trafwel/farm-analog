What's up? It's us. The farm guys

Farming it so hard rn

## Import NASA SMAP soil moisture

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

## First 2050 climate comparison

Run `PYTHONPATH=src python -m farm_analog.climate` after Earth Engine setup.
This downloads monthly Palouse summaries for ACCESS-CM2: a 1995–2014 historical
model baseline and a 2041–2060 projection under SSP2-4.5. Small CSV/JSON outputs
are saved in `data/samples/`. This first prototype uses one model, not an ensemble.
The baseline is modeled climate, not observed weather. Temperature is converted
from kelvin to Celsius; precipitation flux is integrated into mean monthly totals
in millimetres. Both periods must contain complete, unique daily timestamps.

## Import NASA ECOSTRESS land surface temperature

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

## First Pacific Northwest analog search

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

## Import USDA Cropland Data Layer (CDL)

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
