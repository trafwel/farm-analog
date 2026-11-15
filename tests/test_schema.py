import math

import pytest
from pydantic import ValidationError

from farm_analog import config
from farm_analog.fixtures import load_fake_results
from farm_analog.schema import (
    AnalogRequest,
    AnalogResult,
    PolygonGeometry,
    match_quality,
    match_score,
)

SQUARE = [[-117.2, 46.8], [-117.19, 46.8], [-117.19, 46.81], [-117.2, 46.81], [-117.2, 46.8]]


@pytest.mark.parametrize(
    ("sigma", "label"),
    [
        (0.0, "strong"),
        (0.99, "strong"),
        (1.0, "good"),
        (1.99, "good"),
        (2.0, "weak"),
        (3.99, "weak"),
        (4.0, "none"),
        (12.0, "none"),
    ],
)
def test_match_quality_thresholds(sigma, label):
    assert match_quality(sigma) == label


def test_valid_polygon_and_request_defaults():
    req = AnalogRequest(field={"type": "Polygon", "coordinates": [SQUARE]})
    assert req.scenario == config.DEFAULT_SCENARIO
    assert req.top_n == config.DEFAULT_TOP_N


@pytest.mark.parametrize(
    "ring",
    [
        SQUARE[:-1],  # not closed
        [[-117.2, 46.8], [-117.19, 46.8], [-117.2, 46.8]],  # too few positions
        [[-200, 46.8], [-117.19, 46.8], [-117.19, 46.81], [-200, 46.8]],  # longitude out of range
        [[math.nan, 46.8], [-117.19, 46.8], [-117.19, 46.81], [math.nan, 46.8]],  # not a number
    ],
)
def test_bad_polygons_are_rejected(ring):
    with pytest.raises(ValidationError):
        PolygonGeometry(type="Polygon", coordinates=[ring])


def test_too_many_vertices_rejected():
    n = config.MAX_POLYGON_VERTICES + 1
    ring = [[-117 + i * 1e-5, 46.8 + (i % 2) * 1e-5] for i in range(n - 1)] + [[-117, 46.8]]
    with pytest.raises(ValidationError):
        PolygonGeometry(type="Polygon", coordinates=[ring])


def test_unknown_fields_and_bad_top_n_rejected():
    with pytest.raises(ValidationError):
        AnalogRequest(field={"type": "Polygon", "coordinates": [SQUARE]}, colour="green")
    with pytest.raises(ValidationError):
        AnalogRequest(field={"type": "Polygon", "coordinates": [SQUARE]}, top_n=0)


def _result_dict():
    return load_fake_results()[0].model_dump(mode="json")


def test_mismatched_match_quality_rejected():
    data = _result_dict()
    data["analogs"][0]["match_quality"] = "none"
    with pytest.raises(ValidationError):
        AnalogResult.model_validate(data)


def test_unsorted_analogs_rejected():
    data = _result_dict()
    data["analogs"][0], data["analogs"][1] = data["analogs"][1], data["analogs"][0]
    with pytest.raises(ValidationError):
        AnalogResult.model_validate(data)


def test_novel_flag_must_match_best_sigma():
    data = _result_dict()
    data["novel_climate"] = True
    with pytest.raises(ValidationError):
        AnalogResult.model_validate(data)


def test_climograph_needs_twelve_months():
    data = _result_dict()
    data["analogs"][0]["climograph"]["farm_today"]["ppt"] = [1.0] * 11
    with pytest.raises(ValidationError):
        AnalogResult.model_validate(data)


# Same table as frontend/src/lib/matchQuality.test.ts: the two score functions must agree.
@pytest.mark.parametrize(("sigma", "score"), [
    (0.0, 100), (0.2, 97), (0.3, 95), (0.999, 85), (1.0, 84), (1.5, 77), (2.0, 69),
    (3.0, 60), (3.99, 50), (4.0, 49), (6.0, 25), (8.0, 0), (12.0, 0),
])
def test_match_score_table(sigma, score):
    assert match_score(sigma) == score


def test_match_score_band_always_agrees_with_match_quality():
    bands = {"strong": (85, 100), "good": (70, 84), "weak": (50, 69), "none": (0, 49)}
    for i in range(0, 1001):
        sigma = i / 100
        low, high = bands[match_quality(sigma)]
        assert low <= match_score(sigma) <= high, sigma
    assert match_score(math.inf) == 0
