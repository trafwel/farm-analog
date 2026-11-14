"""Project-wide settings.

Change a default here, not inside individual modules, so the analog pipeline, the API and
the docs always agree on periods, thresholds and limits.
"""

from typing import Final

# Present-day climate: PRISM normals and each farm's year-to-year variation.
BASELINE_YEARS: Final = (1991, 2020)

# Climate-model reference period. CMIP6 "historical" runs end in 2014, so the model's own
# baseline can't be 1991-2020; we use the latest 30 historical years instead.
MODEL_HISTORICAL_YEARS: Final = (1985, 2014)

# "The 2050s".
FUTURE_YEARS: Final = (2041, 2070)

DEFAULT_SCENARIO: Final = "ssp245"

# Western US search area as (west, south, east, north) in degrees.
SEARCH_BBOX: Final = (-125.0, 31.0, -100.0, 49.0)

# Grid spacing for sampling candidate locations, in meters (PRISM monthly is ~4 km).
GRID_SCALE_M: Final = 4000

# Sigma dissimilarity thresholds (Mahony et al., 2017).
STRONG_SIGMA: Final = 1.0  # like a typical year at the farm
GOOD_SIGMA: Final = 2.0  # good analog
NOVEL_SIGMA: Final = 4.0  # at or above this, no real match exists ("novel climate")

# API limits.
DEFAULT_TOP_N: Final = 20
MAX_TOP_N: Final = 100
MAX_POLYGON_VERTICES: Final = 1000
