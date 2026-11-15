from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from farm_analog import config
from farm_analog.future import (
    QuarterlyChange,
    apply_delta,
    check_climatology,
    farm_future,
    quarterly_change,
)
from farm_analog.schema import SeasonalFingerprint

SAMPLE = (
    Path(__file__).resolve().parents[1] / "data/samples/palouse_climate_ACCESS-CM2_ssp245_2050.csv"
)


def _climatology(dt=2.0, ratio=1.1):
    rows = []
    for month in range(1, 13):
        base_t, base_p = 10.0 + month, 30.0 + month
        rows.append(
            {
                "period": "baseline",
                "month": month,
                "temperature_c": base_t,
                "precipitation_mm": base_p,
            }
        )
        rows.append(
            {
                "period": "future",
                "month": month,
                "temperature_c": base_t + dt,
                "precipitation_mm": base_p * ratio,
            }
        )
    return pd.DataFrame(rows)


def test_uniform_change_is_recovered():
    change = quarterly_change(_climatology(dt=2.0, ratio=1.1), "toy")
    np.testing.assert_allclose(change.temperature_delta_c, [2.0] * 4)
    np.testing.assert_allclose(change.precipitation_ratio, [1.1] * 4)


def test_real_access_cm2_sample_matches_hand_calculation():
    model = pd.read_csv(SAMPLE)
    change = quarterly_change(model, "ACCESS-CM2")
    summer = model[model.month.between(7, 9)]
    base, fut = summer[summer.period == "baseline"], summer[summer.period == "future"]
    assert change.temperature_delta_c[2] == pytest.approx(
        fut.temperature_c.mean() - base.temperature_c.mean()
    )
    assert change.precipitation_ratio[2] == pytest.approx(
        fut.precipitation_mm.sum() / base.precipitation_mm.sum()
    )
    # ACCESS-CM2 runs warm: about +4 °C in Jul-Sep, and a drier summer.
    assert 3.5 < change.temperature_delta_c[2] < 4.5
    assert change.precipitation_ratio[2] < 1


def test_apply_delta_adds_temperature_and_multiplies_rain():
    normal = np.array([2.0, 100.0, 12.0, 80.0, 20.0, 30.0, 5.0, 150.0])
    change = QuarterlyChange("toy", np.array([1.0, 2.0, 3.0, 4.0]), np.array([1.5, 1.0, 0.5, 2.0]))
    np.testing.assert_allclose(
        apply_delta(normal, change), [3.0, 150.0, 14.0, 80.0, 23.0, 15.0, 9.0, 300.0]
    )
    np.testing.assert_allclose(normal[0], 2.0)  # input not modified


def test_apply_delta_needs_eight_values():
    with pytest.raises(ValueError):
        apply_delta([1.0, 2.0], QuarterlyChange("toy", np.zeros(4), np.ones(4)))


@pytest.mark.parametrize(
    "break_it",
    [
        lambda c: c[c.month != 5],  # a month missing
        lambda c: pd.concat([c, c.iloc[[0]]]),  # a duplicate month
        lambda c: c.assign(temperature_c=c.temperature_c.where(c.month != 3)),  # a missing value
        lambda c: c.drop(columns="precipitation_mm"),  # a missing column
    ],
)
def test_bad_climatology_is_rejected(break_it):
    with pytest.raises(ValueError):
        check_climatology(break_it(_climatology()))


def test_zero_baseline_rain_is_rejected():
    clim = _climatology()
    clim.loc[(clim.period == "baseline") & clim.month.between(7, 9), "precipitation_mm"] = 0.0
    with pytest.raises(ValueError):
        quarterly_change(clim, "dry")


def test_ensemble_median_and_spread():
    normal = np.zeros(8) + 10.0
    changes = [
        QuarterlyChange(f"m{i}", np.full(4, float(dt)), np.full(4, r))
        for i, (dt, r) in enumerate([(1, 0.9), (2, 1.0), (5, 1.2)])
    ]
    future = farm_future(normal, changes)
    assert future.models == ["m0", "m1", "m2"]
    np.testing.assert_allclose(future.median[0], 12.0)  # middle model, not the mean (12.67)
    np.testing.assert_allclose(future.low[0], 11.0)
    np.testing.assert_allclose(future.high[0], 15.0)
    np.testing.assert_allclose(future.median[1], 10.0)
    assert isinstance(future.headline, SeasonalFingerprint)
    assert future.headline.tmean_jfm == pytest.approx(12.0)
    assert future.scenario == config.DEFAULT_SCENARIO
    assert future.future_years == config.FUTURE_YEARS


def test_ensemble_needs_unique_models():
    change = QuarterlyChange("same", np.zeros(4), np.ones(4))
    with pytest.raises(ValueError):
        farm_future(np.zeros(8), [change, change])
    with pytest.raises(ValueError):
        farm_future(np.zeros(8), [])


def test_model_list_spans_several_models():
    assert len(config.CLIMATE_MODELS) >= 6
    assert len(set(config.CLIMATE_MODELS)) == len(config.CLIMATE_MODELS)
