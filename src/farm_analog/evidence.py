"""Evidence for the top analogs (M7): what grows there, the soil, the climograph, and a
place name a farmer recognizes.

As in M1-M3, the arithmetic lives in plain functions tested offline, and Earth Engine is
used only to fetch raw numbers:

- crops: Cropland Data Layer pixel counts within ``CROP_RADIUS_M`` over ``CDL_YEARS``,
  turned into shares of cropland (non-farm classes like forest or towns are left out);
- soil: OpenLandMap topsoil clay, sand and organic carbon (250 m) at the point;
- climograph: monthly PRISM normals at the analog, next to the farm today and in 2050;
- place: the county (US Census TIGER) the analog falls in.

Data flow:
Inputs:  an ``AnalogResult`` from match.to_result; the farm's monthly table
         (FarmToday.monthly) and per-model changes (FarmFuture.changes); from Earth Engine,
         for the top 3 analog points: CDL crop pixel counts (2019-2023, 2 km radius),
         OpenLandMap topsoil clay/sand/organic carbon, monthly PRISM normals, and TIGER
         county names.
Outputs: a copy of the AnalogResult whose top analogs carry ``place_name``, ``crops``
         (list of CropShare), ``soil`` (SoilProfile) and ``climograph`` (farm today, farm
         future and analog today, 12 months each).
Used by: pipeline._analyze_live (``add_evidence``, wrapped so a failure only adds a note);
         the frontend reads the new fields (shown in M8); assistant/summarizer.py reads
         place names and crops.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from farm_analog import config, fingerprint
from farm_analog.future import FarmFuture, QuarterlyChange
from farm_analog.schema import (
    AnalogResult,
    Climograph,
    CropShare,
    MonthlyClimate,
    SoilProfile,
)

CROP_RADIUS_M = 2000
TOP_CROPS = 5
EVIDENCE_FOR_TOP = 3

# Cropland Data Layer codes that are crops (including fallow/idle cropland and double
# crops); everything else (forest, water, towns, grassland, wetlands) is not cropland.
CROP_CODES = set(range(1, 62)) | set(range(66, 78)) | set(range(204, 255))

# OpenLandMap organic carbon is stored in units of 5 g/kg (per its catalog page; check
# before relying on it). Organic matter is about 1.724 x organic carbon (van Bemmelen).
OLM_OC_UNIT_G_PER_KG = 5.0
OM_PER_OC = 1.724

STATE_ABBR = {"16": "ID", "30": "MT", "41": "OR", "53": "WA", "06": "CA", "32": "NV", "56": "WY"}


# ---------------------------------------------------------------------------
# Pure functions (tested offline)
# ---------------------------------------------------------------------------


def crop_shares(counts: dict[int, float], names: dict[int, str], top: int = TOP_CROPS):
    """Shares of cropland by crop, largest first; small crops grouped as "Other crops"."""
    crops = {int(c): float(n) for c, n in counts.items() if int(c) in CROP_CODES and n > 0}
    total = sum(crops.values())
    if total == 0:
        return []
    ranked = sorted(crops.items(), key=lambda kv: (-kv[1], kv[0]))
    shares = [
        CropShare(crop=names.get(code, f"CDL class {code}"), share=round(n / total, 3))
        for code, n in ranked[:top]
    ]
    rest = sum(n for _, n in ranked[top:])
    if rest > 0:
        shares.append(CropShare(crop="Other crops", share=round(rest / total, 3)))
    return shares


def soil_profile(clay_pct, sand_pct, olm_organic_carbon) -> SoilProfile:
    """A contract SoilProfile from OpenLandMap topsoil values (None where missing)."""

    def clean(value, upper=100.0):
        if value is None or not np.isfinite(value) or not 0 <= value <= upper:
            return None
        return round(float(value), 1)

    organic_matter = None
    if olm_organic_carbon is not None and np.isfinite(olm_organic_carbon):
        organic_carbon_pct = olm_organic_carbon * OLM_OC_UNIT_G_PER_KG / 10  # g/kg -> %
        organic_matter = clean(organic_carbon_pct * OM_PER_OC)
    return SoilProfile(
        clay_pct=clean(clay_pct),
        sand_pct=clean(sand_pct),
        organic_matter_pct=organic_matter,
    )


def monthly_normals(monthly: pd.DataFrame) -> pd.DataFrame:
    """12 rows (month 1-12) of average ``tmean`` and ``ppt`` from a year x month table."""
    normals = monthly.groupby("month")[["tmean", "ppt"]].mean().reindex(range(1, 13))
    if normals.isna().any().any():
        raise ValueError("monthly data doesn't cover all 12 months")
    return normals


def future_monthly(normals: pd.DataFrame, changes: list[QuarterlyChange]) -> pd.DataFrame:
    """The farm's future months: each model's quarterly change applied to the month's own
    normal, then the median across models (matching the headline future)."""
    per_model = []
    for change in changes:
        future = normals.copy()
        for q, (first, last) in enumerate(fingerprint.QUARTERS.values()):
            months = list(range(first, last + 1))
            future.loc[months, "tmean"] += change.temperature_delta_c[q]
            future.loc[months, "ppt"] *= change.precipitation_ratio[q]
        per_model.append(future)
    stacked = np.stack([f[["tmean", "ppt"]].to_numpy() for f in per_model])
    return pd.DataFrame(np.median(stacked, axis=0), index=normals.index, columns=["tmean", "ppt"])


def to_monthly_climate(normals: pd.DataFrame) -> MonthlyClimate:
    return MonthlyClimate(
        tmean=[round(float(v), 2) for v in normals["tmean"]],
        ppt=[round(float(v), 2) for v in normals["ppt"]],
    )


def cdl_class_names(values, names) -> dict[int, str]:
    """CDL class code -> name. Earth Engine stores both as comma-separated strings
    ("0,1,2,..." and "Background,Corn,Cotton,..."); lists are accepted too."""
    if isinstance(values, str):
        values = values.split(",")
    if isinstance(names, str):
        names = names.split(",")
    if len(values) != len(names):
        raise ValueError(f"CDL has {len(values)} class codes but {len(names)} names")
    return {int(v): n.strip() for v, n in zip(values, names, strict=True)}


def place_name(county: str | None, state_fips: str | None) -> str | None:
    if not county:
        return None
    state = STATE_ABBR.get(str(state_fips or "").zfill(2))
    return f"{county} County, {state}" if state else f"{county} County"


@dataclass(frozen=True)
class AnalogEvidence:
    """Everything fetched for one analog (any part may be missing)."""

    place_name: str | None
    crops: list[CropShare]
    soil: SoilProfile | None
    monthly: pd.DataFrame | None  # 12 x (tmean, ppt) normals at the analog


def attach(
    result: AnalogResult,
    evidence: dict[int, AnalogEvidence],
    farm_monthly: pd.DataFrame | None = None,
    future_months: pd.DataFrame | None = None,
    farm_soil: SoilProfile | None = None,
    extra_place_names: dict[int, str | None] | None = None,
) -> AnalogResult:
    """Return a copy of ``result`` with evidence attached to the analogs it covers (by rank).

    ``extra_place_names`` supplies names for analogs not in ``evidence`` (e.g. ranks 4-20
    when only the top 3 have full evidence).
    """
    names = extra_place_names or {}
    analogs = []
    for analog in result.analogs:
        found = evidence.get(analog.rank)
        if found is None:
            # Apply an extra place name if available.
            pn = names.get(analog.rank)
            if pn is not None and analog.place_name is None:
                analogs.append(analog.model_copy(update={"place_name": pn}))
            else:
                analogs.append(analog)
            continue
        climograph = None
        if found.monthly is not None and farm_monthly is not None and future_months is not None:
            climograph = Climograph(
                farm_today=to_monthly_climate(farm_monthly),
                farm_future=to_monthly_climate(future_months),
                analog_today=to_monthly_climate(found.monthly),
            )
        analogs.append(
            analog.model_copy(
                update={
                    "place_name": found.place_name,
                    "crops": found.crops or None,
                    "soil": found.soil,
                    "climograph": climograph,
                }
            )
        )
    update = {"analogs": analogs}
    if farm_soil is not None:
        update["farm_soil"] = farm_soil
    return result.model_copy(update=update)


# ---------------------------------------------------------------------------
# Earth Engine (needs login and network)
# ---------------------------------------------------------------------------


def fetch_place_names(points: list[tuple[int, float, float]]) -> dict[int, str | None]:
    """County name for each (rank, lon, lat) — cheap TIGER lookup only."""
    from farm_analog.earthengine import initialize

    ee = initialize()
    fc = ee.FeatureCollection(
        [ee.Feature(ee.Geometry.Point([lon, lat]), {"rank": rank}) for rank, lon, lat in points]
    )
    counties = ee.FeatureCollection("TIGER/2018/Counties")
    county_values = {
        f["properties"]["rank"]: f["properties"]
        for f in fc.map(
            lambda f: f.set(
                ee.Feature(counties.filterBounds(f.geometry()).first()).toDictionary(
                    ["NAME", "STATEFP"]
                )
            )
        ).getInfo()["features"]
    }
    return {
        rank: place_name(c.get("NAME"), c.get("STATEFP"))
        for rank, c in county_values.items()
    }


def fetch_evidence(points: list[tuple[int, float, float]]) -> dict[int, AnalogEvidence]:
    """Crops, soil, monthly PRISM normals and county for each (rank, lon, lat), in a few
    batched requests."""
    from farm_analog.earthengine import initialize

    ee = initialize()
    fc = ee.FeatureCollection(
        [ee.Feature(ee.Geometry.Point([lon, lat]), {"rank": rank}) for rank, lon, lat in points]
    )

    # Crops: CDL pixel counts per class within the radius, summed over the years.
    first, last = config.CDL_YEARS
    cdl = ee.ImageCollection("USDA/NASS/CDL").filterDate(f"{first}-01-01", f"{last + 1}-01-01")
    first_image = cdl.first()
    names = cdl_class_names(
        first_image.get("cropland_class_values").getInfo(),
        first_image.get("cropland_class_names").getInfo(),
    )
    counts = {rank: {} for rank, _, _ in points}
    for image in cdl.toList(cdl.size()).getInfo():
        img = ee.Image(image["id"]).select("cropland")
        hist = img.reduceRegions(
            collection=fc.map(lambda f: f.buffer(CROP_RADIUS_M)),
            reducer=ee.Reducer.frequencyHistogram(),
            scale=30,
        ).getInfo()["features"]
        for f in hist:
            rank = f["properties"]["rank"]
            for code, n in (f["properties"].get("histogram") or {}).items():
                counts[rank][int(float(code))] = counts[rank].get(int(float(code)), 0) + n

    # Soil (topsoil, 0 cm) and county, sampled at the points.
    def olm(asset):
        return ee.Image(asset).select("b0")

    soil = (
        olm("OpenLandMap/SOL/SOL_CLAY-WFRACTION_USDA-3A1A1A_M/v02")
        .rename("clay")
        .addBands(olm("OpenLandMap/SOL/SOL_SAND-WFRACTION_USDA-3A1A1A_M/v02").rename("sand"))
        .addBands(olm("OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02").rename("oc"))
    )
    soil_values = {
        f["properties"]["rank"]: f["properties"]
        for f in soil.reduceRegions(collection=fc, reducer=ee.Reducer.first(), scale=250).getInfo()[
            "features"
        ]
    }
    counties = ee.FeatureCollection("TIGER/2018/Counties")
    county_values = {
        f["properties"]["rank"]: f["properties"]
        for f in fc.map(
            lambda f: f.set(
                ee.Feature(counties.filterBounds(f.geometry()).first()).toDictionary(
                    ["NAME", "STATEFP"]
                )
            )
        ).getInfo()["features"]
    }

    # Monthly PRISM normals at each point.
    years = config.BASELINE_YEARS
    prism = (
        ee.ImageCollection(config.PRISM_COLLECTION)
        .filter(ee.Filter.eq("dataset_type", config.PRISM_DATASET_TYPE))
        .filterDate(f"{years[0]}-01-01", f"{years[1] + 1}-01-01")
    )
    monthly = {rank: [] for rank, _, _ in points}
    for month in range(1, 13):
        normal = (
            prism.filter(ee.Filter.calendarRange(month, month, "month"))
            .select(["tmean", "ppt"])
            .mean()
        )
        for f in normal.reduceRegions(
            collection=fc, reducer=ee.Reducer.first(), scale=config.GRID_SCALE_M
        ).getInfo()["features"]:
            p = f["properties"]
            monthly[p["rank"]].append(
                {"month": month, "tmean": p.get("tmean"), "ppt": p.get("ppt")}
            )

    evidence = {}
    for rank, _, _ in points:
        s, c = soil_values.get(rank, {}), county_values.get(rank, {})
        frame = pd.DataFrame(monthly[rank]).set_index("month")
        evidence[rank] = AnalogEvidence(
            place_name=place_name(c.get("NAME"), c.get("STATEFP")),
            crops=crop_shares(counts[rank], names),
            soil=soil_profile(s.get("clay"), s.get("sand"), s.get("oc")),
            monthly=None if frame[["tmean", "ppt"]].isna().any().any() else frame,
        )
    return evidence


def add_evidence(
    result: AnalogResult,
    farm_monthly_table: pd.DataFrame,
    future: FarmFuture,
    changes: list[QuarterlyChange],
    top: int = EVIDENCE_FOR_TOP,
) -> AnalogResult:
    """Fetch and attach evidence for the top analogs (live mode).

    Full evidence (crops, soil, climograph) is fetched for the top ``top`` analogs.
    Place names (county from TIGER) are fetched for *all* analogs, since the lookup is cheap.
    """
    if not result.analogs:
        return result
    # Full evidence for the top few.
    points = [(a.rank, a.lon, a.lat) for a in result.analogs[:top]]
    evidence = fetch_evidence(points)
    # Place names for the rest (ranks not already covered by full evidence).
    covered_ranks = set(evidence.keys())
    extra_points = [
        (a.rank, a.lon, a.lat) for a in result.analogs if a.rank not in covered_ranks
    ]
    extra_names = fetch_place_names(extra_points) if extra_points else {}
    farm_months = monthly_normals(farm_monthly_table)
    return attach(
        result, evidence, farm_months, future_monthly(farm_months, changes),
        extra_place_names=extra_names,
    )
