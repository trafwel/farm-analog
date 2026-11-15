"""A farm's climate today: its fingerprint and how that fingerprint varies year to year.

Two halves, kept apart on purpose:

- ``fetch_prism_monthly`` talks to Earth Engine (needs login and network) and returns plain
  records: one per month, with the field's mean temperature and precipitation.
- ``records_to_monthly`` and ``farm_today`` are pure Python on those records, so they're
  tested without Earth Engine, and the same records can be cached and replayed.

The yearly fingerprints are what sigma dissimilarity needs: they show how much each value,
and each combination of values, normally swings at this farm.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from farm_analog import config, fingerprint
from farm_analog.schema import PolygonGeometry, SeasonalFingerprint


@dataclass(frozen=True)
class FarmToday:
    """The farm's present-day climate over the reference years."""

    normal: SeasonalFingerprint  # average fingerprint (for the contract and the app)
    yearly: pd.DataFrame  # one fingerprint per year, columns fingerprint.FEATURES
    years: tuple[int, int]
    support: str  # "field_mean" or "centroid_cell" (see fetch_prism_monthly)

    @property
    def yearly_matrix(self) -> np.ndarray:
        """Years x features array, the input sigma dissimilarity expects."""
        return self.yearly[fingerprint.FEATURES].to_numpy()


def records_to_monthly(records: list[dict], years: tuple[int, int]) -> pd.DataFrame:
    """Turn Earth Engine records into a tidy monthly table, checking it's complete.

    Each record needs ``date`` ("YYYY-MM"), ``tmean`` (°C) and ``ppt`` (mm).
    """
    if not records:
        raise ValueError("no monthly records")
    frame = pd.DataFrame(records)
    missing = {"date", "tmean", "ppt"} - set(frame.columns)
    if missing:
        raise ValueError(f"records are missing fields: {sorted(missing)}")
    dates = pd.to_datetime(frame["date"], format="%Y-%m")
    monthly = pd.DataFrame(
        {
            "year": dates.dt.year,
            "month": dates.dt.month,
            "tmean": pd.to_numeric(frame["tmean"], errors="coerce"),
            "ppt": pd.to_numeric(frame["ppt"], errors="coerce"),
        }
    )
    first, last = years
    outside = monthly[~monthly["year"].between(first, last)]
    if len(outside):
        raise ValueError(f"records outside {first}-{last}: {sorted(outside.year.unique())}")
    expected = 12 * (last - first + 1)
    if len(monthly) != expected:
        raise ValueError(f"expected {expected} months for {first}-{last}, got {len(monthly)}")
    return monthly.sort_values(["year", "month"]).reset_index(drop=True)


def farm_today(monthly: pd.DataFrame, years: tuple[int, int], support: str) -> FarmToday:
    """Fingerprint and year-to-year variation from a complete monthly table."""
    yearly = fingerprint.yearly_fingerprints(monthly)
    n_years, n_features = yearly.shape
    if n_years <= n_features:
        raise ValueError(f"need more years ({n_years}) than fingerprint values ({n_features})")
    return FarmToday(
        normal=fingerprint.to_contract(fingerprint.normal(yearly)),
        yearly=yearly,
        years=years,
        support=support,
    )


def fetch_prism_monthly(
    field: PolygonGeometry, years: tuple[int, int] = config.BASELINE_YEARS
) -> tuple[list[dict], str]:
    """Monthly PRISM mean temperature and precipitation for a field, from Earth Engine.

    Averages every PRISM cell (~4 km) whose center falls inside the field. Most fields are
    smaller than one cell, so when no cell center is inside, it uses the cell under the
    field's center instead. Returns (records, support), where support says which was used.
    Needs ``EE_PROJECT`` in ``.env`` and ``earthengine authenticate``.
    """
    from farm_analog.earthengine import field_geometry, initialize, reduce_field

    ee = initialize()
    first, last = years
    source = (
        ee.ImageCollection(config.PRISM_COLLECTION)
        .filter(ee.Filter.eq("dataset_type", config.PRISM_DATASET_TYPE))
        .filterDate(f"{first}-01-01", f"{last + 1}-01-01")
        .select(["tmean", "ppt"])
    )
    expected = 12 * (last - first + 1)
    count = source.size().getInfo()
    if count != expected:
        raise ValueError(f"expected {expected} PRISM months for {first}-{last}, found {count}")
    native = source.first().select("tmean").projection()
    area = field_geometry(ee, field)

    def summarize(item):
        image = ee.Image(item)
        values, support = reduce_field(ee, image, area, native, "tmean")
        return ee.Feature(None, values).set(
            {"date": image.date().format("YYYY-MM"), "support": support}
        )

    features = ee.FeatureCollection(source.toList(count).map(summarize)).getInfo()["features"]
    records = [f["properties"] for f in features]
    supports = {r.pop("support") for r in records}
    support = supports.pop() if len(supports) == 1 else "mixed"
    return records, support


def farm_today_for_field(
    field: PolygonGeometry, years: tuple[int, int] = config.BASELINE_YEARS
) -> FarmToday:
    """Fetch PRISM for a field and build its present-day climate (needs Earth Engine)."""
    records, support = fetch_prism_monthly(field, years)
    return farm_today(records_to_monthly(records, years), years, support)
