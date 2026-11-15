"""Download daily GPM IMERG precipitation for the Palouse.

Uses the GES DISC OPeNDAP server to fetch only the Palouse cells of the IMERG
V07 Final Run daily product (GPM_3IMERGDF, 0.1°), about 40 KB per day instead
of a 31 MB global file, and writes one row per day.

Needs a NASA Earthdata login in ~/.netrc (or %USERPROFILE%\\_netrc on Windows)
with the "NASA GESDISC DATA ARCHIVE" application approved in your Earthdata
profile:
    machine urs.earthdata.nasa.gov login USER password PASS

Run from the repo root:
    PYTHONPATH=src python -m farm_analog.imerg --start 2024-10-01 --end 2025-10-01
"""
import argparse
import csv
import io
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

OPENDAP = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDF.07"
SHORT_NAME = "GPM_3IMERGDF"
VERSION = "07"
DOI = "10.5067/GPM/IMERGDF/DAY/07"
# Same approximate Washington Palouse demo extent as the SMAP importer.
PALOUSE_BOUNDS = (-118.2, 46.5, -117.0, 47.2)
GRID = 0.1  # IMERG cell centers sit at -179.95 + 0.1 i (lon) and -89.95 + 0.1 j (lat)
FIELDS = ["date", "precipitation_mean_mm", "precipitation_max_mm", "random_error_mean_mm",
          "liquid_probability_mean_pct", "cell_count"]


def validate_request(start, end, bounds):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first < date(1998, 1, 1) or first >= last:
        raise ValueError("Dates must start on/after 1998-01-01 and end after start (exclusive).")
    if (last - first).days > 366:
        raise ValueError("Download at most 366 days per request.")
    west, south, east, north = bounds
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Bounds must be west south east north in longitude/latitude.")


def cell_range(low, high, origin):
    """Indices of 0.1° cells whose centers fall within [low, high]."""
    first = math.ceil(round((low - origin) / GRID, 6))
    last = math.floor(round((high - origin) / GRID, 6))
    if first > last:
        raise ValueError("Region is smaller than one IMERG cell.")
    return first, last


def day_url(day):
    stamp = day.strftime("%Y%m%d")
    return f"{OPENDAP}/{day:%Y}/{day:%m}/3B-DAY.MS.MRG.3IMERG.{stamp}-S000000-E235959.V07B.nc4"


def fetch_day(session, day, lon_idx, lat_idx, cache_dir):
    """Download (or reuse) the Palouse subset for one day and return its local path."""
    path = Path(cache_dir) / f"imerg_{day:%Y%m%d}_palouse.nc4"
    if path.exists() and path.stat().st_size:
        return path
    (i0, i1), (j0, j1) = lon_idx, lat_idx
    box = f"[0:0][{i0}:{i1}][{j0}:{j1}]"  # daily arrays are (time, lon, lat)
    ce = ";".join([f"precipitation{box}", f"randomError{box}",
                   f"probabilityLiquidPrecipitation{box}", f"lon[{i0}:{i1}]", f"lat[{j0}:{j1}]", "time"])
    for attempt in range(5):
        try:
            response = session.get(day_url(day) + ".dap.nc4", params={"dap4.ce": ce}, timeout=300)
            if response.status_code in (401, 403) or "/login" in response.url:
                raise PermissionError("Earthdata login rejected; check your netrc and that "
                                      "'NASA GESDISC DATA ARCHIVE' is approved in your Earthdata profile.")
            if response.status_code == 404:
                raise FileNotFoundError(f"No IMERG Final Run file for {day} (Final Run lags ~3.5 months).")
            if response.ok and response.content[:4] == b"\x89HDF":
                tmp = path.with_suffix(".part")
                tmp.write_bytes(response.content)
                tmp.replace(path)
                return path
        except (PermissionError, FileNotFoundError):
            raise
        except Exception:
            if attempt == 4:
                raise
        time.sleep(5 * 2 ** attempt)
    raise RuntimeError(f"OPeNDAP kept failing for {day}")


def summarize_day(path, day):
    import h5py
    import numpy as np

    with h5py.File(path, "r") as handle:
        def read(name):
            values = handle[name][:].astype("float64")
            values[values < 0] = np.nan  # -9999.9 fill; precipitation is never negative
            return values
        precip, error = read("precipitation"), read("randomError")
        liquid = read("probabilityLiquidPrecipitation")
    valid = np.isfinite(precip)
    row = {"date": day.isoformat(), "cell_count": int(valid.sum())}
    if valid.any():
        row.update(precipitation_mean_mm=float(np.nanmean(precip)),
                   precipitation_max_mm=float(np.nanmax(precip)),
                   random_error_mean_mm=float(np.nanmean(error)),
                   liquid_probability_mean_pct=float(np.nanmean(liquid)))
    return row


def download_imerg(start="2024-10-01", end="2025-10-01", bounds=PALOUSE_BOUNDS,
                   output_dir="data/imerg", cache_dir=None, workers=4):
    """Save daily regional precipitation statistics and provenance. End date is exclusive."""
    validate_request(start, end, bounds)
    try:
        import h5py  # noqa: F401
        import numpy  # noqa: F401
        import requests
    except ImportError as exc:
        raise RuntimeError("Install requests, numpy, and h5py in your Python environment.") from exc
    west, south, east, north = bounds
    lon_idx = cell_range(west, east, -179.95)
    lat_idx = cell_range(south, north, -89.95)
    cache_dir = Path(cache_dir or Path(output_dir) / "raw")
    cache_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()  # requests reads netrc for the Earthdata redirect
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    days = [first + timedelta(n) for n in range((last - first).days)]
    # Fetch one day first so a login problem fails fast instead of in every worker.
    fetch_day(session, days[0], lon_idx, lat_idx, cache_dir)
    print(f"Fetching {len(days)} daily Palouse subsets from GES DISC OPeNDAP...", flush=True)

    def work(day):
        return summarize_day(fetch_day(session, day, lon_idx, lat_idx, cache_dir), day)

    rows = []
    with ThreadPoolExecutor(workers) as pool:
        for n, row in enumerate(pool.map(work, days), 1):
            rows.append(row)
            if n % 50 == 0 or n == len(days):
                print(f"  {n}/{len(days)}", flush=True)
    if not any(r["cell_count"] for r in rows):
        raise RuntimeError("No valid IMERG cells in this region; no files written.")
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    csv_path = directory / f"palouse_imerg_daily_{start}_{end}.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    total = sum(r.get("precipitation_mean_mm") or 0 for r in rows)
    metadata = {
        "collection": f"{SHORT_NAME}.{VERSION}", "product": "IMERG V07 Final Run, daily",
        "doi": DOI, "source": "https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary",
        "access": f"{OPENDAP}/ (OPeNDAP subset, Earthdata login)",
        "bounds_west_south_east_north": list(bounds),
        "region_note": "Approximate demo extent; custom bounds may override it. Mean of 0.1° cells whose centers fall in the box.",
        "cell_index_ranges": {"lon": list(lon_idx), "lat": list(lat_idx)},
        "start_inclusive": start, "end_exclusive": end, "rows": len(rows),
        "period_total_precipitation_mm": round(total, 1),
        "units": {"precipitation": "mm/day", "random_error": "mm/day", "liquid_probability": "percent"},
        "aggregation": "Daily regional mean and maximum across cells; random error and liquid-precipitation probability are cell means. Days are UTC.",
        "limitations": "Satellite-gauge merged estimate at ~10 km; not station measurements. Final Run is gauge-adjusted monthly and lags ~3.5 months. Snowfall is included as liquid-equivalent but satellite snow retrievals are less reliable.",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
    }
    csv_path.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    return csv_path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", default="2024-10-01")
    parser.add_argument("--end", default="2025-10-01")
    parser.add_argument("--bounds", nargs=4, type=float, default=PALOUSE_BOUNDS)
    parser.add_argument("--output-dir", default="data/imerg")
    parser.add_argument("--cache-dir", help="Where per-day subsets go (default: OUTPUT_DIR/raw).")
    parser.add_argument("--workers", type=int, default=4, help="Parallel OPeNDAP requests.")
    args = parser.parse_args()
    try:
        path = download_imerg(args.start, args.end, args.bounds, args.output_dir, args.cache_dir, args.workers)
    except Exception as exc:
        parser.exit(1, f"IMERG import failed: {exc}\n")
    print(f"Saved IMERG data: {path}")


if __name__ == "__main__":
    main()
