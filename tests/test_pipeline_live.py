"""The live pipeline's wiring (M1 -> M2 -> M3 -> M4 -> M7), with Earth Engine replaced by fakes
built from real committed data, so the orchestration is tested without network access."""

import json

import numpy as np
import pandas as pd
import pytest

from farm_analog import candidates as cand
from farm_analog import evidence, farm_today, future, pipeline
from farm_analog.match import TEAM_MODEL_CSV, palouse_today_from_cache
from farm_analog.schema import AnalogRequest

REQUEST = AnalogRequest.model_validate(
    {
        "field": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-117.36, 46.88],
                    [-117.35, 46.88],
                    [-117.35, 46.89],
                    [-117.36, 46.89],
                    [-117.36, 46.88],
                ]
            ],
        }
    }
)


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setenv("EE_PROJECT", "test-project")
    monkeypatch.delenv("FARM_ANALOG_OFFLINE", raising=False)
    today = palouse_today_from_cache(json.loads(cand.TEAM_CACHE.read_text()))
    rows = [
        {"year": y, "month": m, "tmean": 10.0 + m, "ppt": 30.0 + m}
        for y in range(1995, 2015)
        for m in range(1, 13)
    ]
    today = farm_today.FarmToday(
        today.normal, today.yearly, today.years, "centroid_cell", monthly=pd.DataFrame(rows)
    )
    climatology = pd.read_csv(TEAM_MODEL_CSV)

    monkeypatch.setattr(farm_today, "farm_today_for_field", lambda field: today)

    def fake_future(field, normal, scenario="ssp245", **_):
        changes = [future.quarterly_change(climatology, "ACCESS-CM2")]
        return future.farm_future(
            normal, changes, scenario, failed_models={"BROKEN-MODEL": "no data"}
        )

    monkeypatch.setattr(future, "farm_future_for_field", fake_future)
    return today


def test_live_pipeline_attaches_evidence(live, monkeypatch):
    normals = evidence.monthly_normals(live.monthly)
    fake = evidence.AnalogEvidence(
        "Walla Walla County, WA",
        evidence.crop_shares({24: 5, 61: 5}, {24: "Winter Wheat"}),
        evidence.soil_profile(20, 25, 3),
        normals,
    )
    monkeypatch.setattr(evidence, "fetch_evidence", lambda points: {p[0]: fake for p in points})
    result = pipeline.analyze(REQUEST)
    assert pipeline.mode() == "live" and result.source == "computed"
    top = result.analogs[0]
    assert top.place_name == "Walla Walla County, WA" and top.climograph is not None
    assert result.analogs[3].crops is None  # evidence only for the top 3
    assert any("BROKEN-MODEL" in n for n in result.notes)  # skipped model is reported
    assert any("smaller than one" in n for n in result.notes)  # centroid-cell caveat
    # Farm today/future climographs come from the farm's own months and the model change.
    assert top.climograph.farm_future.tmean[6] > top.climograph.farm_today.tmean[6]
    assert np.isfinite(top.sigma)


def test_live_pipeline_survives_evidence_failure(live, monkeypatch):
    def boom(points):
        raise TimeoutError("earth engine slow")

    monkeypatch.setattr(evidence, "fetch_evidence", boom)
    result = pipeline.analyze(REQUEST)
    assert len(result.analogs) == 20 and result.analogs[0].crops is None
    assert any("details unavailable (TimeoutError)" in n for n in result.notes)
