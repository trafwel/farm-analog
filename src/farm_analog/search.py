"""Reproducible first PNW analog search; regional prototype, not crop advice."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .analogs import sigma_dissimilarity
from .data import PALOUSE_BOUNDS

PERIODS = {"Jan–Mar": (1, 3), "Apr–Jun": (4, 6), "Jul–Sep": (7, 9), "Oct–Dec": (10, 12)}
FEATURES = [f"{kind}_{q}" for q in range(4) for kind in ["temperature", "precipitation"]]
SEARCH_BOUNDS = [-121, 44, -116, 49]


def run():
    import ee
    from dotenv import load_dotenv

    load_dotenv()
    ee.Initialize(project=os.environ["EE_PROJECT"])
    ee.data.setDeadline(120000)
    folder = Path("data/samples")
    folder.mkdir(parents=True, exist_ok=True)
    cache = folder / "palouse_prism_analog_inputs.json"
    if cache.exists():
        payload = json.loads(cache.read_text())
    else:
        source = (
            ee.ImageCollection("OREGONSTATE/PRISM/ANm")
            .filter(ee.Filter.eq("dataset_type", "AN81"))
            .filterDate("1995-01-01", "2015-01-01")
        )
        count = source.size().getInfo()
        if count != 240:
            raise ValueError(f"Expected 240 PRISM months, found {count}")
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
        for year in range(1995, 2015):
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
            fingerprint(source, 20)
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
            "collection": "OREGONSTATE/PRISM/ANm",
            "dataset_type": "AN81",
            "reference_years": [1995, 2014],
            "search_bounds": SEARCH_BOUNDS,
            "target_bounds": list(PALOUSE_BOUNDS),
            "downloaded_utc": datetime.now(UTC).isoformat(),
        }
        cache.write_text(json.dumps(payload, indent=2) + "\n")
    annual = pd.DataFrame(payload["annual"])[FEATURES].to_numpy()
    candidates = pd.DataFrame(payload["candidates"])
    observed = annual.mean(axis=0)
    target = observed.copy()
    model = pd.read_csv(folder / "palouse_climate_ACCESS-CM2_ssp245_2050.csv")
    for q, (lo, hi) in enumerate(PERIODS.values()):
        part = model[model.month.between(lo, hi)]
        baseline = part[part.period == "baseline"]
        future = part[part.period == "future"]
        target[2 * q] += future.temperature_c.mean() - baseline.temperature_c.mean()
        denominator = baseline.precipitation_mm.sum()
        if denominator <= 0:
            raise ValueError("Cannot apply rainfall ratio to a zero baseline.")
        target[2 * q + 1] *= future.precipitation_mm.sum() / denominator
    matrix = candidates[FEATURES].to_numpy()
    candidates["sigma"] = sigma_dissimilarity(target, annual, matrix)
    candidates["standardized_euclidean"] = np.linalg.norm(
        (matrix - target) / annual.std(axis=0, ddof=1), axis=1
    )
    candidates = candidates.sort_values("sigma").reset_index(drop=True)
    candidates.insert(0, "rank", np.arange(1, len(candidates) + 1))
    candidates.to_csv(folder / "palouse_analog_candidates.csv", index=False)
    summary = {
        "target_future": dict(zip(FEATURES, target, strict=False)),
        "target_observed": dict(zip(FEATURES, observed, strict=False)),
        "quarters": list(PERIODS),
        "model": "ACCESS-CM2",
        "scenario": "SSP2-4.5",
        "future_years": [2041, 2060],
        "reference_years": [1995, 2014],
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
    (folder / "palouse_analog_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        candidates[["rank", "latitude", "longitude", "sigma"]].head().to_string(index=False),
        flush=True,
    )


if __name__ == "__main__":
    run()
