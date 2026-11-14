"""The climate fingerprint: eight numbers that describe a place's climate for matching.

For each calendar quarter (Jan-Mar, Apr-Jun, Jul-Sep, Oct-Dec):

- average temperature: the mean of the quarter's three monthly mean temperatures (°C),
- total precipitation: the sum of the quarter's three monthly totals (mm).

Every part of the app uses this one definition: the farm's own climate (``farm_today``),
the candidate locations (``search``), the future climate (M2) and the JSON contract. Eight
numbers rather than more keeps the year-to-year statistics stable: sigma dissimilarity
estimates how the numbers vary together from only 20 reference years, and that estimate
gets unreliable as the number of values approaches the number of years.
"""

import numpy as np
import pandas as pd

from farm_analog.schema import SeasonalFingerprint

# Quarter code -> (first month, last month). Order matters: it fixes the feature order.
QUARTERS = {"jfm": (1, 3), "amj": (4, 6), "jas": (7, 9), "ond": (10, 12)}
QUARTER_LABELS = {"jfm": "Jan–Mar", "amj": "Apr–Jun", "jas": "Jul–Sep", "ond": "Oct–Dec"}

# Internal feature names, in the order the analog search and its cached data use.
FEATURES = [
    f"{kind}_{q}" for q in range(len(QUARTERS)) for kind in ("temperature", "precipitation")
]

# Feature name -> field name in the JSON contract (schema.SeasonalFingerprint).
CONTRACT_FIELDS = {}
for _i, _code in enumerate(QUARTERS):
    CONTRACT_FIELDS[f"temperature_{_i}"] = f"tmean_{_code}"
    CONTRACT_FIELDS[f"precipitation_{_i}"] = f"ppt_{_code}"


def yearly_fingerprints(monthly: pd.DataFrame) -> pd.DataFrame:
    """One fingerprint per year from monthly values.

    ``monthly`` needs columns ``year``, ``month`` (1-12), ``tmean`` (°C) and ``ppt`` (mm),
    with exactly one row per month and all 12 months for every year. Returns a DataFrame
    indexed by year with columns ``FEATURES``.
    """
    required = {"year", "month", "tmean", "ppt"}
    missing = required - set(monthly.columns)
    if missing:
        raise ValueError(f"monthly data is missing columns: {sorted(missing)}")
    if monthly.duplicated(["year", "month"]).any():
        raise ValueError("monthly data has duplicate (year, month) rows")
    if not monthly["month"].between(1, 12).all():
        raise ValueError("months must be 1-12")
    if monthly[["tmean", "ppt"]].isna().any().any():
        raise ValueError("monthly data has missing values; a fingerprint needs every month")
    counts = monthly.groupby("year")["month"].nunique()
    incomplete = counts[counts != 12]
    if len(incomplete):
        raise ValueError(f"years without all 12 months: {incomplete.index.tolist()}")

    rows = {}
    for year, months in monthly.groupby("year"):
        values = []
        for first, last in QUARTERS.values():
            quarter = months[months["month"].between(first, last)]
            values += [quarter["tmean"].mean(), quarter["ppt"].sum()]
        rows[int(year)] = values
    return pd.DataFrame.from_dict(rows, orient="index", columns=FEATURES).sort_index()


def normal(yearly: pd.DataFrame) -> np.ndarray:
    """The average fingerprint across years, in ``FEATURES`` order."""
    return yearly[FEATURES].to_numpy().mean(axis=0)


def to_contract(vector) -> SeasonalFingerprint:
    """Convert a vector in ``FEATURES`` order to the contract's named fields."""
    vector = np.asarray(vector, dtype=float)
    if vector.shape != (len(FEATURES),):
        raise ValueError(f"expected {len(FEATURES)} values, got shape {vector.shape}")
    return SeasonalFingerprint(
        **{CONTRACT_FIELDS[f]: float(v) for f, v in zip(FEATURES, vector, strict=True)}
    )


def from_contract(fingerprint: SeasonalFingerprint) -> np.ndarray:
    """Convert the contract's named fields back to a vector in ``FEATURES`` order."""
    return np.array([getattr(fingerprint, CONTRACT_FIELDS[f]) for f in FEATURES], dtype=float)
