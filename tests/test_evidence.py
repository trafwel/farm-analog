import numpy as np
import pandas as pd
import pytest

from farm_analog import evidence
from farm_analog.future import QuarterlyChange
from farm_analog.match import palouse_demo
from farm_analog.schema import AnalogResult

NAMES = {
    24: "Winter Wheat",
    61: "Fallow/Idle Cropland",
    52: "Lentils",
    53: "Peas",
    51: "Chick Peas",
    23: "Spring Wheat",
    141: "Deciduous Forest",
    121: "Developed/Open Space",
}


def test_crop_shares_leave_out_non_farm_land_and_group_small_crops():
    counts = {24: 500, 61: 200, 52: 100, 53: 80, 51: 60, 23: 40, 141: 9999, 121: 5000}
    shares = evidence.crop_shares(counts, NAMES, top=5)
    assert [s.crop for s in shares] == [
        "Winter Wheat",
        "Fallow/Idle Cropland",
        "Lentils",
        "Peas",
        "Chick Peas",
        "Other crops",
    ]
    assert shares[0].share == pytest.approx(500 / 980, abs=1e-3)  # forest and towns excluded
    assert sum(s.share for s in shares) == pytest.approx(1.0, abs=0.005)


def test_crop_shares_edge_cases():
    assert evidence.crop_shares({141: 100}, NAMES) == []  # no cropland at all
    assert evidence.crop_shares({999: 0}, NAMES) == []
    unnamed = evidence.crop_shares({205: 10}, {})  # a double-crop code with no name
    assert unnamed[0].crop == "CDL class 205" and unnamed[0].share == 1.0


def test_soil_profile_converts_openlandmap_units():
    soil = evidence.soil_profile(clay_pct=22, sand_pct=15, olm_organic_carbon=4)
    # 4 x 5 g/kg = 20 g/kg = 2.0 % organic carbon -> x 1.724 = 3.4 % organic matter
    assert soil.clay_pct == 22 and soil.sand_pct == 15
    assert soil.organic_matter_pct == pytest.approx(3.4, abs=0.05)


def test_soil_profile_drops_impossible_or_missing_values():
    soil = evidence.soil_profile(clay_pct=250, sand_pct=None, olm_organic_carbon=float("nan"))
    assert soil.clay_pct is None and soil.sand_pct is None and soil.organic_matter_pct is None


def _monthly():
    rows = [
        {"year": y, "month": m, "tmean": float(m), "ppt": 10.0 * m}
        for y in (2000, 2001)
        for m in range(1, 13)
    ]
    return pd.DataFrame(rows)


def test_monthly_normals_and_future_months():
    normals = evidence.monthly_normals(_monthly())
    assert list(normals.index) == list(range(1, 13))
    assert normals.loc[7, "tmean"] == 7.0 and normals.loc[7, "ppt"] == 70.0
    changes = [
        QuarterlyChange("a", np.array([1.0, 1.0, 2.0, 1.0]), np.array([1.0, 1.0, 0.5, 1.0])),
        QuarterlyChange("b", np.array([1.0, 1.0, 4.0, 1.0]), np.array([1.0, 1.0, 0.7, 1.0])),
        QuarterlyChange("c", np.array([1.0, 1.0, 9.0, 1.0]), np.array([1.0, 1.0, 0.9, 1.0])),
    ]
    future = evidence.future_monthly(normals, changes)
    assert future.loc[7, "tmean"] == pytest.approx(7.0 + 4.0)  # median model, Jul-Sep quarter
    assert future.loc[7, "ppt"] == pytest.approx(70.0 * 0.7)
    assert future.loc[1, "tmean"] == pytest.approx(2.0)


def test_monthly_normals_need_every_month():
    with pytest.raises(ValueError):
        evidence.monthly_normals(_monthly()[lambda m: m.month != 2])


def test_attach_adds_evidence_and_keeps_the_contract_valid():
    result, _ = palouse_demo(top_n=5)
    normals = evidence.monthly_normals(_monthly())
    found = evidence.AnalogEvidence(
        place_name="Walla Walla County, WA",
        crops=evidence.crop_shares({24: 7, 61: 3}, NAMES),
        soil=evidence.soil_profile(20, 30, 3),
        monthly=normals,
    )
    enriched = evidence.attach(
        result, {1: found}, normals, normals, farm_soil=evidence.soil_profile(18, 12, 4)
    )
    first = enriched.analogs[0]
    assert first.place_name == "Walla Walla County, WA"
    assert first.crops[0].crop == "Winter Wheat" and first.climograph is not None
    assert enriched.analogs[1].crops is None  # only rank 1 had evidence
    assert enriched.farm_soil.clay_pct == 18
    AnalogResult.model_validate(enriched.model_dump())  # still satisfies every contract rule


def test_place_names():
    assert evidence.place_name("Walla Walla", "53") == "Walla Walla County, WA"
    assert evidence.place_name("Umatilla", 41) == "Umatilla County, OR"
    assert evidence.place_name(None, "53") is None
