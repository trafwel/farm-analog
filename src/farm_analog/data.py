"""Download regional SMAP L4 moisture time series through Earth Engine.

Run from the repo root:
    PYTHONPATH=src python -m farm_analog.data

Data flow:
Inputs:  SMAP L4 soil moisture (NASA/SMAP/SPL4SMGP/008) over a date range and bounding box
         (default config.PALOUSE_BOUNDS), via Earth Engine.
Outputs: data/smap/palouse_smap_<start>_<end>.csv (3-hourly regional means) and a .json
         with metadata; a committed sample lives in data/samples/.
Used by: app/app.py (the SMAP chart reads the sample). Planned: field conditions next to
         the analogs (see docs/ARCHITECTURE.md).
"""

import argparse
import csv
import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

from farm_analog.config import PALOUSE_BOUNDS  # defined once, in config.py

SMAP_COLLECTION = "NASA/SMAP/SPL4SMGP/008"
SMAP_BANDS = ["sm_surface", "sm_rootzone"]


def validate_request(start, end, bounds):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first < date(2015, 3, 31) or first >= last:
        raise ValueError("Dates must start on/after 2015-03-31 and end after start (exclusive).")
    if (last - first).days > 366:
        raise ValueError("Download at most 366 days per request.")
    west, south, east, north = bounds
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Bounds must be west south east north in longitude/latitude.")


def download_smap(
    start="2025-07-01",
    end="2025-07-08",
    bounds=PALOUSE_BOUNDS,
    output_dir="data/smap",
    project=None,
):
    """Save native-timestep regional means, valid-pixel counts, and provenance.

    Moisture is volumetric (m³/m³), not percent. L4 combines satellite
    observations and modeling; these are not field measurements or forecasts.
    End date is exclusive. Masked values remain empty rather than becoming zero.
    """
    validate_request(start, end, bounds)
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    project = project or os.environ.get("EE_PROJECT")
    if not project:
        raise RuntimeError(
            "Set EE_PROJECT in .env or pass --project, and run earthengine authenticate."
        )
    try:
        import ee
    except ImportError as exc:
        raise RuntimeError(
            "Install earthengine-api and python-dotenv in your Python environment."
        ) from exc
    ee.Initialize(project=project)
    region = ee.Geometry.Rectangle(list(bounds), geodesic=False)
    collection = ee.ImageCollection(SMAP_COLLECTION).filterDate(start, end).select(SMAP_BANDS)
    first_image = collection.first()
    count = collection.size().getInfo()
    if not count:
        raise RuntimeError("No SMAP images available for the requested dates; no files written.")
    projection = ee.Image(first_image).select(0).projection()
    reducer = ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True)

    def summarize(item):
        image = ee.Image(item)
        values = image.reduceRegion(
            reducer=reducer,
            geometry=region,
            crs=projection,
            scale=projection.nominalScale(),
            maxPixels=10_000_000,
        )
        return ee.Feature(None, values).set(
            {
                "timestamp_utc": image.date().format("YYYY-MM-dd'T'HH:mm:ss'Z'"),
                "image_id": image.get("system:index"),
            }
        )

    # Map over a list: ImageCollection.map must return images, not features.
    features = ee.FeatureCollection(collection.toList(count).map(summarize)).getInfo()["features"]
    rows = sorted((f["properties"] for f in features), key=lambda r: r["timestamp_utc"])
    if not any(r.get("sm_surface_count", 0) or r.get("sm_rootzone_count", 0) for r in rows):
        raise RuntimeError("No valid moisture pixels in this region; no files written.")
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"palouse_smap_{start}_{end}"
    csv_path = directory / f"{stem}.csv"
    fields = [
        "timestamp_utc",
        "image_id",
        "sm_surface_mean",
        "sm_surface_count",
        "sm_rootzone_mean",
        "sm_rootzone_count",
    ]
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "collection": SMAP_COLLECTION,
        "doi": "10.5067/T5RUATAQREF8",
        "source": "https://developers.google.com/earth-engine/datasets/catalog/NASA_SMAP_SPL4SMGP_008",
        "bounds_west_south_east_north": list(bounds),
        "region_note": "Approximate demo extent; custom bounds may override it.",
        "start_inclusive": start,
        "end_exclusive": end,
        "rows": len(rows),
        "units": "m3/m3",
        "surface_depth_cm": [0, 5],
        "rootzone_depth_cm": [0, 100],
        "aggregation": (
            "Regional pixel mean at each native 3-hour timestep; counts are valid pixels."
        ),
        "native_grid_km": 9,
        "earth_engine_projection": projection.getInfo(),
        "limitations": (
            "Satellite-assimilating land model; regional context, not field measurements. During "
            "satellite outages, estimates are model-only."
        ),
        "downloaded_utc": datetime.now(UTC).isoformat(),
    }
    csv_path.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    return csv_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2025-07-01")
    parser.add_argument("--end", default="2025-07-08")
    parser.add_argument("--bounds", nargs=4, type=float, default=PALOUSE_BOUNDS)
    parser.add_argument("--output-dir", default="data/smap")
    parser.add_argument("--project")
    args = parser.parse_args()
    try:
        path = download_smap(args.start, args.end, args.bounds, args.output_dir, args.project)
    except Exception as exc:
        parser.exit(1, f"SMAP import failed: {exc}\n")
    print(f"Saved SMAP data: {path}")


if __name__ == "__main__":
    main()
