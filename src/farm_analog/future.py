"""The farm's climate around 2050: the delta method, across several climate models.

Climate models have biases (a model may run 2 °C too cold in the Palouse), so we never use
their raw values. Instead, for each model we measure its *change* between the reference
years and the future years, and apply that change to the farm's real PRISM climate:

- temperature: add the change (future mean minus reference mean, °C),
- precipitation: multiply by the ratio (future total over reference total), so dry places
  can't go below zero rain.

Doing this per model, rather than averaging the models first, keeps each model's own
pattern of change intact; M4 matches each model separately and counts how many agree.
Like ``farm_today``, the Earth Engine fetch is kept apart from the pure, tested logic.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from farm_analog import config, fingerprint
from farm_analog.schema import PolygonGeometry, SeasonalFingerprint

CMIP6_COLLECTION = "NASA/GDDP-CMIP6"
# Average days per calendar month, used to turn mean daily precipitation into a monthly total.
# The model's own calendar (some use 365 or 360 days) then doesn't matter, and the factor
# cancels in the future/reference ratio anyway.
DAYS_PER_MONTH = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
CLIMATOLOGY_COLUMNS = ["period", "month", "temperature_c", "precipitation_mm"]


@dataclass(frozen=True)
class QuarterlyChange:
    """One climate model's change per quarter, in ``fingerprint.QUARTERS`` order."""

    model: str
    temperature_delta_c: np.ndarray  # 4 values: add to the farm's quarterly mean temperature
    precipitation_ratio: np.ndarray  # 4 values: multiply the farm's quarterly precipitation


def check_climatology(climatology: pd.DataFrame) -> pd.DataFrame:
    """Validate a model climatology: 12 months for each of "baseline" and "future"."""
    missing = set(CLIMATOLOGY_COLUMNS) - set(climatology.columns)
    if missing:
        raise ValueError(f"climatology is missing columns: {sorted(missing)}")
    if climatology[["temperature_c", "precipitation_mm"]].isna().any().any():
        raise ValueError("climatology has missing values")
    for period in ("baseline", "future"):
        months = sorted(climatology.loc[climatology.period == period, "month"])
        if months != list(range(1, 13)):
            raise ValueError(f"{period} needs exactly one row per month 1-12, got {months}")
    return climatology


def quarterly_change(climatology: pd.DataFrame, model: str) -> QuarterlyChange:
    """A model's quarterly change, from its monthly baseline and future climatology.

    ``climatology`` has columns ``period`` ("baseline"/"future"), ``month`` (1-12),
    ``temperature_c`` (monthly mean) and ``precipitation_mm`` (monthly total) - the same
    layout as the team's ``palouse_climate_*.csv`` sample.
    """
    check_climatology(climatology)
    deltas, ratios = [], []
    for first, last in fingerprint.QUARTERS.values():
        part = climatology[climatology.month.between(first, last)]
        baseline = part[part.period == "baseline"]
        future = part[part.period == "future"]
        deltas.append(future.temperature_c.mean() - baseline.temperature_c.mean())
        denominator = baseline.precipitation_mm.sum()
        if denominator <= 0:
            raise ValueError(f"{model}: cannot apply a rainfall ratio to a zero baseline")
        ratios.append(future.precipitation_mm.sum() / denominator)
    return QuarterlyChange(model, np.array(deltas), np.array(ratios))


def apply_delta(normal, change: QuarterlyChange) -> np.ndarray:
    """The farm's future fingerprint: add temperature changes, multiply precipitation."""
    future = np.array(normal, dtype=float, copy=True)
    if future.shape != (len(fingerprint.FEATURES),):
        raise ValueError(f"expected {len(fingerprint.FEATURES)} values, got {future.shape}")
    for q in range(len(fingerprint.QUARTERS)):
        future[2 * q] += change.temperature_delta_c[q]
        future[2 * q + 1] *= change.precipitation_ratio[q]
    return future


@dataclass(frozen=True)
class FarmFuture:
    """The farm's future fingerprint under each climate model, plus the ensemble view."""

    per_model: dict[str, np.ndarray]  # model -> fingerprint, FEATURES order
    scenario: str
    future_years: tuple[int, int]
    failed_models: dict[str, str] = field(default_factory=dict)  # model -> reason

    @property
    def models(self) -> list[str]:
        return list(self.per_model)

    @property
    def matrix(self) -> np.ndarray:
        """Models x features."""
        return np.vstack(list(self.per_model.values()))

    @property
    def median(self) -> np.ndarray:
        """The middle model for each value: the headline future, robust to one odd model."""
        return np.median(self.matrix, axis=0)

    @property
    def low(self) -> np.ndarray:
        return self.matrix.min(axis=0)

    @property
    def high(self) -> np.ndarray:
        return self.matrix.max(axis=0)

    @property
    def headline(self) -> SeasonalFingerprint:
        """The ensemble median in contract form (``AnalogResult.farm_future``)."""
        return fingerprint.to_contract(self.median)


def farm_future(
    normal,
    changes: list[QuarterlyChange],
    scenario: str = config.DEFAULT_SCENARIO,
    future_years: tuple[int, int] = config.FUTURE_YEARS,
    failed_models: dict[str, str] | None = None,
) -> FarmFuture:
    """Apply each model's change to the farm's present-day normal fingerprint."""
    if not changes:
        raise ValueError("need at least one climate model")
    names = [c.model for c in changes]
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate models: {names}")
    return FarmFuture(
        per_model={c.model: apply_delta(normal, c) for c in changes},
        scenario=scenario,
        future_years=future_years,
        failed_models=dict(failed_models or {}),
    )


# ---------------------------------------------------------------------------
# Earth Engine (needs login and network)
# ---------------------------------------------------------------------------


def fetch_model_climatology(
    field: PolygonGeometry,
    model: str,
    scenario: str = config.DEFAULT_SCENARIO,
    baseline_years: tuple[int, int] = config.MODEL_HISTORICAL_YEARS,
    future_years: tuple[int, int] = config.FUTURE_YEARS,
) -> pd.DataFrame:
    """One model's monthly climatology at the field, for both periods, in one request."""
    from farm_analog.earthengine import field_geometry, initialize, reduce_field

    ee = initialize()
    area = field_geometry(ee, field)
    base = ee.ImageCollection(CMIP6_COLLECTION).filter(ee.Filter.eq("model", model))
    features = []
    for period, run, (first, last) in [
        ("baseline", "historical", baseline_years),
        ("future", scenario, future_years),
    ]:
        images = base.filter(ee.Filter.eq("scenario", run)).filterDate(
            f"{first}-01-01", f"{last + 1}-01-01"
        )
        expected_days = 365.25 * (last - first + 1)
        count = images.size().getInfo()
        if count < 0.95 * expected_days:  # allows 360/365-day model calendars
            raise ValueError(f"{model} {run}: only {count} daily images for {first}-{last}")
        projection = images.first().select("tas").projection()
        for month in range(1, 13):
            monthly = images.filter(ee.Filter.calendarRange(month, month, "month"))
            image = (
                monthly.select("tas")
                .mean()
                .subtract(273.15)
                .rename("temperature_c")
                .addBands(
                    monthly.select("pr")
                    .mean()
                    .multiply(86400 * DAYS_PER_MONTH[month - 1])
                    .rename("precipitation_mm")
                )
            )
            values, support = reduce_field(ee, image, area, projection, "temperature_c")
            features.append(
                ee.Feature(None, values).set({"period": period, "month": month, "support": support})
            )
    rows = [f["properties"] for f in ee.FeatureCollection(features).getInfo()["features"]]
    frame = pd.DataFrame(rows)
    return check_climatology(frame[CLIMATOLOGY_COLUMNS + ["support"]])


def farm_future_for_field(
    field: PolygonGeometry,
    normal,
    models: list[str] = config.CLIMATE_MODELS,
    scenario: str = config.DEFAULT_SCENARIO,
    min_models: int = 3,
) -> FarmFuture:
    """Fetch every model's change at the field and apply it to the farm's normal fingerprint.

    A model that fails (missing data, a timeout) is recorded in ``failed_models`` rather than
    stopping the run; at least ``min_models`` must succeed.
    """
    changes, failed = [], {}
    for model in models:
        try:
            climatology = fetch_model_climatology(field, model, scenario)
            changes.append(quarterly_change(climatology, model))
        except Exception as exc:  # one model's data problem shouldn't sink the ensemble
            failed[model] = str(exc)
    if len(changes) < min_models:
        raise RuntimeError(f"only {len(changes)} models succeeded (need {min_models}): {failed}")
    return farm_future(normal, changes, scenario, failed_models=failed)
