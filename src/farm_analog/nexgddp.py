"""Download a multi-model NEX-GDDP-CMIP6 climate comparison for the Palouse.

Uses the NASA NCCS THREDDS NetCDF Subset Service (NCSS), which needs no login and
returns only the Palouse grid cells (~50 KB per model-variable-year instead of
~245 MB global files). Produces the same monthly baseline/future table as
climate.py (Earth Engine, ACCESS-CM2 only), for several models plus their mean.

Run from the repo root:
    PYTHONPATH=src python -m farm_analog.nexgddp
"""

import argparse
import csv
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

THREDDS = "https://ds.nccs.nasa.gov/thredds"
DATASET_ROOT = "AMES/NEX/GDDP-CMIP6"
SOURCE = "https://www.nccs.nasa.gov/services/data-collections/land-based-products/nex-gddp-cmip6"
DOI = "10.7917/OFSG3345"
# Same approximate Washington Palouse demo extent as the SMAP importer.
PALOUSE_BOUNDS = (-118.2, 46.5, -117.0, 47.2)
# Models with r1i1p1f1 runs spanning a range of climate sensitivities.
DEFAULT_MODELS = [
    "ACCESS-CM2",
    "CanESM5",
    "EC-Earth3",
    "GFDL-ESM4",
    "MIROC6",
    "MPI-ESM1-2-HR",
    "MRI-ESM2-0",
    "NorESM2-MM",
]
PERIODS = [("baseline", 1995, 2014, "historical"), ("future", 2041, 2060, "ssp245")]
VARIABLES = ["tas", "pr"]
FIELDS = [
    "period",
    "start_year",
    "end_year",
    "model",
    "scenario",
    "month",
    "precipitation_mm",
    "temperature_c",
]
NOLEAP = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def list_files(session, model, scenario, variable, member="r1i1p1f1"):
    """Return {year: url_path}, choosing the newest version (_v2.0 > _v1.1 > none) per year."""
    url = f"{THREDDS}/catalog/{DATASET_ROOT}/{model}/{scenario}/{member}/{variable}/catalog.xml"
    response = session.get(url, timeout=120)
    response.raise_for_status()
    best = {}
    for path in re.findall(r'urlPath="([^"]+\.nc)"', response.text):
        match = re.search(r"_(\d{4})(?:_v(\d+)\.(\d+))?\.nc$", path)
        if match:
            year = int(match.group(1))
            version = (int(match.group(2) or 0), int(match.group(3) or 0))
            if year not in best or version > best[year][0]:
                best[year] = (version, path)
    return {year: path for year, (_, path) in best.items()}


def fetch_subset(session, url_path, variable, bounds, cache_dir):
    """Download (or reuse) the NCSS subset for one file and return its local path."""
    west, south, east, north = bounds
    path = Path(cache_dir) / Path(url_path).name.replace(".nc", "_palouse.nc")
    if path.exists() and path.stat().st_size:
        return path
    params = {
        "var": variable,
        "north": north,
        "south": south,
        "west": west % 360,
        "east": east % 360,
        "temporal": "all",
        "accept": "netcdf4",
    }
    for attempt in range(5):
        try:
            response = session.get(f"{THREDDS}/ncss/grid/{url_path}", params=params, timeout=300)
            if response.ok and response.content[:4] == b"\x89HDF":
                tmp = path.with_suffix(".part")
                tmp.write_bytes(response.content)
                tmp.replace(path)
                return path
            if response.status_code < 500 and response.status_code != 429:
                raise RuntimeError(
                    f"NCSS refused {url_path} (HTTP {response.status_code}): {response.text[:200]}"
                )
        except Exception as exc:  # network errors and 5xx: retry
            if attempt == 4 or isinstance(exc, RuntimeError):
                raise
        time.sleep(5 * 2**attempt)
    raise RuntimeError(f"NCSS kept failing for {url_path}")


def monthly_sums(path, variable, bounds):
    """Return ([sum per month], [days per month]) of the regional daily mean."""
    import h5py
    import numpy as np

    west, south, east, north = bounds
    with h5py.File(path, "r") as handle:
        data = handle[variable][:].astype("float64")
        lat, lon = handle["lat"][:], handle["lon"][:] % 360
        calendar = handle["time"].attrs.get("calendar", b"standard")
        calendar = calendar.decode() if isinstance(calendar, bytes) else str(calendar)
    fill = data >= 1e19
    data[fill] = np.nan
    keep_lat = (lat >= south) & (lat <= north)
    keep_lon = (lon >= west % 360) & (lon <= east % 360)
    # Mean of cells whose centers fall in the box (0.25° grid, so cells are near-equal area).
    regional = np.nanmean(data[:, keep_lat][:, :, keep_lon], axis=(1, 2))
    days = len(regional)
    if calendar in ("360_day",) or days not in (365, 366):
        raise RuntimeError(f"Unsupported calendar/length in {path.name}: {calendar}, {days} days")
    lengths = NOLEAP.copy()
    if days == 366:
        lengths[1] = 29
    sums, start = [], 0
    for length in lengths:
        chunk = regional[start : start + length]
        if np.isnan(chunk).any():
            raise RuntimeError(f"Missing daily values in {path.name}")
        sums.append(float(chunk.sum()))
        start += length
    return sums, lengths


def download_nexgddp(
    models=DEFAULT_MODELS,
    bounds=PALOUSE_BOUNDS,
    output_dir="data/nexgddp",
    cache_dir=None,
    workers=4,
):
    """Save monthly baseline/future means per model plus an ensemble mean, and provenance."""
    try:
        import h5py  # noqa: F401
        import numpy  # noqa: F401
        import requests
    except ImportError as exc:
        raise RuntimeError("Install requests, numpy, and h5py in your Python environment.") from exc
    cache_dir = Path(cache_dir or Path(output_dir) / "raw")
    cache_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    jobs, files_used = [], {}
    for model in models:
        for label, first, last, scenario in PERIODS:
            for variable in VARIABLES:
                available = list_files(session, model, scenario, variable)
                missing = [y for y in range(first, last + 1) if y not in available]
                if missing:
                    raise RuntimeError(f"{model} {scenario} {variable} is missing years {missing}")
                for year in range(first, last + 1):
                    jobs.append((model, label, variable, year, available[year]))
                    files_used.setdefault(model, set()).add(Path(available[year]).name)
    print(f"Fetching {len(jobs)} Palouse subsets from NCCS THREDDS...", flush=True)
    done = 0

    def work(job):
        model, label, variable, year, url_path = job
        return job, monthly_sums(
            fetch_subset(session, url_path, variable, bounds, cache_dir), variable, bounds
        )

    totals = {}
    with ThreadPoolExecutor(workers) as pool:
        for (model, label, variable, _year, _), (sums, lengths) in pool.map(work, jobs):
            key = (model, label, variable)
            acc = totals.setdefault(key, {"sum": [0.0] * 12, "days": [0] * 12, "years": 0})
            acc["sum"] = [a + b for a, b in zip(acc["sum"], sums, strict=False)]
            acc["days"] = [a + b for a, b in zip(acc["days"], lengths, strict=False)]
            acc["years"] += 1
            done += 1
            if done % 40 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}", flush=True)
    rows = []
    for model in models:
        for label, first, last, scenario in PERIODS:
            tas, pr = totals[(model, label, "tas")], totals[(model, label, "pr")]
            for m in range(12):
                rows.append(
                    {
                        "period": label,
                        "start_year": first,
                        "end_year": last,
                        "model": model,
                        "scenario": scenario,
                        "month": m + 1,
                        # pr is kg m-2 s-1 (= mm/s):
                        # daily flux sum × 86400 / years = mean monthly total.
                        "precipitation_mm": pr["sum"][m] * 86400 / pr["years"],
                        # tas is K: mean over all days in the month across the period.
                        "temperature_c": tas["sum"][m] / tas["days"][m] - 273.15,
                    }
                )
    for label, first, last, scenario in PERIODS:
        for m in range(12):
            members = [r for r in rows if r["period"] == label and r["month"] == m + 1]
            rows.append(
                {
                    "period": label,
                    "start_year": first,
                    "end_year": last,
                    "model": "ensemble_mean",
                    "scenario": scenario,
                    "month": m + 1,
                    "precipitation_mm": sum(r["precipitation_mm"] for r in members) / len(members),
                    "temperature_c": sum(r["temperature_c"] for r in members) / len(members),
                }
            )
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    csv_path = directory / "palouse_climate_nexgddp_ensemble_ssp245_2050.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "dataset": "NASA NEX-GDDP-CMIP6",
        "doi": DOI,
        "source": SOURCE,
        "access": f"{THREDDS}/ncss/grid/{DATASET_ROOT}/ (NetCDF Subset Service, no login)",
        "models": list(models),
        "member": "r1i1p1f1",
        "scenario": "SSP2-4.5",
        "ensemble": "ensemble_mean rows are the unweighted mean of the listed models.",
        "bounds_west_south_east_north": list(bounds),
        "region_note": "Mean of 0.25° grid cells whose centers fall in the box.",
        "baseline": "1995–2014 historical model simulation; not observations",
        "future": "2041–2060 (20-year climate centered around 2050)",
        "temperature": "Monthly mean daily near-surface temperature in °C; tas minus 273.15",
        "precipitation": "Mean monthly precipitation total in mm; sum(pr) × 86400 / 20 years",
        "file_versions": "Newest available version per year (_v2.0 > _v1.1 > unversioned).",
        "files_per_model": {m: len(f) for m, f in files_used.items()},
        "limitations": (
            "Bias-corrected, statistically downscaled GCM output at 0.25°; one ensemble member per"
            " model; unweighted ensemble. Regional means, not field-level. Not a forecast of any "
            "specific year."
        ),
        "related": "climate.py builds the same table for ACCESS-CM2 through Earth Engine.",
        "downloaded_utc": datetime.now(UTC).isoformat(),
    }
    csv_path.with_suffix(".json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"
    )
    return csv_path


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--bounds", nargs=4, type=float, default=PALOUSE_BOUNDS)
    parser.add_argument("--output-dir", default="data/nexgddp")
    parser.add_argument("--cache-dir", help="Where per-file subsets go (default: OUTPUT_DIR/raw).")
    parser.add_argument("--workers", type=int, default=4, help="Parallel NCSS requests.")
    args = parser.parse_args()
    try:
        path = download_nexgddp(
            args.models, args.bounds, args.output_dir, args.cache_dir, args.workers
        )
    except Exception as exc:
        parser.exit(1, f"NEX-GDDP import failed: {exc}\n")
    print(f"Saved NEX-GDDP data: {path}")


if __name__ == "__main__":
    main()
