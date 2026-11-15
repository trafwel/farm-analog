"""Project-wide settings.

Change a default here, not inside individual modules, so the analog pipeline, the API and
the docs always agree on periods, thresholds and limits.
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

# Approximate Washington Palouse demo extent as (west, south, east, north) in degrees.
# Not an official regional boundary.
PALOUSE_BOUNDS: Final = (-118.2, 46.5, -117.0, 47.2)

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

# Sigma dissimilarity thresholds (Mahony et al., 2017).
STRONG_SIGMA: Final = 1.0  # like a typical year at the farm
GOOD_SIGMA: Final = 2.0  # good analog
NOVEL_SIGMA: Final = 4.0  # at or above this, no real match exists ("novel climate")

# API limits.
DEFAULT_TOP_N: Final = 20
MAX_TOP_N: Final = 100
MAX_POLYGON_VERTICES: Final = 1000
