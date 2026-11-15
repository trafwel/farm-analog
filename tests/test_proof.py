import numpy as np
import pandas as pd
import pytest

from farm_analog import candidates as cand
from farm_analog import config, fingerprint, proof


def test_palouse_self_check_finds_home_and_matches_the_committed_numbers():
    report = proof.palouse_proof()
    check = report["self_check"]
    assert check["best_is_home"] and check["best_sigma"] < config.STRONG_SIGMA
    assert check["home_share_good"] == 1.0  # every Palouse cell is a good match for itself
    assert check["home_median_sigma"] < 1 < check["elsewhere_median_sigma"]
    agree = report["rank_agreement"]
    assert agree["models_total"] == 1 and agree["top"] == 20
    # The numbers quoted in docs/REVIEWS.md (M10); update both together.
    assert (check["home_cells"], agree["top_overlap"]) == (28, 17)
    assert agree["spearman"] == pytest.approx(0.997, abs=0.001)


def test_crop_mix_and_similarity():
    mix = proof.crop_mix({24: 60, 61: 40, 141: 1000})  # forest left out
    assert mix == {24: 0.6, 61: 0.4}
    assert proof.crop_mix({141: 5}) == {}
    assert proof.similarity(mix, mix) == pytest.approx(1.0)
    assert proof.similarity(mix, {52: 1.0}) == 0.0
    assert proof.similarity(mix, {24: 0.3, 52: 0.7}) == pytest.approx(0.3)
    assert np.isnan(proof.similarity(mix, {}))
    assert proof.average_mix([{24: 1.0}, {52: 1.0}, {}]) == {24: 0.5, 52: 0.5}


def test_distance_km():
    # One degree of latitude is about 111 km.
    assert proof.distance_km(-117, 46, [-117], [47])[0] == pytest.approx(111.2, abs=0.5)


def _grid(climate_of):
    """Cells on a 0.5-degree line of longitudes, each with a climate from ``climate_of``."""
    rows = []
    for i, lon in enumerate(np.arange(-120.0, -115.0, 0.5)):
        values = climate_of(i)
        rows.append({"cell_id": f"c{i}", "lon": lon, "lat": 46.0,
                     **dict(zip(fingerprint.FEATURES, values, strict=True))})
    return pd.DataFrame(rows)


def test_backtest_analogs_beat_random_when_crops_follow_climate():
    base = np.array([0, 10, 20, 10, 100, 50, 10, 80], dtype=float)
    then = _grid(lambda i: base + [i, i, i, i, 0, 0, 0, 0])  # warmer to the east
    now = then.copy()
    now[fingerprint.FEATURES[:4]] += 3.0  # every cell warmed by 3 cells' worth
    test = now[now["cell_id"].isin(["c0", "c1", "c2"])]
    rng = np.random.default_rng(1)
    yearly = {c: base + rng.normal(0, 1, (20, 8)) for c in test["cell_id"]}

    picks = proof.pick_cells(test, then, yearly, k=1, exclude_km=10)
    # c0 now is as warm as c3 was then.
    assert picks["c0"].analogs == ("c3",) and picks["c1"].analogs == ("c4",)

    # Crops follow temperature: cell i grew crop code 1 + i then; now the test cells grow
    # the crop of the place three cells east.
    crops_then = {f"c{i}": {1 + i: 1.0} for i in range(10)}
    crops_now = {f"c{i}": crops_then[f"c{i + 3}"] for i in range(3)}
    result = proof.score_backtest(picks, crops_then, crops_now)
    assert result.test_cells == 3
    assert result.analog_similarity == 1.0
    assert result.persistence_similarity == 0.0  # the crops changed
    assert result.analog_beats_random >= 2 / 3


def test_pick_cells_never_picks_neighbors_or_itself():
    then = _grid(lambda i: np.array([0, 10, 20, 10, 100, 50, 10, 80], dtype=float))
    test = then[then["cell_id"] == "c4"]
    yearly = {"c4": then[fingerprint.FEATURES].to_numpy()[4]
              + np.random.default_rng(0).normal(0, 1, (20, 8))}
    picks = proof.pick_cells(test, then, yearly, k=3, exclude_km=60)  # 0.5 deg ~ 39 km
    chosen = set(picks["c4"].analogs) | set(picks["c4"].random)
    assert not chosen & {"c3", "c4", "c5"}


def test_score_backtest_needs_crop_data():
    picks = {"a": proof.Picks(analogs=("b",), random=("c",), best_sigma=0.5)}
    with pytest.raises(ValueError):
        proof.score_backtest(picks, {}, {})


def test_near_latitude():
    frame = pd.DataFrame({"cell_id": ["a", "b", "c"], "lon": [-117] * 3, "lat": [40, 46, 52]})
    assert list(cand.near_latitude(frame, 46.5, 5)["cell_id"]) == ["b"]
