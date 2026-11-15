"""Hazard history and field conditions (M13): heat stress, frost, extreme rain, soil
moisture and bare-field months from NASA Earth observations.

An analog's hazard history today previews the farm's future, so each analog's numbers are
compared with the farm's own numbers today. As in evidence.py, the arithmetic lives in plain
functions tested offline, and Earth Engine is used only to fetch raw numbers:

- heat days and frost dates: PRISM daily tmax/tmin (~4 km) over ``HAZARD_YEARS``;
- extreme rain: NASA GPM IMERG V07 half-hourly rain, summed into UTC days, over
  ``IMERG_YEARS`` (a shorter, recent window; see the note at ``IMERG_YEARS``);
- soil moisture: NASA SMAP L4 root-zone moisture (~9 km), monthly means over ``SMAP_YEARS``;
- field greenness: Landsat 8/9 Collection 2 Level 2 NDVI within ``NDVI_BUFFER_M`` of the
  point, cloud-masked, over ``NDVI_YEARS``; months whose median NDVI is low are "bare".

Each source is fetched on its own: if one fails (timeout, missing asset), its fields stay
None and the reason goes into ``HazardProfile.missing``; ``fetch_hazards`` never raises.

Data flow:
Inputs:  a list of (key, lon, lat) points (the farm and its analogs); from Earth Engine:
         PRISM daily tmax/tmin (OREGONSTATE/PRISM/AN81d, 1995-2014), GPM IMERG V07
         (NASA/GPM_L3/IMERG_V07, 2014-2023), SMAP L4 sm_rootzone (NASA/SMAP/SPL4SMGP/008,
         2016-2023), Landsat 8/9 C2 L2 surface reflectance (2019-2023) and ECOSTRESS
         L2T LSTE V2 surface temperature (NASA/ECOSTRESS/L2T_LSTE/V2, 2018-2025, M17).
Outputs: dict key -> HazardProfile (heat days, frost dates, extreme rain, 12 monthly soil
         moisture and NDVI values, bare months, and a ``missing`` list); ``compare`` turns a
         farm and an analog profile into farm/analog/change numbers.
         ``add_hazards`` attaches them to an AnalogResult as schema.Hazards
         (``farm_hazards`` and each top analog's ``hazards``).
Used by: pipeline._analyze_live (wrapped so a failure only adds a note); the frontend and
         Bill read the hazard fields from the result.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, fields, replace

import numpy as np
import pandas as pd

from farm_analog import config

HEAT_THRESHOLD_C = 32.0  # ~90 F, a common heat-stress threshold for wheat at flowering
FROST_THRESHOLD_C = 0.0  # frost: daily minimum at or below freezing
EXTREME_RAIN_MM = 25.0  # ~1 inch in a day
BARE_NDVI = 0.25  # below this, mostly bare soil or stubble
MID_YEAR_DOY = 182  # ~1 July: frosts before are "spring", from here on "fall"

PRISM_DAILY_COLLECTION = "OREGONSTATE/PRISM/AN81d"
HAZARD_YEARS = config.BASELINE_YEARS  # same 1995-2014 present day as the climate match

# IMERG V07 in Earth Engine is half-hourly only (no daily product; the monthly product
# can't count days), so daily totals are summed on the server from 48 images per day.
# A full 2001-2023 window is ~400k images and too slow for a live request, so we use a
# recent 10 years. Days are UTC, not local, so a storm spanning ~5 pm local can be split.
IMERG_COLLECTION = "NASA/GPM_L3/IMERG_V07"
IMERG_BAND = "precipitation"  # mm/hr, half-hourly
IMERG_YEARS = (2014, 2023)

SMAP_COLLECTION = "NASA/SMAP/SPL4SMGP/008"
SMAP_BAND = "sm_rootzone"  # volumetric, m3/m3, 0-100 cm
SMAP_YEARS = (2016, 2023)
SMAP_SCALE_M = 9000
SMAP_HOUR_UTC = 1  # keep the 01:30 UTC snapshot of each day

LANDSAT_COLLECTIONS = ("LANDSAT/LC08/C02/T1_L2", "LANDSAT/LC09/C02/T1_L2")
NDVI_YEARS = (2019, 2023)
NDVI_BUFFER_M = 200
NDVI_MIN_PIXELS = 30  # a 200 m circle holds ~140 Landsat pixels; skip mostly-cloudy scenes
# QA_PIXEL bits masked out: fill (0), dilated cloud (1), cirrus (2), cloud (3), shadow (4),
# snow (5; snow would read as bare ground).
LANDSAT_QA_MASK = 0b111111

SOURCE_TIMEOUT_S = 180

# ECOSTRESS (M17): land-surface temperature at 70 m from the space station, so the only
# field-scale heat number here. Passes come at any hour; we keep clear-sky summer afternoons
# (18-23 UTC = 11 am-4 pm Pacific daylight time) over cultivated pixels within 1 km of the
# point. June (crops still green, grain fill) and July-August (mostly stubble and fallow
# after harvest) are reported apart, because bare ground reads far hotter than a crop.
ECOSTRESS_COLLECTION = "NASA/ECOSTRESS/L2T_LSTE/V2"
ECOSTRESS_YEARS = (2018, 2025)  # data start in July 2018
ECOSTRESS_HOURS_UTC = (18, 23)
ECOSTRESS_BUFFER_M = 1000
ECOSTRESS_MIN_PIXELS = 20  # cropland pixels with a clear reading, per pass and point
CDL_CULTIVATED_YEARS = (2019, 2023)  # same years as the candidate cells' cropland mask



# ---------------------------------------------------------------------------
# Pure functions (tested offline)
# ---------------------------------------------------------------------------


def _check_daily(series: pd.Series) -> pd.Series:
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("expected a pandas Series with a DatetimeIndex")
    return series.dropna()


def heat_days(daily_tmax_c: pd.Series, threshold_c: float = HEAT_THRESHOLD_C) -> float | None:
    """Mean days per year with a daily maximum above ``threshold_c``."""
    s = _check_daily(daily_tmax_c)
    if s.empty:
        return None
    return float((s > threshold_c).groupby(s.index.year).sum().mean())


@dataclass(frozen=True)
class FrostDates:
    last_spring_doy: float | None  # mean day-of-year of the last frost before MID_YEAR_DOY
    first_fall_doy: float | None  # mean day-of-year of the first frost from MID_YEAR_DOY on
    frost_free_days: float | None  # mean (first fall - last spring), years with both


def frost_dates(daily_tmin_c: pd.Series, threshold_c: float = FROST_THRESHOLD_C) -> FrostDates:
    """Mean last spring frost, first fall frost and frost-free season (tmin <= threshold).

    A year without a spring (or fall) frost is left out of that mean, as on the server.
    """
    s = _check_daily(daily_tmin_c)
    doy = pd.Series(s.index.day_of_year, index=s.index)
    frost = doy[s <= threshold_c]
    spring = frost[frost < MID_YEAR_DOY].groupby(frost[frost < MID_YEAR_DOY].index.year).max()
    fall = frost[frost >= MID_YEAR_DOY].groupby(frost[frost >= MID_YEAR_DOY].index.year).min()
    season = (fall - spring).dropna()

    def mean(values):
        return float(values.mean()) if len(values) else None

    return FrostDates(mean(spring), mean(fall), mean(season))


def extreme_rain_days(
    daily_precip_mm: pd.Series, threshold_mm: float = EXTREME_RAIN_MM
) -> tuple[float | None, float | None]:
    """(mean days per year with at least ``threshold_mm``, mean yearly max 1-day total)."""
    s = _check_daily(daily_precip_mm)
    if s.empty:
        return None, None
    by_year = s.groupby(s.index.year)
    return float((s >= threshold_mm).groupby(s.index.year).sum().mean()), float(
        by_year.max().mean()
    )


def _by_month(series: pd.Series, how: str) -> list[float | None]:
    s = series.dropna()
    months = s.index.month if isinstance(s.index, pd.DatetimeIndex) else s.index.astype(int)
    values = s.groupby(months).agg(how).reindex(range(1, 13))
    return [None if pd.isna(v) else float(v) for v in values]


def monthly_soil_moisture(series: pd.Series) -> list[float | None]:
    """12 monthly means (Jan-Dec; None for a month with no data)."""
    return _by_month(series, "mean")


def monthly_medians(series: pd.Series) -> list[float | None]:
    """12 monthly medians (Jan-Dec; None for a month with no data)."""
    return _by_month(series, "median")


def bare_months(monthly_ndvi: pd.Series, threshold: float = BARE_NDVI) -> list[int]:
    """Months (1-12) whose median NDVI is below ``threshold`` (likely bare soil or stubble).

    Takes NDVI values indexed by date (any number per month, from any years) or by month.
    """
    medians = monthly_medians(monthly_ndvi)
    return [m for m, v in enumerate(medians, start=1) if v is not None and v < threshold]


def surface_temperature(passes: pd.Series) -> dict:
    """June and July-August median afternoon surface temperature (°C) from ECOSTRESS passes.

    ``passes``: one mean cropland temperature per pass, indexed by pass time. Overlapping map
    tiles deliver the same pass twice, so repeated times count once. Returns the two medians
    (None for a period with no pass) and the number of distinct passes.
    """
    if passes.empty:
        return {"surface_temp_june_c": None, "surface_temp_julaug_c": None, "surface_passes": 0}
    s = passes[~passes.index.duplicated(keep="first")].dropna()
    months = pd.DatetimeIndex(s.index).month
    june, julaug = s[months == 6], s[(months == 7) | (months == 8)]

    def median(x):
        return round(float(x.median()), 1) if len(x) else None

    return {"surface_temp_june_c": median(june), "surface_temp_julaug_c": median(julaug),
            "surface_passes": int(len(s))}


@dataclass
class HazardProfile:
    """Hazard history and field conditions at one point; any number may be missing."""

    heat_days: float | None = None  # days/year with tmax > HEAT_THRESHOLD_C
    last_spring_frost_doy: float | None = None
    first_fall_frost_doy: float | None = None
    frost_free_days: float | None = None
    extreme_rain_days: float | None = None  # days/year with >= EXTREME_RAIN_MM
    max_1day_rain_mm: float | None = None  # mean of each year's wettest day
    soil_moisture_monthly: list[float | None] | None = None  # m3/m3, Jan-Dec
    ndvi_monthly: list[float | None] | None = None  # median NDVI, Jan-Dec
    bare_months: list[int] | None = None
    surface_temp_june_c: float | None = None  # median afternoon cropland surface temp, June
    surface_temp_julaug_c: float | None = None  # same, July-August
    surface_passes: int | None = None  # clear afternoon ECOSTRESS passes used
    missing: list[str] = field(default_factory=list)  # "source: reason" for failed sources


SCALAR_FIELDS = (
    "heat_days",
    "last_spring_frost_doy",
    "first_fall_frost_doy",
    "frost_free_days",
    "extreme_rain_days",
    "max_1day_rain_mm",
    "surface_temp_june_c",
    "surface_temp_julaug_c",
)
DIGITS = {"extreme_rain_days": 1, "max_1day_rain_mm": 1, "surface_temp_june_c": 1,
          "surface_temp_julaug_c": 1}  # others: whole days


def _rounded(value, digits):
    return None if value is None else round(float(value), digits) + 0.0  # no "-0.0"


def compare(farm: HazardProfile, analog: HazardProfile) -> dict:
    """Farm-today vs analog-today numbers, ready for plain-language text.

    Scalars become ``{"farm", "analog", "change"}`` (change = analog - farm). Monthly soil
    moisture gets a per-month change; bare months get the months gained and lost. A field
    missing on either side is left out.
    """
    out = {}
    for name in SCALAR_FIELDS:
        a, b = getattr(farm, name), getattr(analog, name)
        if a is None or b is None:
            continue
        digits = DIGITS.get(name, 0)
        out[name] = {
            "farm": _rounded(a, digits),
            "analog": _rounded(b, digits),
            "change": _rounded(b - a, digits),
        }
    if farm.soil_moisture_monthly and analog.soil_moisture_monthly:
        a, b = farm.soil_moisture_monthly, analog.soil_moisture_monthly
        out["soil_moisture_monthly"] = {
            "farm": [_rounded(v, 3) for v in a],
            "analog": [_rounded(v, 3) for v in b],
            "change": [
                None if x is None or y is None else round(y - x, 3)
                for x, y in zip(a, b, strict=True)
            ],
        }
    if farm.bare_months is not None and analog.bare_months is not None:
        a, b = set(farm.bare_months), set(analog.bare_months)
        out["bare_months"] = {
            "farm": sorted(a),
            "analog": sorted(b),
            "added": sorted(b - a),
            "removed": sorted(a - b),
        }
    return out


def merge(base: HazardProfile, update: HazardProfile) -> HazardProfile:
    """``base`` with every non-None field of ``update`` filled in; missing lists combined."""
    changes = {
        f.name: getattr(update, f.name)
        for f in fields(HazardProfile)
        if f.name != "missing" and getattr(update, f.name) is not None
    }
    return replace(base, **changes, missing=base.missing + update.missing)


def _number(value, digits: int = 2) -> float | None:
    """A rounded float from an Earth Engine value (None if missing or not finite)."""
    if value is None:
        return None
    value = float(value)
    return round(value, digits) if np.isfinite(value) else None


# ---------------------------------------------------------------------------
# Earth Engine (needs login and network)
# ---------------------------------------------------------------------------


def _points_fc(ee, points):
    return ee.FeatureCollection(
        [ee.Feature(ee.Geometry.Point([lon, lat]), {"key": str(key)}) for key, lon, lat in points]
    )


def _by_key(ee_result) -> dict[str, dict]:
    return {f["properties"]["key"]: f["properties"] for f in ee_result.getInfo()["features"]}


def _years_filter(ee, years):
    return ee.Filter.date(f"{years[0]}-01-01", f"{years[1] + 1}-01-01")


def fetch_heat_frost(ee, points, years=HAZARD_YEARS) -> dict[str, HazardProfile]:
    """Heat days and frost dates from PRISM daily, all computed on the server."""
    prism = ee.ImageCollection(PRISM_DAILY_COLLECTION).filter(_years_filter(ee, years))
    n_years = years[1] - years[0] + 1
    heat = (
        prism.select("tmax")
        .map(lambda img: img.gt(HEAT_THRESHOLD_C))
        .sum()
        .divide(n_years)
        .rename("heat_days")
    )

    def frost_doy(img):
        doy = ee.Number.parse(img.date().format("D"))
        frost = img.select("tmin").lte(FROST_THRESHOLD_C)
        return ee.Image.constant(doy).toInt().rename("doy").updateMask(frost)

    yearly = []
    for year in range(years[0], years[1] + 1):
        days = prism.filter(ee.Filter.calendarRange(year, year, "year"))
        spring = days.filter(ee.Filter.dayOfYear(1, MID_YEAR_DOY - 1)).map(frost_doy).max()
        fall = days.filter(ee.Filter.dayOfYear(MID_YEAR_DOY, 366)).map(frost_doy).min()
        spring, fall = spring.rename("spring"), fall.rename("fall")
        season = fall.subtract(spring).rename("season")
        yearly.append(spring.addBands(fall).addBands(season).toFloat())
    frost = ee.ImageCollection.fromImages(yearly).mean()

    image = heat.addBands(frost)
    values = _by_key(
        image.reduceRegions(
            collection=_points_fc(ee, points),
            reducer=ee.Reducer.first(),
            crs=prism.first().select("tmax").projection(),
        )
    )
    out = {}
    for key, _, _ in points:
        p = values.get(str(key), {})
        out[str(key)] = HazardProfile(
            heat_days=_number(p.get("heat_days")),
            last_spring_frost_doy=_number(p.get("spring")),
            first_fall_frost_doy=_number(p.get("fall")),
            frost_free_days=_number(p.get("season")),
        )
    return out


def _imerg_year(ee, fc, year):
    """One year of IMERG on the server: (count of days >= EXTREME_RAIN_MM, wettest day)."""
    imerg = (
        ee.ImageCollection(IMERG_COLLECTION)
        .filterDate(f"{year}-01-01", f"{year + 1}-01-01")
        .select(IMERG_BAND)
    )
    start = ee.Date(f"{year}-01-01")
    n_days = ee.Date(f"{year + 1}-01-01").difference(start, "day")

    def daily(offset):
        day = start.advance(offset, "day")
        # Half-hourly rates in mm/hr: each image is half an hour of rain.
        return imerg.filterDate(day, day.advance(1, "day")).sum().multiply(0.5).rename("rain")

    days = ee.ImageCollection.fromImages(ee.List.sequence(0, n_days.subtract(1)).map(daily))
    image = days.map(lambda img: img.gte(EXTREME_RAIN_MM)).sum().rename("wet")
    image = image.addBands(days.max().rename("rain_max"))
    return _by_key(
        image.reduceRegions(
            collection=fc,
            reducer=ee.Reducer.first(),
            crs=ee.Image(imerg.first()).projection(),
        )
    )


def _mean(values) -> float | None:
    values = [v for v in values if v is not None]
    return float(np.mean(values)) if values else None


def fetch_extreme_rain(ee, points, years=IMERG_YEARS) -> dict[str, HazardProfile]:
    """Extreme-rain days and the mean yearly wettest day from IMERG, summed into UTC days.

    Ten years in one request exceeds Earth Engine's memory limit, so each year is its own
    request (run in parallel) and the years are averaged here.
    """
    fc = _points_fc(ee, points)
    year_list = range(years[0], years[1] + 1)
    with ThreadPoolExecutor(max_workers=len(year_list)) as pool:
        per_year = list(pool.map(lambda y: _imerg_year(ee, fc, y), year_list))
    out = {}
    for key, _, _ in points:
        rows = [year.get(str(key), {}) for year in per_year]
        out[str(key)] = HazardProfile(
            extreme_rain_days=_mean(_number(r.get("wet")) for r in rows),
            max_1day_rain_mm=_mean(_number(r.get("rain_max")) for r in rows),
        )
    return out


def fetch_soil_moisture(ee, points, years=SMAP_YEARS) -> dict[str, HazardProfile]:
    """Monthly mean SMAP L4 root-zone soil moisture (12 values) at each point.

    SMAP L4 is 3-hourly; averaging all ~23k images exceeds Earth Engine's memory limit, so
    we keep one snapshot a day (``SMAP_HOUR_UTC``; root-zone moisture changes slowly) and
    fetch three months per request, in parallel.
    """
    smap = (
        ee.ImageCollection(SMAP_COLLECTION)
        .filter(_years_filter(ee, years))
        .filter(ee.Filter.calendarRange(SMAP_HOUR_UTC, SMAP_HOUR_UTC, "hour"))
        .select(SMAP_BAND)
    )
    fc = _points_fc(ee, points)

    def quarter(months):
        image = ee.Image.cat(
            [
                smap.filter(ee.Filter.calendarRange(m, m, "month")).mean().rename(f"m{m:02d}")
                for m in months
            ]
        )
        return _by_key(
            image.reduceRegions(collection=fc, reducer=ee.Reducer.first(), scale=SMAP_SCALE_M)
        )

    quarters = [range(q, q + 3) for q in (1, 4, 7, 10)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        parts = list(pool.map(quarter, quarters))
    out = {}
    for key, _, _ in points:
        p = {k: v for part in parts for k, v in part.get(str(key), {}).items()}
        months = [_number(p.get(f"m{m:02d}"), 3) for m in range(1, 13)]
        out[str(key)] = HazardProfile(
            soil_moisture_monthly=None if all(v is None for v in months) else months
        )
    return out


def fetch_ndvi_scenes(ee, points, years=NDVI_YEARS) -> dict[str, pd.Series]:
    """Per-scene mean NDVI within ``NDVI_BUFFER_M`` of each point (cloud-masked Landsat 8/9),
    as a Series indexed by scene date."""
    fc = _points_fc(ee, points)
    buffered = fc.map(lambda f: f.buffer(NDVI_BUFFER_M))
    landsat = ee.ImageCollection(LANDSAT_COLLECTIONS[0])
    for asset in LANDSAT_COLLECTIONS[1:]:
        landsat = landsat.merge(ee.ImageCollection(asset))
    landsat = landsat.filter(_years_filter(ee, years)).filterBounds(fc.geometry())
    reducer = ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True)

    def scene(img):
        clear = img.select("QA_PIXEL").bitwiseAnd(LANDSAT_QA_MASK).eq(0)
        sr = img.select(["SR_B4", "SR_B5"]).multiply(0.0000275).add(-0.2)
        ndvi = sr.normalizedDifference(["SR_B5", "SR_B4"]).rename("ndvi").updateMask(clear)
        stats = ndvi.reduceRegions(collection=buffered, reducer=reducer, scale=30)
        return stats.map(lambda f: f.set("t", img.get("system:time_start")).setGeometry(None))

    rows = (
        landsat.map(scene)
        .flatten()
        .filter(ee.Filter.gte("count", NDVI_MIN_PIXELS))
        .reduceColumns(ee.Reducer.toList(3), ["key", "t", "mean"])
        .get("list")
        .getInfo()
    )
    out = {str(key): pd.Series(dtype=float) for key, _, _ in points}
    frame = pd.DataFrame(rows, columns=["key", "t", "ndvi"])
    for key, group in frame.groupby("key"):
        out[key] = pd.Series(
            group["ndvi"].to_numpy(dtype=float), index=pd.to_datetime(group["t"], unit="ms")
        ).sort_index()
    return out


def fetch_greenness(ee, points, years=NDVI_YEARS) -> dict[str, HazardProfile]:
    """Monthly median NDVI and bare months at each point."""
    out = {}
    for key, series in fetch_ndvi_scenes(ee, points, years).items():
        if series.empty:
            out[key] = HazardProfile(missing=["landsat_ndvi: no clear scenes"])
            continue
        out[key] = HazardProfile(
            ndvi_monthly=[_rounded(v, 3) for v in monthly_medians(series)],
            bare_months=bare_months(series),
        )
    return out


def fetch_surface_temperature(ee, points, years=ECOSTRESS_YEARS) -> dict[str, HazardProfile]:
    """ECOSTRESS afternoon surface temperature over cropland near each point (M17)."""
    fc = _points_fc(ee, points)
    buffered = fc.map(lambda f: f.buffer(ECOSTRESS_BUFFER_M))
    cropland = (
        ee.ImageCollection("USDA/NASS/CDL")
        .filter(_years_filter(ee, CDL_CULTIVATED_YEARS))
        .select("cultivated")
        .mode()
        .eq(2)
    )
    passes = (
        ee.ImageCollection(ECOSTRESS_COLLECTION)
        .filterBounds(fc.geometry())
        .filter(_years_filter(ee, years))
        .filter(ee.Filter.calendarRange(6, 8, "month"))
        .filter(ee.Filter.calendarRange(*ECOSTRESS_HOURS_UTC, "hour"))
    )
    reducer = ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True)

    def one_pass(img):
        clear = img.select("cloud").eq(0)
        lst = img.select("LST").subtract(273.15).rename("lst")
        lst = lst.updateMask(clear).updateMask(cropland)
        stats = lst.reduceRegions(collection=buffered, reducer=reducer, scale=70)
        return stats.map(lambda f: f.set("t", img.get("system:time_start")).setGeometry(None))

    rows = (
        passes.map(one_pass)
        .flatten()
        .filter(ee.Filter.gte("count", ECOSTRESS_MIN_PIXELS))
        .reduceColumns(ee.Reducer.toList(3), ["key", "t", "mean"])
        .get("list")
        .getInfo()
    )
    frame = pd.DataFrame(rows, columns=["key", "t", "lst"])
    out = {}
    for key, _, _ in points:
        group = frame[frame["key"] == str(key)]
        series = pd.Series(group["lst"].to_numpy(dtype=float),
                           index=pd.to_datetime(group["t"], unit="ms")).sort_index()
        values = surface_temperature(series)
        if values["surface_passes"] == 0:
            out[str(key)] = HazardProfile(missing=["ecostress_surface_temp: no clear passes"])
        else:
            out[str(key)] = HazardProfile(**values)
    return out


SOURCES = {
    "prism_heat_frost": fetch_heat_frost,
    "imerg_rain": fetch_extreme_rain,
    "smap_soil_moisture": fetch_soil_moisture,
    "landsat_ndvi": fetch_greenness,
    "ecostress_surface_temp": fetch_surface_temperature,
}


def fetch_hazards(
    points: list[tuple[object, float, float]],
    sources: dict | None = None,
    timings: dict[str, float] | None = None,
) -> dict[str, HazardProfile]:
    """HazardProfile for each (key, lon, lat), keyed by ``str(key)``. Never raises: a source
    that fails leaves its fields None and adds "source: reason" to ``missing``.

    Sources run in parallel threads; pass a dict as ``timings`` to get seconds per source.
    """
    sources = SOURCES if sources is None else sources
    profiles = {str(key): HazardProfile() for key, _, _ in points}
    if not points:
        return profiles
    try:
        from farm_analog.earthengine import initialize

        ee = initialize()
        ee.data.setDeadline(SOURCE_TIMEOUT_S * 1000)
    except Exception as exc:  # no login, no network
        for profile in profiles.values():
            profile.missing.append(f"earthengine: {type(exc).__name__}: {exc}")
        return profiles

    def run(name, fetch):
        started = time.perf_counter()
        try:
            return name, fetch(ee, points), None, time.perf_counter() - started
        except Exception as exc:
            reason = f"{type(exc).__name__}: {str(exc)[:200]}"
            return name, None, reason, time.perf_counter() - started

    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        results = list(pool.map(lambda item: run(*item), sources.items()))
    for name, found, reason, seconds in results:
        if timings is not None:
            timings[name] = round(seconds, 1)
        for key in profiles:
            if reason is not None:
                profiles[key].missing.append(f"{name}: {reason}")
            elif key in found:
                profiles[key] = merge(profiles[key], found[key])
    return profiles


# ---------------------------------------------------------------------------
# Contract (M13 integration)
# ---------------------------------------------------------------------------

HAZARDS_FOR_TOP = 3  # analogs that get hazards, like evidence.EVIDENCE_FOR_TOP


def to_contract(profile: HazardProfile):
    """A HazardProfile as the contract's schema.Hazards. Failure reasons stay out of the
    result (only the source names are kept), like the API's error handling."""
    from farm_analog.schema import Hazards

    values = {f.name: getattr(profile, f.name) for f in fields(profile) if f.name != "missing"}
    sources = sorted({m.split(":")[0].strip() for m in profile.missing})
    return Hazards(**values, missing_sources=sources)


def add_hazards(result, field_polygon, top: int = HAZARDS_FOR_TOP):
    """Fetch hazards for the farm (its center) and the top analogs and attach them.

    Raises only if every source failed for every point, so the pipeline can note it; partial
    gaps are listed in a note and in each place's ``missing_sources``.
    """
    from shapely.geometry import Polygon

    shell, *holes = field_polygon.coordinates
    center = Polygon(shell, holes).centroid
    points = [("farm", center.x, center.y)] + [(a.rank, a.lon, a.lat)
                                              for a in result.analogs[:top]]
    profiles = fetch_hazards(points)
    contract = {key: to_contract(p) for key, p in profiles.items()}
    if not any(c.model_dump(exclude={"missing_sources"}, exclude_none=True)
               for c in contract.values()):
        raise RuntimeError("no hazard source returned data")
    analogs = [a.model_copy(update={"hazards": contract.get(str(a.rank))})
               if str(a.rank) in contract else a for a in result.analogs]
    missing = sorted({m for c in contract.values() for m in c.missing_sources})
    notes = list(result.notes)
    if missing:
        notes.append(f"Some hazard data unavailable: {', '.join(missing)}.")
    return result.model_copy(update={"analogs": analogs, "farm_hazards": contract.get("farm"),
                                     "notes": notes})
