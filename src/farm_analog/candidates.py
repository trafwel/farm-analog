"""Candidate places: farmland cells whose present-day climate can be matched against a farm's
future climate (M3).

Each candidate is one ~4 km PRISM cell with the shared 8-value fingerprint (1995-2014
normals) and the share of the cell the Cropland Data Layer marks as cultivated. Only
farmland is kept, so an analog is always somewhere people actually farm.

Candidates are the same for every farm, so they're computed once (Earth Engine, minutes)
and cached as Parquet in ``data/candidates/`` (ignored by git). Until someone with Earth
Engine access builds that cache, ``load_candidates`` falls back to the team's committed
20 km search cache, which has the same fingerprint but no farmland filter.

Data flow:
Inputs:  Earth Engine (PRISM normals + Cropland Data Layer cultivated band) when building the
         cache with ``python -m farm_analog.candidates``; otherwise
         data/candidates/candidates.parquet if it exists, else the team's
         data/samples/palouse_prism_analog_inputs.json (784-cell, 20 km grid).
Outputs: a DataFrame with COLUMNS (cell_id, lon, lat, the 8 FEATURES,
         cultivated_fraction) plus a one-line note saying which source was used;
         data/candidates/candidates.parquet (+ metadata) when the cache is built.
Used by: match.match (scores every row), pipeline._analyze_live (after near_latitude),
         match.palouse_demo, proof.py (self-check pool and backtest cells).
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from farm_analog import config, fingerprint

REPO = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO / "data" / "candidates"
CACHE_FILE = CACHE_DIR / "candidates.parquet"
TEAM_CACHE = REPO / "data" / "samples" / "palouse_prism_analog_inputs.json"

ID_COLUMNS = ["cell_id", "lon", "lat"]
COLUMNS = ID_COLUMNS + fingerprint.FEATURES + ["cultivated_fraction"]


def cell_id(lon: float, lat: float) -> str:
    """A stable id from the cell's location (about 10 m precision)."""
    return f"{lat:.4f}_{lon:.4f}"


def validate_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Check columns, ranges and missing values; return a clean copy in ``COLUMNS`` order."""
    missing = set(COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"candidates are missing columns: {sorted(missing)}")
    frame = frame[COLUMNS].copy()
    if frame.empty:
        raise ValueError("no candidates")
    if frame["cell_id"].duplicated().any():
        raise ValueError("duplicate candidate cells")
    if frame[["lon", "lat", *fingerprint.FEATURES]].isna().any().any():
        raise ValueError("candidates have missing climate values")
    if not (frame["lon"].between(-180, 180).all() and frame["lat"].between(-90, 90).all()):
        raise ValueError("candidate coordinates out of range")
    precip = [f for f in fingerprint.FEATURES if f.startswith("precipitation")]
    if (frame[precip] < 0).any().any():
        raise ValueError("negative precipitation in candidates")
    fraction = frame["cultivated_fraction"].dropna()
    if not fraction.between(0, 1).all():
        raise ValueError("cultivated_fraction must be between 0 and 1")
    return frame.reset_index(drop=True)


def keep_farmland(frame: pd.DataFrame, min_fraction: float = config.MIN_CULTIVATED_FRACTION):
    """Drop cells that are mostly not farmland. Cells with unknown cover are kept."""
    known = frame["cultivated_fraction"].notna()
    return frame[~known | (frame["cultivated_fraction"] >= min_fraction)].reset_index(drop=True)


def near_latitude(
    frame: pd.DataFrame, lat: float, max_diff: float = config.MAX_LATITUDE_DIFF_DEG
) -> pd.DataFrame:
    """Candidates within ``max_diff`` degrees of latitude (similar day length)."""
    return frame[(frame["lat"] - lat).abs() <= max_diff].reset_index(drop=True)


def matrix(frame: pd.DataFrame) -> np.ndarray:
    """Candidates x features, the input sigma dissimilarity expects."""
    return frame[fingerprint.FEATURES].to_numpy(dtype=float)


def from_team_cache(payload: dict) -> pd.DataFrame:
    """Candidates from the team's ``palouse_prism_analog_inputs.json`` (20 km, no farmland
    filter, so ``cultivated_fraction`` is unknown)."""
    rows = []
    for c in payload["candidates"]:
        rows.append(
            {
                "cell_id": cell_id(c["longitude"], c["latitude"]),
                "lon": c["longitude"],
                "lat": c["latitude"],
                **{f: c[f] for f in fingerprint.FEATURES},
                "cultivated_fraction": np.nan,
            }
        )
    return validate_candidates(pd.DataFrame(rows))


def save_candidates(frame: pd.DataFrame, metadata: dict, path: Path = CACHE_FILE) -> Path:
    """Write candidates to Parquet with a provenance JSON beside it."""
    frame = validate_candidates(frame)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    meta = {
        **metadata,
        "rows": len(frame),
        "columns": COLUMNS,
        "saved_utc": datetime.now(UTC).isoformat(),
    }
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    return path


def load_candidates(path: Path = CACHE_FILE, team_cache: Path = TEAM_CACHE):
    """The candidate cells to search, and a note saying where they came from.

    Prefers the full farmland cache built by ``fetch_candidates``; falls back to the team's
    committed 20 km cache so the app works offline.
    """
    if path.exists():
        frame = validate_candidates(pd.read_parquet(path))
        return keep_farmland(frame), f"{len(frame)} farmland cells (~4 km, Cropland Data Layer)"
    frame = from_team_cache(json.loads(team_cache.read_text()))
    note = (
        f"{len(frame)} cells on the team's 20 km grid; not yet filtered to farmland "
        "(build data/candidates with Earth Engine for the full ~4 km farmland search)"
    )
    return frame, note


# ---------------------------------------------------------------------------
# Earth Engine (needs login and network)
# ---------------------------------------------------------------------------


def _tiles(bbox, step=1.0):
    west, south, east, north = bbox
    lons = np.arange(west, east, step)
    lats = np.arange(south, north, step)
    for x in lons:
        for y in lats:
            yield (float(x), float(y), float(min(x + step, east)), float(min(y + step, north)))


def fetch_candidates(
    bbox=config.SEARCH_BBOX,
    years=config.BASELINE_YEARS,
    cdl_years=config.CDL_YEARS,
    min_fraction=config.MIN_CULTIVATED_FRACTION,
) -> pd.DataFrame:
    """Sample every farmland PRISM cell in ``bbox``: fingerprint + cultivated share.

    Works tile by tile (1° x 1°) so each request stays under Earth Engine's 5,000-feature
    limit for direct downloads.
    """
    from farm_analog.earthengine import initialize

    ee = initialize()
    first, last = years
    n_years = last - first + 1
    prism = (
        ee.ImageCollection(config.PRISM_COLLECTION)
        .filter(ee.Filter.eq("dataset_type", config.PRISM_DATASET_TYPE))
        .filterDate(f"{first}-01-01", f"{last + 1}-01-01")
    )
    count = prism.size().getInfo()
    if count != 12 * n_years:
        raise ValueError(f"expected {12 * n_years} PRISM months, found {count}")
    native = prism.first().select("tmean").projection()

    bands = []
    for q, (lo, hi) in enumerate(fingerprint.QUARTERS.values()):
        quarter = prism.filter(ee.Filter.calendarRange(lo, hi, "month"))
        bands.append(quarter.select("tmean").mean().rename(f"temperature_{q}"))
        bands.append(quarter.select("ppt").sum().divide(n_years).rename(f"precipitation_{q}"))
    climate = ee.Image.cat(bands)

    # CDL "cultivated" band: 2 = cultivated. Average over years, then over each PRISM cell.
    cdl = ee.ImageCollection("USDA/NASS/CDL").filterDate(
        f"{cdl_years[0]}-01-01", f"{cdl_years[1] + 1}-01-01"
    )
    cultivated = (
        cdl.select("cultivated")
        .map(lambda img: img.eq(2))
        .mean()
        # A collection's mean has no projection of its own; give it CDL's 30 m grid back so
        # reduceResolution knows what it is averaging from.
        .setDefaultProjection(cdl.first().select("cultivated").projection())
        .reduceResolution(ee.Reducer.mean(), maxPixels=65535)
        .reproject(native)
        .rename("cultivated_fraction")
    )
    image = climate.addBands(cultivated).updateMask(cultivated.gte(min_fraction))

    rows = []
    for tile in _tiles(bbox):
        region = ee.Geometry.Rectangle(list(tile), geodesic=False)
        # Sample on PRISM's own grid (~4.6 km): a fixed 4 km step picked some cells twice,
        # which listed the same place as two analogs.
        features = image.sample(
            region=region, projection=native, scale=native.nominalScale(), geometries=True
        ).getInfo()["features"]
        for f in features:
            lon, lat = f["geometry"]["coordinates"]
            rows.append({"cell_id": cell_id(lon, lat), "lon": lon, "lat": lat, **f["properties"]})
    frame = pd.DataFrame(rows).drop_duplicates("cell_id")
    return validate_candidates(frame)


def build_cache(path: Path = CACHE_FILE) -> Path:
    """Fetch candidates from Earth Engine and cache them (run once, by someone with access):
    ``python -m farm_analog.candidates``."""
    frame = fetch_candidates()
    metadata = {
        "prism": f"{config.PRISM_COLLECTION} ({config.PRISM_DATASET_TYPE})",
        "baseline_years": list(config.BASELINE_YEARS),
        "cdl": "USDA/NASS/CDL cultivated band",
        "cdl_years": list(config.CDL_YEARS),
        "min_cultivated_fraction": config.MIN_CULTIVATED_FRACTION,
        "search_bbox": list(config.SEARCH_BBOX),
        "grid_scale_m": config.GRID_SCALE_M,
        "fingerprint": "8 quarterly values (farm_analog.fingerprint)",
    }
    return save_candidates(frame, metadata, path)


if __name__ == "__main__":
    print(f"Saved {build_cache()}")
