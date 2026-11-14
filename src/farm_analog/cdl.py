"""Summarize the USDA NASS Cropland Data Layer (CDL) for the Palouse.

Downloads the national 30 m CDL release zip from NASS (about 2 GB, cached),
reads only the Palouse window, and writes the crop/land-cover acreage within
the same approximate lon/lat box used by the SMAP and ECOSTRESS importers.

The CropScape web service (nassgeodata.gmu.edu) serves the same data, but is
often slow or unavailable, so this uses the national release file instead.
No login is needed.

Run from the repo root:
    PYTHONPATH=src python -m farm_analog.cdl --year 2025
"""
import argparse
import csv
import json
import struct
import time
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

NASS_RELEASE = ("https://www.nass.usda.gov/sites/default/files/Research_and_Science/"
                "Cropland/Release/datasets/{year}_30m_cdls.zip")
CROPSCAPE = "https://nassgeodata.gmu.edu/CropScape/"
# Same approximate Washington Palouse demo extent as the SMAP importer.
PALOUSE_BOUNDS = (-118.2, 46.5, -117.0, 47.2)
SQ_M_PER_ACRE = 4046.8564224
FIELDS = ["code", "class_name", "pixels", "acres", "hectares", "percent_of_mapped"]


def validate_request(year, bounds):
    # The 30 m national CDL begins in 2008; a year's release appears early the next year.
    if not 2008 <= year < date.today().year:
        raise ValueError(f"Year must be between 2008 and {date.today().year - 1}.")
    west, south, east, north = bounds
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Bounds must be west south east north in longitude/latitude.")


def _fetch_segment(url, part, start, end):
    """Download bytes [start, end] into part, resuming from whatever it already holds."""
    import requests

    for attempt in range(8):
        have = part.stat().st_size if part.exists() else 0
        if start + have > end:
            return
        try:
            headers = {"Range": f"bytes={start + have}-{end}"}
            with requests.get(url, headers=headers, stream=True, timeout=120) as response:
                if response.status_code != 206:
                    raise RuntimeError(f"Server ignored range request (HTTP {response.status_code}).")
                with part.open("ab") as handle:
                    for chunk in response.iter_content(1 << 20):
                        handle.write(chunk)
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError):
            if attempt == 7:
                raise
            time.sleep(min(2 ** attempt * 5, 120))


def download_release(year, cache_dir, connections=8):
    """Download the national CDL zip in parallel resumable segments and return its path.

    NASS throttles each connection (~0.05-0.1 MB/s), so one stream takes hours.
    Segments are kept as .partNN files until all are complete, then joined.
    """
    import requests
    from concurrent.futures import ThreadPoolExecutor

    url = NASS_RELEASE.format(year=year)
    path = Path(cache_dir) / url.rsplit("/", 1)[-1]
    if path.exists():
        return path
    head = requests.head(url, allow_redirects=True, timeout=60)
    if head.status_code == 404:
        raise RuntimeError(f"No national CDL release found for {year}: {url}")
    head.raise_for_status()
    size = int(head.headers["Content-Length"])
    step = -(-size // connections)
    segments = [(path.with_name(f"{path.name}.part{i:02d}"), i * step, min((i + 1) * step, size) - 1)
                for i in range(connections)]
    legacy = path.with_name(path.name + ".part")  # single-stream partial from earlier versions
    if legacy.exists() and not segments[0][0].exists() and legacy.stat().st_size <= step:
        legacy.replace(segments[0][0])
    with ThreadPoolExecutor(connections) as pool:
        for future in [pool.submit(_fetch_segment, url, *seg) for seg in segments]:
            future.result()
    for part, start, end in segments:
        if part.stat().st_size != end - start + 1:
            raise RuntimeError(f"Segment {part.name} is incomplete; rerun to resume.")
    tmp = path.with_name(path.name + ".joining")
    with tmp.open("wb") as out:
        for part, _, _ in segments:
            with part.open("rb") as handle:
                while chunk := handle.read(1 << 24):
                    out.write(chunk)
    tmp.replace(path)
    for part, _, _ in segments:
        part.unlink()
    return path


def read_class_names(zip_path):
    """Map CDL codes to class names from the release's .vat.dbf attribute table."""
    with zipfile.ZipFile(zip_path) as archive:
        member = next(n for n in archive.namelist() if n.lower().endswith(".tif.vat.dbf"))
        data = archive.read(member)
    count, header_len, record_len = struct.unpack("<IHH", data[4:12])
    fields, offset = [], 1  # each record starts with a deletion flag byte
    for pos in range(32, header_len - 1, 32):
        name = data[pos:pos + 11].split(b"\0", 1)[0].decode("ascii").lower()
        width = data[pos + 16]
        fields.append((name, offset, width))
        offset += width
    columns = {name: (start, width) for name, start, width in fields}
    value_col = next(c for c in ("value", "code") if c in columns)
    name_col = next(c for c in ("class_name", "class_names", "category") if c in columns)
    names = {}
    for i in range(count):
        record = data[header_len + i * record_len: header_len + (i + 1) * record_len]
        get = lambda col: record[columns[col][0]:sum(columns[col])].decode("latin-1").strip()
        if get(name_col):
            names[int(float(get(value_col)))] = get(name_col)
    return names


def summarize_cdl(zip_path, bounds):
    """Return ({code: pixel_count}, pixel_area_m2, crs_wkt) for pixel centers inside bounds."""
    import numpy as np
    import rasterio
    from rasterio.warp import transform, transform_bounds
    from rasterio.windows import from_bounds

    with zipfile.ZipFile(zip_path) as archive:
        member = next(n for n in archive.namelist() if n.lower().endswith(".tif"))
    with rasterio.open(f"zip://{Path(zip_path).resolve().as_posix()}!/{member}") as src:
        box = transform_bounds("EPSG:4326", src.crs, *bounds, densify_pts=21)
        window = from_bounds(*box, transform=src.transform).round_offsets().round_lengths()
        codes = src.read(1, window=window)
        win_transform = src.window_transform(window)
        nodata = src.nodata
        pixel_area = abs(src.res[0] * src.res[1])
        crs_wkt = src.crs.to_wkt()
        crs = src.crs
    # The projected window is the lon/lat box's envelope; keep only pixel centers inside the box.
    rows, cols = np.mgrid[0:codes.shape[0], 0:codes.shape[1]]
    xs, ys = rasterio.transform.xy(win_transform, rows.ravel(), cols.ravel())
    lons, lats = transform(crs, "EPSG:4326", xs, ys)
    lons, lats = np.asarray(lons).reshape(codes.shape), np.asarray(lats).reshape(codes.shape)
    west, south, east, north = bounds
    inside = (lons >= west) & (lons <= east) & (lats >= south) & (lats <= north)
    mapped = inside & (codes != 0) & ((codes != nodata) if nodata is not None else True)
    values, counts = np.unique(codes[mapped], return_counts=True)
    return dict(zip(values.tolist(), counts.tolist())), pixel_area, crs_wkt


def download_cdl(year=2025, bounds=PALOUSE_BOUNDS, output_dir="data/cdl", cache_dir=None):
    """Save per-class CDL acreage for the region and provenance."""
    validate_request(year, bounds)
    try:
        import numpy  # noqa: F401
        import rasterio  # noqa: F401
        import requests  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Install requests, numpy, and rasterio in your Python environment.") from exc
    cache_dir = Path(cache_dir or Path(output_dir) / "raw")
    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_path = download_release(year, cache_dir)
    names = read_class_names(zip_path)
    counts, pixel_area, crs_wkt = summarize_cdl(zip_path, bounds)
    if not counts:
        raise RuntimeError("No mapped CDL pixels in this region; no files written.")
    total = sum(counts.values())
    rows = [{
        "code": code, "class_name": names.get(code, ""), "pixels": n,
        "acres": round(n * pixel_area / SQ_M_PER_ACRE, 1),
        "hectares": round(n * pixel_area / 10_000, 1),
        "percent_of_mapped": round(100 * n / total, 3),
    } for code, n in counts.items()]
    rows.sort(key=lambda r: -r["pixels"])
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    csv_path = directory / f"palouse_cdl_{year}.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "dataset": "USDA NASS Cropland Data Layer (CDL)", "year": year,
        "source": NASS_RELEASE.format(year=year), "viewer": CROPSCAPE,
        "bounds_west_south_east_north": list(bounds),
        "region_note": "Approximate demo extent; custom bounds may override it. Pixels whose centers fall inside the lon/lat box are counted.",
        "rows": len(rows), "mapped_pixels": total,
        "mapped_acres": round(total * pixel_area / SQ_M_PER_ACRE, 1),
        "native_resolution_m": 30, "pixel_area_m2": pixel_area,
        "crs_wkt": crs_wkt,
        "aggregation": "Pixel counts per CDL class; acres and hectares are pixel count times pixel area. Code 0 (background/no data) is excluded.",
        "limitations": "CDL is a classified satellite product with per-class accuracy that varies by crop and state; pixel-counted acreage is biased for small or mixed classes and is not an official NASS acreage estimate. Single year, not a rotation or forecast.",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
    }
    csv_path.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    return csv_path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--bounds", nargs=4, type=float, default=PALOUSE_BOUNDS)
    parser.add_argument("--output-dir", default="data/cdl")
    parser.add_argument("--cache-dir", help="Where the national zip goes (default: OUTPUT_DIR/raw).")
    args = parser.parse_args()
    try:
        path = download_cdl(args.year, args.bounds, args.output_dir, args.cache_dir)
    except Exception as exc:
        parser.exit(1, f"CDL import failed: {exc}\n")
    print(f"Saved CDL data: {path}")


if __name__ == "__main__":
    main()
