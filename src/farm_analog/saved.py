"""Saved live results for the test fields (M11), so the demo works without Earth Engine.

Someone with Earth Engine runs ``python -m farm_analog.saved`` once. It analyzes each test
field in ``config.TEST_FIELDS`` live, for every scenario, and saves each ``AnalogResult`` as
``data/samples/live_<field>_<scenario>.json`` (committed). In offline mode, a drawn field near
a test field gets that saved result, with a note saying so.
``python -m farm_analog.saved --traits-only`` adds M19's rotation traits to the saved files
without Earth Engine.

Data flow:
Inputs:  live mode: pipeline.analyze on each test field (Earth Engine via M1-M4, M7);
         offline: the saved JSON files and a drawn field (schema.PolygonGeometry).
Outputs: data/samples/live_<field>_<scenario>.json; ``nearest_saved`` -> (AnalogResult with an
         extra note, distance in km) or None.
Used by: pipeline._analyze_offline; ``python -m farm_analog.saved``; tests/test_saved.py.
"""

import json
import math
from datetime import date
from pathlib import Path

from shapely.geometry import Polygon

from farm_analog import config
from farm_analog.schema import AnalogRequest, AnalogResult, PolygonGeometry

SAVED_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"
SCENARIOS = ("ssp245", "ssp585")
HALF_SIDE_DEG = 0.0025  # each test field is a ~400 m square around its point


def path_for(name: str, scenario: str, folder: Path = SAVED_DIR) -> Path:
    return folder / f"live_{name}_{scenario}.json"


def test_field_request(name: str, scenario: str) -> AnalogRequest:
    _, lat, lon = config.TEST_FIELDS[name]
    h = HALF_SIDE_DEG
    ring = [[lon - h, lat - h], [lon + h, lat - h], [lon + h, lat + h], [lon - h, lat + h],
            [lon - h, lat - h]]
    return AnalogRequest.model_validate(
        {"field": {"type": "Polygon", "coordinates": [ring]}, "scenario": scenario}
    )


def distance_km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def nearest_saved(
    field: PolygonGeometry,
    scenario: str,
    top_n: int,
    folder: Path = SAVED_DIR,
    radius_km: float = config.SAVED_RESULT_RADIUS_KM,
):
    """The closest test field's saved result for ``scenario`` within ``radius_km``, trimmed
    to ``top_n`` matches and with a note saying whose result it is; else None."""
    shell, *holes = field.coordinates
    center = Polygon(shell, holes).centroid
    best = None
    for name, (label, lat, lon) in config.TEST_FIELDS.items():
        path = path_for(name, scenario, folder)
        if not path.exists():
            continue
        km = distance_km(center.y, center.x, lat, lon)
        if km <= radius_km and (best is None or km < best[0]):
            best = (km, label, path)
    if best is None:
        return None
    km, label, path = best
    saved = AnalogResult.model_validate_json(path.read_text())
    note = (
        f"Saved live result for the {label} test field ({km:.1f} km from your field's "
        "center), computed with Earth Engine. Your own field's climate may differ slightly."
    )
    return saved.model_copy(update={"analogs": saved.analogs[:top_n],
                                    "notes": [note, *saved.notes]}), km


def save_all(folder: Path = SAVED_DIR) -> list[Path]:
    """Analyze every test field live for every scenario and save the results."""
    from farm_analog import pipeline

    if pipeline.mode() != "live":
        raise RuntimeError("Saving live results needs Earth Engine (set EE_PROJECT in .env)")
    written = []
    for name, (label, _, _) in config.TEST_FIELDS.items():
        for scenario in SCENARIOS:
            result = pipeline.analyze(test_field_request(name, scenario))
            result = result.model_copy(update={"field_id": f"test-{name}"})
            path = path_for(name, scenario, folder)
            path.write_text(result.model_dump_json(indent=2) + "\n")
            best = result.analogs[0] if result.analogs else None
            print(f"{label} {scenario}: best sigma {best.sigma if best else None} "
                  f"({best.place_name if best else '-'}) -> {path.name}", flush=True)
            written.append(path)
    (folder / "live_results.json").write_text(json.dumps({
        "computed": date.today().isoformat(),
        "fields": {n: {"label": v[0], "lat": v[1], "lon": v[2]}
                   for n, v in config.TEST_FIELDS.items()},
        "scenarios": list(SCENARIOS),
    }, indent=2) + "\n")
    return written


def add_traits_to_saved(folder: Path = SAVED_DIR) -> list[Path]:
    """Add M19's rotation traits to results saved before M19. Offline: the traits come from a
    fixed table, so no Earth Engine run is needed and nothing else in the files changes."""
    from farm_analog import rotations

    written = []
    for name in config.TEST_FIELDS:
        for scenario in SCENARIOS:
            path = path_for(name, scenario, folder)
            if not path.exists():
                continue
            result = rotations.add_traits(AnalogResult.model_validate_json(path.read_text()))
            path.write_text(result.model_dump_json(indent=2) + "\n")
            written.append(path)
    return written


if __name__ == "__main__":
    import sys

    if "--traits-only" in sys.argv:
        for p in add_traits_to_saved():
            print("traits added:", p.name)
    else:
        from dotenv import load_dotenv

        load_dotenv()
        save_all()
