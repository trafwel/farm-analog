import numpy as np
import pandas as pd
import pytest

from farm_analog import candidates as cand
from farm_analog import config, fingerprint
from farm_analog.farm_today import FarmToday
from farm_analog.future import QuarterlyChange, farm_future
from farm_analog.match import SAMPLES, match, palouse_demo, to_result
from farm_analog.schema import AnalogResult


def _today(seed=0):
    rng = np.random.default_rng(seed)
    base = np.array([2.0, 150.0, 12.0, 110.0, 19.0, 36.0, 4.0, 156.0])
    yearly = pd.DataFrame(
        base + rng.normal(0, 1, size=(20, 8)) * np.array([1, 20, 1, 15, 1, 8, 1, 20]),
        columns=fingerprint.FEATURES,
        index=range(1995, 2015),
    )
    return FarmToday(
        normal=fingerprint.to_contract(fingerprint.normal(yearly)),
        yearly=yearly,
        years=(1995, 2014),
        support="field_mean",
    )


def _candidates(rows):
    frame = pd.DataFrame(rows, columns=fingerprint.FEATURES)
    frame.insert(0, "lat", 46.0 + np.arange(len(frame)) * 0.1)
    frame.insert(0, "lon", -118.0 + np.arange(len(frame)) * 0.1)
    frame.insert(
        0, "cell_id", [cand.cell_id(x, y) for x, y in zip(frame.lon, frame.lat, strict=True)]
    )
    frame["cultivated_fraction"] = 0.8
    return cand.validate_candidates(frame)


def _future(today, deltas=((2.0, 1.0), (3.0, 0.9))):
    changes = [
        QuarterlyChange(f"m{i}", np.full(4, dt), np.full(4, r)) for i, (dt, r) in enumerate(deltas)
    ]
    return farm_future(fingerprint.from_contract(today.normal), changes)


def test_place_matching_a_models_future_scores_zero_for_that_model():
    today = _today()
    future = _future(today)
    far = future.per_model["m0"] + 40
    table = match(today, future, _candidates([future.per_model["m0"], far]))
    best = table.iloc[0]
    assert best["sigma_m0"] == pytest.approx(0, abs=1e-9)
    assert best["rank"] == 1 and table.iloc[1]["sigma"] > best["sigma"]
    assert {"sigma_m0", "sigma_m1", "models_agree", "standardized_euclidean"} <= set(table.columns)


def test_median_and_agreement_across_models():
    today = _today()
    future = _future(today, deltas=((2.0, 1.0), (2.0, 1.0), (8.0, 0.5)))
    table = match(today, future, _candidates([future.per_model["m0"]]))
    row = table.iloc[0]
    assert row["sigma"] == pytest.approx(
        np.median([row["sigma_m0"], row["sigma_m1"], row["sigma_m2"]])
    )
    assert row["models_agree"] == 2  # the two models whose future it matches; not the outlier
    assert row["models_total"] == 3


def test_result_follows_the_contract_and_flags_novel_climates():
    today = _today()
    future = _future(today)
    near = _candidates([future.median, future.median + 1])
    result = to_result(match(today, future, near), today, future, "field-1", top_n=1, notes=["n"])
    assert isinstance(result, AnalogResult)
    assert result.source == "computed" and len(result.analogs) == 1
    assert result.novel_climate is False and result.notes == ["n"]
    assert result.models == ["m0", "m1"] and result.analogs[0].models_total == 2

    far = _candidates([future.median + 60, future.median + 80])
    novel = to_result(match(today, future, far), today, future, "field-1")
    assert novel.novel_climate is True
    assert all(a.match_quality == "none" for a in novel.analogs)


def test_palouse_demo_reproduces_the_teams_rankings():
    # One model on the team's own data must give exactly the team's committed sigma ranking.
    result, table = palouse_demo(top_n=20)
    committed = pd.read_csv(SAMPLES / "palouse_analog_candidates.csv")
    np.testing.assert_allclose(table["sigma"].to_numpy(), committed["sigma"].to_numpy(), rtol=1e-12)
    np.testing.assert_allclose(table["lon"].to_numpy(), committed["longitude"].to_numpy())
    np.testing.assert_allclose(
        table["standardized_euclidean"].to_numpy(),
        committed["standardized_euclidean"].to_numpy(),
        rtol=1e-12,
    )
    assert result.analogs[0].lat == pytest.approx(committed["latitude"][0])
    assert result.models == ["ACCESS-CM2"] and len(result.notes) == 3
    assert result.baseline_years == config.BASELINE_YEARS


def test_demo_result_round_trips_through_json():
    result, _ = palouse_demo(top_n=5)
    again = AnalogResult.model_validate_json(result.model_dump_json())
    assert again == result
