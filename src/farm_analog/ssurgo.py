"""Summarize USDA NRCS SSURGO soil map units for the Palouse.

Queries the Soil Data Access (SDA) web service, which needs no login, for every
SSURGO map unit intersecting the region. Map-unit acreage is computed on the
server by clipping polygons to the box, in a grid of sub-boxes so each query
stays under SDA's time limit. Map-unit attributes come from the mapunit,
muaggatt, and component tables.

Run from the repo root:
    PYTHONPATH=src python -m farm_analog.ssurgo
"""
import argparse
import csv
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SDA_URL = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"
# Same approximate Washington Palouse demo extent as the SMAP importer.
PALOUSE_BOUNDS = (-118.2, 46.5, -117.0, 47.2)
SQ_M_PER_ACRE = 4046.8564224
FIELDS = ["mukey", "areasymbol", "musym", "muname", "acres", "percent_of_mapped",
          "dominant_component", "dominant_component_pct", "farmland_class",
          "drainage_class", "nonirrigated_capability_class", "hydrologic_group",
          "aws_0_100cm_cm", "slope_pct", "water_table_min_cm", "bedrock_min_cm"]


def validate_bounds(bounds):
    west, south, east, north = bounds
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Bounds must be west south east north in longitude/latitude.")
    if (east - west) * (north - south) > 4:
        raise ValueError("Keep the region under 4 square degrees; SDA queries time out.")


def query(session, sql):
    """Run one SDA SQL query and return a list of row dicts."""
    for attempt in range(4):
        response = session.post(SDA_URL, json={"query": sql, "format": "JSON+COLUMNNAME"}, timeout=300)
        if response.ok:
            table = response.json().get("Table", [])
            return [dict(zip(table[0], row)) for row in table[1:]] if table else []
        if "timed out" not in response.text or attempt == 3:
            raise RuntimeError(f"SDA query failed (HTTP {response.status_code}): {response.text[:300]}")
        time.sleep(5 * 2 ** attempt)
    return []


def box_wkt(west, south, east, north):
    return f"POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south}))"


def mapunit_areas(session, bounds, grid=4):
    """Return {mukey: area_m2} for polygons clipped to the box, summed over a grid of sub-boxes."""
    west, south, east, north = bounds
    dx, dy = (east - west) / grid, (north - south) / grid
    areas = defaultdict(float)
    for i in range(grid):
        for j in range(grid):
            wkt = box_wkt(west + i * dx, south + j * dy, west + (i + 1) * dx, south + (j + 1) * dy)
            aoi = f"geometry::STGeomFromText('{wkt}', 4326)"
            # Clip in planar lon/lat, then measure the clipped shape as geography (m²).
            sql = f"""
                SELECT P.mukey, SUM(geography::STGeomFromText(
                    P.mupolygongeo.STIntersection({aoi}).MakeValid().STAsText(), 4326
                ).MakeValid().STArea()) AS area_m2
                FROM mupolygon P
                INNER JOIN SDA_Get_Mupolygonkey_from_intersection_with_WktWgs84('{wkt}') K
                    ON P.mupolygonkey = K.mupolygonkey
                GROUP BY P.mukey"""
            for row in query(session, sql):
                areas[str(row["mukey"])] += float(row["area_m2"] or 0)
    return dict(areas)


def mapunit_attributes(session, mukeys):
    """Return {mukey: attribute dict} from mapunit, legend, muaggatt, and component."""
    attrs, keys = {}, sorted(mukeys)
    for start in range(0, len(keys), 300):
        key_list = ",".join(keys[start:start + 300])
        for row in query(session, f"""
                SELECT mu.mukey, l.areasymbol, mu.musym, mu.muname, mu.farmlndcl,
                       ma.drclassdcd, ma.niccdcd, ma.hydgrpdcd, ma.aws0100wta,
                       ma.slopegradwta, ma.wtdepannmin, ma.brockdepmin
                FROM mapunit mu
                INNER JOIN legend l ON l.lkey = mu.lkey
                LEFT JOIN muaggatt ma ON ma.mukey = mu.mukey
                WHERE mu.mukey IN ({key_list})"""):
            attrs[str(row["mukey"])] = row
        for row in query(session, f"""
                SELECT mukey, compname, comppct_r FROM component
                WHERE mukey IN ({key_list}) AND comppct_r IS NOT NULL"""):
            current = attrs.get(str(row["mukey"]))
            pct = int(row["comppct_r"])
            if current is not None and pct > current.get("_dominant_pct", -1):
                current["_dominant"], current["_dominant_pct"] = row["compname"], pct
    return attrs


def download_ssurgo(bounds=PALOUSE_BOUNDS, output_dir="data/ssurgo"):
    """Save per-map-unit acreage and soil attributes for the region, plus provenance."""
    validate_bounds(bounds)
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Install requests in your Python environment.") from exc
    session = requests.Session()
    areas = mapunit_areas(session, bounds)
    areas = {k: v for k, v in areas.items() if v > 0}
    if not areas:
        raise RuntimeError("No SSURGO map units in this region; no files written.")
    attrs = mapunit_attributes(session, areas)
    total = sum(areas.values())
    rows = []
    for mukey, area in areas.items():
        a = attrs.get(mukey, {})
        rows.append({
            "mukey": mukey, "areasymbol": a.get("areasymbol"), "musym": a.get("musym"),
            "muname": a.get("muname"), "acres": round(area / SQ_M_PER_ACRE, 1),
            "percent_of_mapped": round(100 * area / total, 3),
            "dominant_component": a.get("_dominant"), "dominant_component_pct": a.get("_dominant_pct"),
            "farmland_class": a.get("farmlndcl"), "drainage_class": a.get("drclassdcd"),
            "nonirrigated_capability_class": a.get("niccdcd"), "hydrologic_group": a.get("hydgrpdcd"),
            "aws_0_100cm_cm": a.get("aws0100wta"), "slope_pct": a.get("slopegradwta"),
            "water_table_min_cm": a.get("wtdepannmin"), "bedrock_min_cm": a.get("brockdepmin"),
        })
    rows.sort(key=lambda r: -r["acres"])
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    csv_path = directory / "palouse_ssurgo_mapunits.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "dataset": "USDA NRCS Soil Survey Geographic Database (SSURGO)",
        "source": SDA_URL, "documentation": "https://sdmdataaccess.nrcs.usda.gov/",
        "survey_areas": sorted({r["areasymbol"] for r in rows if r["areasymbol"]}),
        "bounds_west_south_east_north": list(bounds),
        "region_note": "Approximate demo extent; custom bounds may override it. Polygons are clipped to the lon/lat box.",
        "rows": len(rows), "mapped_acres": round(total / SQ_M_PER_ACRE, 1),
        "aggregation": "One row per map unit: clipped polygon area (geodesic) and map-unit attributes. Dominant component is the highest comppct_r.",
        "attribute_notes": {
            "aws_0_100cm_cm": "Available water storage 0-100 cm, weighted average (muaggatt.aws0100wta).",
            "drainage_class": "Dominant-condition drainage class (muaggatt.drclassdcd).",
            "nonirrigated_capability_class": "Dominant-condition land capability class, non-irrigated (muaggatt.niccdcd).",
            "hydrologic_group": "Dominant-condition hydrologic soil group (muaggatt.hydgrpdcd).",
            "slope_pct": "Weighted-average slope gradient (muaggatt.slopegradwta).",
            "water_table_min_cm": "Minimum annual depth to water table (muaggatt.wtdepannmin).",
            "bedrock_min_cm": "Minimum depth to bedrock (muaggatt.brockdepmin).",
        },
        "limitations": "SSURGO map units are mixtures of soil components mapped at roughly 1:12,000-1:24,000; attributes are map-unit aggregates, not field or point measurements. Empty values mean SDA has no value.",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
    }
    csv_path.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    return csv_path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bounds", nargs=4, type=float, default=PALOUSE_BOUNDS)
    parser.add_argument("--output-dir", default="data/ssurgo")
    args = parser.parse_args()
    try:
        path = download_ssurgo(args.bounds, args.output_dir)
    except Exception as exc:
        parser.exit(1, f"SSURGO import failed: {exc}\n")
    print(f"Saved SSURGO data: {path}")


if __name__ == "__main__":
    main()
