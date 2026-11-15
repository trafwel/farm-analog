"""Shared Earth Engine helpers for field-level extraction (used by farm_today and future).

Imported lazily by callers, so modules that don't need Earth Engine never require a login.

Data flow:
Inputs:  ``EE_PROJECT`` from the environment / .env (initialize); a schema.PolygonGeometry
         (field_geometry); an ee.Image + field area + projection + band (reduce_field).
Outputs: an initialized ``ee`` module; an ee.Geometry; one number per image (the field's
         mean, or the cell under the field's center when no cell center falls inside).
Used by: farm_today.fetch_prism_monthly, future.fetch_model_climatology, and (initialize
         only) candidates.fetch_candidates, evidence.fetch_evidence and proof.py's
         Earth Engine fetches. Always imported lazily, inside those functions.
"""

import os

from farm_analog.schema import PolygonGeometry


def initialize():
    """Log in to Earth Engine with the project from ``.env`` (``EE_PROJECT``)."""
    import ee
    from dotenv import load_dotenv

    load_dotenv()
    ee.Initialize(project=os.environ["EE_PROJECT"])
    return ee


def field_geometry(ee, field: PolygonGeometry):
    """The drawn field as an Earth Engine polygon (planar lon/lat, as drawn on the map)."""
    return ee.Geometry.Polygon(field.coordinates, proj="EPSG:4326", geodesic=False)


def reduce_field(ee, image, area, projection, band):
    """Average an image over a field, falling back to the cell under the field's center.

    Grid cells (PRISM ~4 km, climate models ~25 km) are usually bigger than a field, so no
    cell center falls inside it and the plain average comes back empty. Returns
    (values, support), where support is "field_mean" or "centroid_cell".
    """
    kwargs = {"crs": projection, "scale": projection.nominalScale(), "maxPixels": 1_000_000}
    mean = image.reduceRegion(ee.Reducer.mean(), area, **kwargs)
    cell = image.reduceRegion(ee.Reducer.first(), area.centroid(maxError=1), **kwargs)
    # IsEqual returns a server-side Boolean, which can't be negated as a Number, so branch on
    # "empty" directly instead of on "not empty".
    empty = ee.Algorithms.IsEqual(mean.get(band), None)
    values = ee.Dictionary(ee.Algorithms.If(empty, cell, mean))
    support = ee.Algorithms.If(empty, "centroid_cell", "field_mean")
    return values, support
