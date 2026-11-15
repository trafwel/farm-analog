"""Download a first NEX-GDDP-CMIP6 climate comparison for the Palouse.

Data flow:
Inputs:  NEX-GDDP-CMIP6 (ACCESS-CM2, historical + ssp245) over config.PALOUSE_BOUNDS, via
         Earth Engine (needs EE_PROJECT).
Outputs: data/samples/palouse_climate_ACCESS-CM2_ssp245_2050.csv (monthly temperature and
         precipitation, 1995-2014 baseline and 2041-2060 future) and a matching .json with metadata.
Used by: search.py and match.palouse_demo (the offline model change),
         future.quarterly_change (parses this CSV's layout), app/app.py (2050 charts).
"""

import csv
import json
import os
from calendar import monthrange
from datetime import UTC, datetime
from pathlib import Path

from .data import PALOUSE_BOUNDS

COLLECTION = "NASA/GDDP-CMIP6"
SOURCE = "https://developers.google.com/earth-engine/datasets/catalog/NASA_GDDP-CMIP6"


def download_projection(output_dir="data/samples"):
    import ee
    from dotenv import load_dotenv

    load_dotenv()
    ee.Initialize(project=os.environ["EE_PROJECT"])
    ee.data.setDeadline(120000)
    model = "ACCESS-CM2"
    region = ee.Geometry.Rectangle(list(PALOUSE_BOUNDS), geodesic=False)
    base = ee.ImageCollection(COLLECTION).filter(ee.Filter.eq("model", model))
    rows = []
    provenance = []
    for label, first, last, scenario in [
        ("baseline", 1995, 2014, "historical"),
        ("future", 2041, 2060, "ssp245"),
    ]:
        images = base.filter(ee.Filter.eq("scenario", scenario)).filterDate(
            f"{first}-01-01", f"{last + 1}-01-01"
        )
        info = ee.Dictionary(
            {
                "count": images.size(),
                "versions": images.aggregate_histogram("version"),
                "unique_dates": images.aggregate_count_distinct("system:time_start"),
            }
        ).getInfo()
        expected = sum(monthrange(y, m)[1] for y in range(first, last + 1) for m in range(1, 13))
        if info["count"] != expected or info["unique_dates"] != expected:
            raise RuntimeError(f"Incomplete or duplicate daily data: {label}: {info}")
        provenance.append({"period": label, **info})
        projection = images.first().select("tas").projection()
        for month in range(1, 13):
            monthly = images.filter(ee.Filter.calendarRange(month, month, "month"))
            # Daily mean temperature -> period monthly mean (C).
            # Daily precipitation flux -> mm/day -> average monthly total (mm).
            climate = (
                monthly.select("tas")
                .mean()
                .subtract(273.15)
                .rename("temperature_c")
                .addBands(
                    monthly.select("pr")
                    .sum()
                    .multiply(86400 / (last - first + 1))
                    .rename("precipitation_mm")
                )
            )
            values = climate.reduceRegion(
                ee.Reducer.mean(),
                region,
                crs=projection,
                scale=projection.nominalScale(),
                maxPixels=1000000,
            ).getInfo()
            if any(values.get(k) is None for k in ["temperature_c", "precipitation_mm"]):
                raise RuntimeError(f"Missing regional values for {label} month {month}")
            rows.append(
                {
                    "period": label,
                    "start_year": first,
                    "end_year": last,
                    "model": model,
                    "scenario": scenario,
                    "month": month,
                    **values,
                }
            )
            print(f"{label} month {month}/12 downloaded", flush=True)
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "palouse_climate_ACCESS-CM2_ssp245_2050.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "collection": COLLECTION,
        "source": SOURCE,
        "model": model,
        "scenario": "SSP2-4.5",
        "bounds_west_south_east_north": list(PALOUSE_BOUNDS),
        "baseline": "1995–2014 historical model simulation; not observations",
        "future": "2041–2060 (20-year climate centered around 2050)",
        "temperature": "Monthly mean daily near-surface temperature in °C; tas minus 273.15",
        "precipitation": "Mean monthly precipitation total in mm; sum(pr) × 86400 / 20 years",
        "spatial_aggregation": "Regional mean at source projection and nominal scale",
        "grid_degrees": 0.25,
        "data_checks": provenance,
        "limitations": (
            "One model and one scenario for a first prototype. Not an ensemble or a daily weather "
            "forecast; no analogs calculated yet. Source may include interpolated calendar days."
        ),
        "downloaded_utc": datetime.now(UTC).isoformat(),
    }
    path.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Saved {path}")
    return path


if __name__ == "__main__":
    download_projection()
