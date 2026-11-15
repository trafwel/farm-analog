"""The full analysis for one drawn field (M5): farm today -> farm in 2050 -> candidates ->
match -> contract result.

Two modes:

- **live** (Earth Engine configured: ``EE_PROJECT`` set, ``FARM_ANALOG_OFFLINE`` not "1"):
  the real per-field analysis across every climate model.
- **offline demo** (no Earth Engine): the Palouse result computed from the team's committed
  data. It only answers for fields inside the Palouse demo area and only for SSP2-4.5, and
  says so in the result's notes; anything else is refused rather than faked.
"""

import hashlib
import json
import os

from shapely.geometry import Polygon

from farm_analog import config
from farm_analog.schema import AnalogRequest, AnalogResult, PolygonGeometry


class FieldNotSupported(ValueError):
    """The field can't be analyzed (wrong place, too big, invalid shape, unsupported mode)."""


def mode() -> str:
    if os.environ.get("FARM_ANALOG_OFFLINE") == "1" or not os.environ.get("EE_PROJECT"):
        return "offline-demo"
    return "live"


def field_id(field: PolygonGeometry) -> str:
    """A short, stable id for a field, so results can be cached without storing coordinates."""
    digest = hashlib.sha256(json.dumps(field.coordinates).encode()).hexdigest()
    return f"field-{digest[:12]}"


def field_area_km2(field: PolygonGeometry) -> float:
    """Area on the Earth's surface (WGS84 ellipsoid), not in degrees."""
    from pyproj import Geod

    area, _ = Geod(ellps="WGS84").geometry_area_perimeter(Polygon(*_rings(field)))
    return abs(area) / 1e6


def _rings(field: PolygonGeometry):
    shell, *holes = field.coordinates
    return shell, holes


def check_field(field: PolygonGeometry, region=config.SUPPORTED_REGION_BBOX) -> None:
    """Reject fields the analysis can't handle, with a reason a farmer can act on."""
    polygon = Polygon(*_rings(field))
    if not polygon.is_valid:
        raise FieldNotSupported("The field outline crosses itself. Please redraw it.")
    west, south, east, north = region
    lon, lat = polygon.centroid.x, polygon.centroid.y
    if not (west <= lon <= east and south <= lat <= north):
        raise FieldNotSupported("The field is outside the area this tool covers.")
    area = field_area_km2(field)
    if area > config.MAX_FIELD_AREA_KM2:
        raise FieldNotSupported(
            f"The field is {area:.0f} km²; the limit is {config.MAX_FIELD_AREA_KM2:.0f} km². "
            "Please draw a single field."
        )


def analyze(request: AnalogRequest) -> AnalogResult:
    """Run the analysis for a validated request in the current mode."""
    check_field(request.field)
    if mode() == "live":
        return _analyze_live(request)
    return _analyze_offline(request)


def _analyze_offline(request: AnalogRequest) -> AnalogResult:
    from farm_analog.match import palouse_demo

    if request.scenario != "ssp245":
        raise FieldNotSupported("The offline demo only covers SSP2-4.5 (moderate emissions).")
    west, south, east, north = config.PALOUSE_BOUNDS
    centroid = Polygon(*_rings(request.field)).centroid
    if not (west <= centroid.x <= east and south <= centroid.y <= north):
        raise FieldNotSupported(
            "Without Earth Engine, only fields in the Palouse demo area can be analyzed."
        )
    result, _ = palouse_demo(top_n=request.top_n)
    notes = [*result.notes, "Crop, soil and climate details need Earth Engine (live mode)."]
    return result.model_copy(update={"field_id": field_id(request.field), "notes": notes})


def _analyze_live(request: AnalogRequest) -> AnalogResult:
    from farm_analog import candidates as cand
    from farm_analog import fingerprint
    from farm_analog.farm_today import farm_today_for_field
    from farm_analog.future import farm_future_for_field
    from farm_analog.match import match, to_result

    today = farm_today_for_field(request.field)
    future = farm_future_for_field(
        request.field, fingerprint.from_contract(today.normal), scenario=request.scenario
    )
    candidates, candidate_note = cand.load_candidates()
    table = match(today, future, candidates)
    notes = [f"Candidates: {candidate_note}."]
    if today.support == "centroid_cell":
        notes.append(
            "The field is smaller than one ~4 km climate cell, so its climate is the cell "
            "under its center."
        )
    if future.failed_models:
        notes.append(
            f"{len(future.failed_models)} climate model(s) had no usable data and were "
            f"skipped: {', '.join(sorted(future.failed_models))}."
        )
    result = to_result(table, today, future, field_id(request.field), request.top_n, notes)
    try:
        from farm_analog.evidence import add_evidence

        return add_evidence(result, today.monthly, future, list(future.changes))
    except Exception as exc:  # evidence is helpful but optional; never lose the match itself
        return result.model_copy(
            update={
                "notes": [
                    *result.notes,
                    f"Crop, soil and climate details unavailable ({type(exc).__name__}).",
                ]
            }
        )
