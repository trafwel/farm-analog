import numpy as np
import pytest

from farm_analog.analogs import sigma_dissimilarity
from farm_analog.farm_today import farm_today, records_to_monthly

YEARS = (1995, 2014)


def _records(years=YEARS, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for year in range(years[0], years[1] + 1):
        for month in range(1, 13):
            out.append(
                {
                    "date": f"{year}-{month:02d}",
                    "tmean": 10 - 12 * np.cos(2 * np.pi * (month - 1) / 12) + rng.normal(0, 1.5),
                    "ppt": max(
                        0.0, 40 + 30 * np.cos(2 * np.pi * (month - 1) / 12) + rng.normal(0, 15)
                    ),
                }
            )
    return out


def test_records_become_a_complete_monthly_table():
    monthly = records_to_monthly(_records(), YEARS)
    assert len(monthly) == 240
    assert monthly.iloc[0][["year", "month"]].tolist() == [1995, 1]
    assert monthly.iloc[-1][["year", "month"]].tolist() == [2014, 12]


@pytest.mark.parametrize(
    "break_it",
    [
        lambda r: r[:-1],  # a month missing
        lambda r: r + [{"date": "2015-01", "tmean": 1.0, "ppt": 1.0}],  # outside the period
        lambda r: [{k: v for k, v in x.items() if k != "ppt"} for x in r],  # field missing
        lambda r: [],  # nothing at all
    ],
)
def test_bad_records_are_rejected(break_it):
    with pytest.raises(ValueError):
        records_to_monthly(break_it(_records()), YEARS)


def test_farm_today_shapes_and_contract():
    today = farm_today(records_to_monthly(_records(), YEARS), YEARS, support="field_mean")
    assert today.yearly_matrix.shape == (20, 8)
    assert today.years == YEARS and today.support == "field_mean"
    assert today.normal.tmean_jas > today.normal.tmean_jfm  # summer warmer than winter


def test_farm_today_plugs_into_sigma_dissimilarity():
    # The farm's own normal climate should be the closest possible match to itself.
    today = farm_today(records_to_monthly(_records(), YEARS), YEARS, support="field_mean")
    normal = today.yearly_matrix.mean(axis=0)
    candidates = np.vstack([normal, normal + today.yearly_matrix.std(axis=0)])
    sigma = sigma_dissimilarity(normal, today.yearly_matrix, candidates)
    assert sigma[0] == pytest.approx(0, abs=1e-9)
    assert sigma[1] > sigma[0]


def test_too_few_years_for_eight_values_is_rejected():
    years = (2000, 2007)  # 8 years, 8 values: covariance can't be estimated
    with pytest.raises(ValueError):
        farm_today(records_to_monthly(_records(years), years), years, support="field_mean")
