import numpy as np
import pandas as pd
import pytest

from farm_analog import fingerprint
from farm_analog.schema import SeasonalFingerprint


def _monthly(years=(2000, 2001)):
    rows = []
    for year in range(years[0], years[1] + 1):
        for month in range(1, 13):
            rows.append(
                {
                    "year": year,
                    "month": month,
                    "tmean": float(month) + (year - years[0]),
                    "ppt": 10.0 * month,
                }
            )
    return pd.DataFrame(rows)


def test_quarters_cover_each_month_once():
    months = [m for first, last in fingerprint.QUARTERS.values() for m in range(first, last + 1)]
    assert sorted(months) == list(range(1, 13))


def test_feature_order_matches_the_teams_cached_search_data():
    # search.py's cache and CSV use these names in this order; changing it breaks the cache.
    assert fingerprint.FEATURES == [
        "temperature_0",
        "precipitation_0",
        "temperature_1",
        "precipitation_1",
        "temperature_2",
        "precipitation_2",
        "temperature_3",
        "precipitation_3",
    ]


def test_yearly_fingerprint_values():
    yearly = fingerprint.yearly_fingerprints(_monthly())
    first = yearly.loc[2000]
    assert first["temperature_0"] == pytest.approx(2.0)  # mean of 1, 2, 3
    assert first["precipitation_0"] == pytest.approx(60.0)  # 10 + 20 + 30
    assert first["temperature_3"] == pytest.approx(11.0)  # mean of 10, 11, 12
    assert first["precipitation_3"] == pytest.approx(330.0)  # 100 + 110 + 120
    assert yearly.loc[2001, "temperature_0"] == pytest.approx(3.0)


def test_normal_is_the_average_year():
    yearly = fingerprint.yearly_fingerprints(_monthly())
    np.testing.assert_allclose(fingerprint.normal(yearly), yearly.mean().to_numpy())


@pytest.mark.parametrize(
    "break_it",
    [
        lambda m: m[~((m.year == 2000) & (m.month == 5))],  # a missing month
        lambda m: pd.concat([m, m.iloc[[0]]]),  # a duplicate month
        lambda m: m.assign(tmean=m.tmean.where(m.month != 7)),  # a missing value
        lambda m: m.drop(columns="ppt"),  # a missing column
    ],
)
def test_incomplete_monthly_data_is_rejected(break_it):
    with pytest.raises(ValueError):
        fingerprint.yearly_fingerprints(break_it(_monthly()))


def test_contract_round_trip():
    vector = np.arange(8, dtype=float) + 1
    fp = fingerprint.to_contract(vector)
    assert isinstance(fp, SeasonalFingerprint)
    assert fp.tmean_jfm == 1.0 and fp.ppt_jfm == 2.0 and fp.ppt_ond == 8.0
    np.testing.assert_array_equal(fingerprint.from_contract(fp), vector)


def test_contract_needs_eight_values():
    with pytest.raises(ValueError):
        fingerprint.to_contract([1.0, 2.0])
