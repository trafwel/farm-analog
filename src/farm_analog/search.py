"""Reproducible first PNW analog search; regional prototype, not crop advice.

Data flow:
Inputs:  data/samples/palouse_prism_analog_inputs.json (cached PRISM years; rebuilt from
         Earth Engine only if missing) and data/samples/palouse_climate_ACCESS-CM2_ssp245_
         2050.csv (from climate.py).
Outputs: palouse_analog_candidates.csv (every grid cell ranked by sigma) and
         palouse_analog_summary.json, in ``output_dir`` (default: the data folder).
Used by: app/app.py (the Streamlit preview reads both outputs); tests/test_search.py and
         tests/test_match.py (regression: match.py must reproduce these rankings).
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .analogs import sigma_dissimilarity
from .config import (
    BASELINE_YEARS,
    FUTURE_YEARS,
    PALOUSE_BOUNDS,
    PRISM_COLLECTION,
    PRISM_DATASET_TYPE,
)
from .fingerprint import FEATURES, QUARTER_LABELS, QUARTERS
from .future import apply_delta, quarterly_change

# Quarter label -> (first month, last month), from the shared fingerprint definition.
PERIODS = {QUARTER_LABELS[code]: months for code, months in QUARTERS.items()}
SEARCH_BOUNDS = [-121, 44, -116, 49]


def run(data_dir="data/samples", output_dir=None):
    """Rank candidate locations. Reads cached inputs from ``data_dir`` when present (no Earth
    Engine needed); writes rankings and a summary to ``output_dir`` (default: ``data_dir``)."""
    folder = Path(data_dir)
    out = Path(output_dir) if output_dir is not None else folder
    out.mkdir(parents=True, exist_ok=True)
    first_year, last_year = BASELINE_YEARS
    n_years = last_year - first_year + 1
    cache = folder / "palouse_prism_analog_inputs.json"
    if cache.exists():
        payload = json.loads(cache.read_text())
    else:
        import ee
        from dotenv import load_dotenv

        load_dotenv()
        ee.Initialize(project=os.environ["EE_PROJECT"])
        ee.data.setDeadline(120000)
        folder.mkdir(parents=True, exist_ok=True)
        source = (
            ee.ImageCollection(PRISM_COLLECTION)
            .filter(ee.Filter.eq("dataset_type", PRISM_DATASET_TYPE))
            .filterDate(f"{first_year}-01-01", f"{last_year + 1}-01-01")
        )
        count = source.size().getInfo()
        if count != 12 * n_years:
            raise ValueError(f"Expected {12 * n_years} PRISM months, found {count}")
        native = source.first().select("tmean").projection()
        region = ee.Geometry.Rectangle(list(PALOUSE_BOUNDS), geodesic=False)

        def fingerprint(collection, years):
            bands = []
            for q, (lo, hi) in enumerate(PERIODS.values()):
                season = collection.filter(ee.Filter.calendarRange(lo, hi, "month"))
                bands.extend(
                    [
                        season.select("tmean").mean().rename(f"temperature_{q}"),
                        season.select("ppt").sum().divide(years).rename(f"precipitation_{q}"),
                    ]
                )
            return ee.Image.cat(bands).setDefaultProjection(native)

        annual = []
        for year in range(first_year, last_year + 1):
            collection = source.filterDate(f"{year}-01-01", f"{year + 1}-01-01")
            values = (
                fingerprint(collection, 1)
                .reduceRegion(
                    ee.Reducer.mean(),
                    region,
                    crs=native,
                    scale=native.nominalScale(),
                    maxPixels=1000000,
                )
                .getInfo()
            )
            annual.append({"year": year, **values})
            print(f"PRISM target year {year} downloaded", flush=True)
        # Sparse search: nearest native PRISM cell at a regular 20-km grid of points.
        points = (
            fingerprint(source, n_years)
            .sample(
                region=ee.Geometry.Rectangle(SEARCH_BOUNDS, geodesic=False),
                projection=native,
                scale=20000,
                geometries=True,
            )
            .getInfo()["features"]
        )
        candidates = [
            {
                "longitude": p["geometry"]["coordinates"][0],
                "latitude": p["geometry"]["coordinates"][1],
                **p["properties"],
            }
            for p in points
        ]
        payload = {
            "annual": annual,
            "candidates": candidates,
            "collection": PRISM_COLLECTION,
            "dataset_type": PRISM_DATASET_TYPE,
            "reference_years": list(BASELINE_YEARS),
            "search_bounds": SEARCH_BOUNDS,
            "target_bounds": list(PALOUSE_BOUNDS),
            "downloaded_utc": datetime.now(UTC).isoformat(),
        }
        cache.write_text(json.dumps(payload, indent=2) + "\n")
    annual = pd.DataFrame(payload["annual"])[FEATURES].to_numpy()
    candidates = pd.DataFrame(payload["candidates"])
    observed = annual.mean(axis=0)
    model = pd.read_csv(folder / "palouse_climate_ACCESS-CM2_ssp245_2050.csv")
    target = apply_delta(observed, quarterly_change(model, "ACCESS-CM2"))
    matrix = candidates[FEATURES].to_numpy()
    candidates["sigma"] = sigma_dissimilarity(target, annual, matrix)
    candidates["standardized_euclidean"] = np.linalg.norm(
        (matrix - target) / annual.std(axis=0, ddof=1), axis=1
    )
    candidates = candidates.sort_values("sigma").reset_index(drop=True)
    candidates.insert(0, "rank", np.arange(1, len(candidates) + 1))
    candidates.to_csv(out / "palouse_analog_candidates.csv", index=False)
    summary = {
        "target_future": dict(zip(FEATURES, target, strict=False)),
        "target_observed": dict(zip(FEATURES, observed, strict=False)),
        "quarters": list(PERIODS),
        "model": "ACCESS-CM2",
        "scenario": "SSP2-4.5",
        "future_years": list(FUTURE_YEARS),
        "reference_years": list(BASELINE_YEARS),
        "candidate_count": len(candidates),
        "search_bounds": SEARCH_BOUNDS,
        "method": (
            "Quarterly temperature additive delta and precipitation multiplicative ratio applied "
            "to PRISM. PCA-whitened Mahalanobis distance using 20 annual regional PRISM vectors, "
            "converted to one-dimensional sigma. Standardized Euclidean baseline also provided."
        ),
        "spatial_support": (
            "Palouse regional mean vs sampled native PRISM cells on a sparse 20-km search grid. "
            "Not field-level matching."
        ),
        "limitations": (
            "Exploratory single-model ranking, not validated advice. Reference is 1995–2014, not "
            "current live climate. No soil, agricultural-land, irrigation, or crop filter. "
            "Quarter means omit extremes. Model tas and PRISM tmean definitions differ. No "
            "ensemble confidence or backtest yet."
        ),
        "sources": [
            "https://developers.google.com/earth-engine/datasets/catalog/OREGONSTATE_PRISM_ANm",
            "https://developers.google.com/earth-engine/datasets/catalog/NASA_GDDP-CMIP6",
        ],
        "created_utc": datetime.now(UTC).isoformat(),
    }
    (out / "palouse_analog_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        candidates[["rank", "latitude", "longitude", "sigma"]].head().to_string(index=False),
        flush=True,
    )


if __name__ == "__main__":
    run()
