"""Download regional ECOSTRESS land surface temperature (LST) summaries.

Searches NASA CMR for ECOSTRESS L2T LSTE v002 tiles (70 m, MGRS-tiled), downloads
each tile's LST and cloud-mask GeoTIFFs from LP DAAC, clips them to the region,
and writes one row per tile overpass.

Needs a NASA Earthdata login in ~/.netrc (or %USERPROFILE%\\_netrc on Windows):
    machine urs.earthdata.nasa.gov login USER password PASS

Run from the repo root:
    PYTHONPATH=src python -m farm_analog.ecostress
"""

import argparse
import csv
import json
import time
from datetime import UTC, date, datetime
from pathlib import Path

ECOSTRESS_SHORT_NAME = "ECO_L2T_LSTE"
ECOSTRESS_VERSION = "002"
ECOSTRESS_DOI = "10.5067/ECOSTRESS/ECO_L2T_LSTE.002"
CMR_GRANULES = "https://cmr.earthdata.nasa.gov/search/granules.json"
# Same approximate Washington Palouse demo extent as the SMAP importer.
PALOUSE_BOUNDS = (-118.2, 46.5, -117.0, 47.2)
FIELDS = [
    "timestamp_utc",
    "granule_id",
    "tile",
    "lst_mean_k",
    "lst_std_k",
    "lst_min_k",
    "lst_max_k",
    "lst_valid_count",
    "cloud_count",
    "pixel_count",
]


def validate_request(start, end, bounds):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    # Collection 2 tiled products begin with the mission's first data in July 2018.
    if first < date(2018, 7, 1) or first >= last:
        raise ValueError("Dates must start on/after 2018-07-01 and end after start (exclusive).")
    if (last - first).days > 31:
        raise ValueError("Download at most 31 days per request (each tile is a few MB).")
    west, south, east, north = bounds
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Bounds must be west south east north in longitude/latitude.")


def search_granules(session, start, end, bounds):
    """Return [(granule_id, {suffix: url})] for tiles intersecting the region."""
    params = {
        "short_name": ECOSTRESS_SHORT_NAME,
        "version": ECOSTRESS_VERSION,
        "bounding_box": ",".join(str(v) for v in bounds),
        "temporal": f"{start}T00:00:00Z,{end}T00:00:00Z",
        "page_size": 2000,
    }
    response = session.get(CMR_GRANULES, params=params, timeout=60)
    response.raise_for_status()
    granules = []
    for entry in response.json()["feed"]["entry"]:
        links = {}
        for link in entry.get("links", []):
            href = link.get("href", "")
            for suffix in ("LST", "cloud"):
                if href.startswith("https://") and href.endswith(f"_{suffix}.tif"):
                    links[suffix] = href
        if len(links) == 2:
            granules.append((entry["title"], links))
    return granules


def download(session, url, cache_dir):
    path = Path(cache_dir) / url.rsplit("/", 1)[-1]
    if not path.exists():
        # requests reads netrc for the Earthdata redirect; the session keeps the cookie.
        for attempt in range(4):  # LP DAAC returns occasional transient 5xx errors.
            response = session.get(url, timeout=300)
            if response.status_code < 500 or attempt == 3:
                break
            time.sleep(2**attempt * 5)
        if response.status_code in (401, 403):
            raise RuntimeError(
                "Earthdata login rejected; check your netrc and that LP DAAC is authorized."
            )
        response.raise_for_status()
        tmp = path.with_suffix(".part")
        tmp.write_bytes(response.content)
        tmp.replace(path)
    return path


def summarize_tile(lst_path, cloud_path, bounds):
    """Clip a tile to the lon/lat box and summarize clear-sky LST pixels."""
    import numpy as np
    import rasterio
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds

    with rasterio.open(lst_path) as lst_src, rasterio.open(cloud_path) as cloud_src:
        box = transform_bounds("EPSG:4326", lst_src.crs, *bounds, densify_pts=21)
        window = from_bounds(*box, transform=lst_src.transform).round_offsets().round_lengths()
        try:
            window = window.intersection(
                rasterio.windows.Window(0, 0, lst_src.width, lst_src.height)
            )
        except rasterio.errors.WindowError:
            return None  # CMR footprint touches the box, but no tile pixels fall inside it.
        lst = lst_src.read(1, window=window).astype("float64")
        cloud = cloud_src.read(1, window=window)
    # The UTM window is the projected box's envelope, so edges extend slightly past it.
    # v002 tiles already set cloudy pixels to NaN in LST; the mask is applied again
    # defensively. Pixels that are NaN but not cloudy are outside the swath or other fill.
    cloudy = cloud == 1
    clear = lst[np.isfinite(lst) & ~cloudy]
    stats = {
        "lst_valid_count": int(clear.size),
        "cloud_count": int(cloudy.sum()),
        "pixel_count": int(lst.size),
    }
    if clear.size:
        stats.update(
            lst_mean_k=float(clear.mean()),
            lst_std_k=float(clear.std()),
            lst_min_k=float(clear.min()),
            lst_max_k=float(clear.max()),
        )
    return stats


def download_ecostress(
    start="2025-07-01",
    end="2025-07-08",
    bounds=PALOUSE_BOUNDS,
    output_dir="data/ecostress",
    cache_dir=None,
):
    """Save per-tile clear-sky LST summaries (Kelvin) and provenance.

    End date is exclusive. Cloudy or missing pixels are excluded; tiles with no
    clear pixels keep empty LST values rather than zeros.
    """
    validate_request(start, end, bounds)
    try:
        import rasterio  # noqa: F401
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "Install requests, numpy, and rasterio in your Python environment."
        ) from exc
    cache_dir = Path(cache_dir or Path(output_dir) / "raw")
    cache_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    granules = search_granules(session, start, end, bounds)
    if not granules:
        raise RuntimeError("No ECOSTRESS tiles found for the requested dates; no files written.")
    rows = []
    for granule_id, links in granules:
        # e.g. ECOv002_L2T_LSTE_39657_008_11TMN_20250704T115216_0713_01
        parts = granule_id.split("_")
        tile, stamp = parts[5], parts[6]
        stats = summarize_tile(
            download(session, links["LST"], cache_dir),
            download(session, links["cloud"], cache_dir),
            bounds,
        )
        if stats is None:
            continue
        rows.append(
            {
                "timestamp_utc": datetime.strptime(stamp, "%Y%m%dT%H%M%S").strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "granule_id": granule_id,
                "tile": tile,
                **stats,
            }
        )
    rows.sort(key=lambda r: (r["timestamp_utc"], r["tile"]))
    if not any(r["lst_valid_count"] for r in rows):
        raise RuntimeError("No clear-sky LST pixels in this region; no files written.")
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    csv_path = directory / f"palouse_ecostress_lst_{start}_{end}.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "collection": f"{ECOSTRESS_SHORT_NAME}.{ECOSTRESS_VERSION}",
        "doi": ECOSTRESS_DOI,
        "source": "https://lpdaac.usgs.gov/products/eco_l2t_lstev002/",
        "bounds_west_south_east_north": list(bounds),
        "region_note": (
            "Approximate demo extent; custom bounds may override it. Pixels are clipped to the "
            "box's UTM envelope."
        ),
        "start_inclusive": start,
        "end_exclusive": end,
        "rows": len(rows),
        "overpasses": len({r["timestamp_utc"] for r in rows}),
        "units": "K",
        "native_resolution_m": 70,
        "tile_crs": "UTM (MGRS tiles 11T*)",
        "aggregation": (
            "One row per MGRS tile per overpass: clear-sky pixel stats; counts are pixels in the "
            "clipped window. Adjacent tiles overlap, so do not sum counts across tiles."
        ),
        "cloud_masking": (
            "Pixels with cloud mask == 1 or missing LST are excluded. cloud_count is "
            "cloud-flagged pixels in the window; pixel_count minus valid and cloud counts is "
            "mostly outside-swath fill."
        ),
        "limitations": (
            "ISS orbit gives irregular overpass times (often night); timestamps are UTC. LST is "
            "land surface skin temperature, not air temperature."
        ),
        "downloaded_utc": datetime.now(UTC).isoformat(),
    }
    csv_path.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    return csv_path


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--start", default="2025-07-01")
    parser.add_argument("--end", default="2025-07-08")
    parser.add_argument("--bounds", nargs=4, type=float, default=PALOUSE_BOUNDS)
    parser.add_argument("--output-dir", default="data/ecostress")
    parser.add_argument("--cache-dir", help="Where raw GeoTIFFs go (default: OUTPUT_DIR/raw).")
    args = parser.parse_args()
    try:
        path = download_ecostress(
            args.start, args.end, args.bounds, args.output_dir, args.cache_dir
        )
    except Exception as exc:
        parser.exit(1, f"ECOSTRESS import failed: {exc}\n")
    print(f"Saved ECOSTRESS data: {path}")


if __name__ == "__main__":
    main()
