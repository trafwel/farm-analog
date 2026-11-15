"""Project-wide settings.

Change a default here, not inside individual modules, so the analog pipeline, the API and
the docs always agree on periods, thresholds and limits.

Data flow:
Inputs:  none (constants only; nothing is read from disk or the environment here).
Outputs: periods (BASELINE_YEARS, FUTURE_YEARS), CLIMATE_MODELS, PRISM asset names,
         PALOUSE_BOUNDS, the search area and grid (SEARCH_BBOX, GRID_SCALE_M), the farmland
         and day-length filters, sigma thresholds, API limits, backtest settings, and
         Bill's settings.
Used by: nearly every module: schema.py (thresholds), fingerprint/farm_today/future
         (periods), candidates.py, match.py, pipeline.py, evidence.py, proof.py, the team's
         importers (data.py, ecostress.py, climate.py, search.py) and assistant/*.
"""

from typing import Final

# Periods follow the IPCC AR6 convention (team decision, M1): a 1995-2014 reference and a
# 2041-2060 "mid-century" future. Using the same reference years for PRISM and for the
# climate models means the model's change is measured over exactly the years it's applied to.

# Present-day climate: PRISM normals and each farm's year-to-year variation (20 years).
BASELINE_YEARS: Final = (1995, 2014)

# Climate-model reference period (CMIP6 "historical" runs end in 2014).
MODEL_HISTORICAL_YEARS: Final = (1995, 2014)

# "Around 2050".
FUTURE_YEARS: Final = (2041, 2060)

DEFAULT_SCENARIO: Final = "ssp245"

# NEX-GDDP-CMIP6 models used for the future climate (M2). Chosen to span the range of
# projected warming: warmer-running (ACCESS-CM2, CanESM5, UKESM1-0-LL), middle (EC-Earth3,
# MRI-ESM2-0) and cooler-running (GFDL-ESM4, MIROC6, MPI-ESM1-2-HR). Each model's change is
# applied separately; M4 counts how many models agree on an analog.
CLIMATE_MODELS: Final = (
    "ACCESS-CM2",
    "CanESM5",
    "EC-Earth3",
    "GFDL-ESM4",
    "MIROC6",
    "MPI-ESM1-2-HR",
    "MRI-ESM2-0",
    "UKESM1-0-LL",
)

# PRISM monthly grids in Earth Engine (~4 km). AN81 = the long-running monthly series.
PRISM_COLLECTION: Final = "OREGONSTATE/PRISM/ANm"
PRISM_DATASET_TYPE: Final = "AN81"
# Earth Engine labels PRISM from 2021 on "AN91" (the newer PRISM version). Periods that reach
# past 2020 (the M10 backtest's 2019-2023) accept both; the 1995-2014 baseline is all AN81.
PRISM_DATASET_TYPES: Final = ("AN81", "AN91")

# Approximate Washington Palouse demo extent as (west, south, east, north) in degrees.
# Not an official regional boundary.
PALOUSE_BOUNDS: Final = (-118.2, 46.5, -117.0, 47.2)

# The 5 test fields (M11), across the Palouse rainfall gradient: name -> (label, lat, lon).
# Starting from the approximate points in docs/IMPLEMENTATION_GUIDE.md, each was moved to the
# nearest spot (within about 1 km) where a ~450 m square was cultivated in at least 97% of
# Cropland Data Layer pixel-years 2016-2023; the original points were towns or station
# buildings. Each is analyzed as a ~400 m square.
TEST_FIELDS: Final = {
    "cook": ("WSU Cook Agronomy Farm, Pullman", 46.7806, -117.0913),
    "colfax": ("Colfax", 46.8820, -117.3482),
    "lacrosse": ("LaCrosse", 46.8117, -117.8723),
    "lind": ("Lind (near the WSU Dryland Research Station)", 46.9609, -118.6084),
    "dayton": ("Dayton", 46.3271, -117.9860),
}

# Offline mode (M11) serves a test field's saved live result when the drawn field's center is
# within this distance of it; farther fields fall back to the regional Palouse demo.
SAVED_RESULT_RADIUS_KM: Final = 8.0

# Candidate search area (M3) as (west, south, east, north) in degrees: the inland Pacific
# Northwest, matching the team's search.py. Default chosen while the team was away; confirm.
# The whole western US (-125, 31, -100, 49) would need an Earth Engine export to Drive.
SEARCH_BBOX: Final = (-121.0, 44.0, -116.0, 49.0)

# Grid spacing for sampling candidate locations, in meters (PRISM monthly is ~4 km).
GRID_SCALE_M: Final = 4000

# Farmland filter for candidates (M3): share of each ~4 km cell that the Cropland Data Layer
# marks "cultivated", averaged over these years. Cells below the threshold are dropped.
CDL_YEARS: Final = (2019, 2023)
MIN_CULTIVATED_FRACTION: Final = 0.3

# Day-length check (M10): candidates farther than this from the farm's latitude are dropped,
# because day length shapes crop development even where the climate matches. Within the
# inland Northwest it has no effect; it matters if the search area grows.
MAX_LATITUDE_DIFF_DEG: Final = 5.0

# Backtest (M10): find analogs for each test cell's climate "now" among every cell's
# climate "then", and check whether those places grew "then" what the test cell grows "now".
# CDL covers the inland Northwest from 2008 on, so the periods are short (5 years each).
BACKTEST_THEN_YEARS: Final = (2008, 2012)
BACKTEST_NOW_YEARS: Final = (2019, 2023)
BACKTEST_TEST_CELLS: Final = 200  # test cells sampled from the candidate cache
BACKTEST_ANALOGS: Final = 5  # top analogs (and random cells) compared per test cell
BACKTEST_EXCLUDE_KM: Final = 25.0  # skip cells this close, so "analog" isn't just "neighbor"

# Sigma dissimilarity thresholds (Mahony et al., 2017).
STRONG_SIGMA: Final = 1.0  # like a typical year at the farm
GOOD_SIGMA: Final = 2.0  # good analog
NOVEL_SIGMA: Final = 4.0  # at or above this, no real match exists ("novel climate")

# API limits.
# Fields must sit in the contiguous US (where PRISM has data) and be at most this big.
SUPPORTED_REGION_BBOX: Final = (-125.0, 24.0, -66.5, 49.5)
MAX_FIELD_AREA_KM2: Final = 50.0
DEFAULT_TOP_N: Final = 20
MAX_TOP_N: Final = 100
MAX_POLYGON_VERTICES: Final = 1000

# Bill, the Gemini assistant (M9). Bill only parses farmer text and restates results.
# Flash-Lite is the cheapest current text model; 3.5 Flash-Lite is the stable release.
GEMINI_MODEL: Final = "gemini-3.5-flash-lite"
GEMINI_THINKING_LEVEL: Final = "MINIMAL"  # Bill restates, he doesn't reason
GEMINI_TIMEOUT_MS: Final = 20_000
GEMINI_MAX_OUTPUT_TOKENS: Final = 1024
# Gemini sometimes answers 503 "high demand" (seen in the first live check). Retry server
# errors briefly; never retry timeouts (each already waited GEMINI_TIMEOUT_MS) or quota (429).
GEMINI_RETRY_CODES: Final = (500, 503, 504)
GEMINI_RETRY_DELAYS_S: Final = (1.0, 3.0)  # waits before the 2nd and 3rd attempts
MAX_FARMER_TEXT_CHARS: Final = 2000  # longer free text is cut before it reaches Gemini
BILL_TOP_ANALOGS: Final = 5  # how many analogs the summary describes
