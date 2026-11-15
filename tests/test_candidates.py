import json

import numpy as np
import pandas as pd
import pytest

from farm_analog import candidates, config, fingerprint


def _frame(n=3, fraction=0.5):
    rows = []
    for i in range(n):
        lon, lat = -118.0 + i * 0.05, 46.0 + i * 0.05
        rows.append(
            {
                "cell_id": candidates.cell_id(lon, lat),
                "lon": lon,
                "lat": lat,
                **{f: 10.0 + i for f in fingerprint.FEATURES},
                "cultivated_fraction": fraction,
            }
        )
    return pd.DataFrame(rows)


def test_team_cache_becomes_candidates():
    frame = candidates.from_team_cache(json.loads(candidates.TEAM_CACHE.read_text()))
    assert len(frame) == 784
    assert list(frame.columns) == candidates.COLUMNS
    assert frame["cultivated_fraction"].isna().all()  # the team's grid has no farmland info
    assert candidates.matrix(frame).shape == (784, 8)


def test_load_falls_back_to_team_cache_with_an_honest_note(tmp_path):
    frame, note = candidates.load_candidates(path=tmp_path / "missing.parquet")
    assert len(frame) == 784
    assert "not yet filtered to farmland" in note


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "candidates.parquet"
    candidates.save_candidates(_frame(), {"source": "test"}, path)
    meta = json.loads(path.with_suffix(".json").read_text())
    assert meta["rows"] == 3 and meta["source"] == "test"
    frame, note = candidates.load_candidates(path=path)
    pd.testing.assert_frame_equal(frame, candidates.validate_candidates(_frame()))
    assert "farmland cells" in note


def test_farmland_filter_keeps_unknown_and_drops_low():
    frame = _frame(3)
    frame.loc[0, "cultivated_fraction"] = 0.1  # mostly not farmland: dropped
    frame.loc[1, "cultivated_fraction"] = np.nan  # unknown: kept
    kept = candidates.keep_farmland(frame, min_fraction=0.3)
    assert list(kept["cell_id"]) == list(frame["cell_id"][1:])


@pytest.mark.parametrize(
    "break_it",
    [
        lambda f: f.drop(columns="temperature_0"),
        lambda f: pd.concat([f, f.iloc[[0]]]),
        lambda f: f.assign(precipitation_0=-1.0),
        lambda f: f.assign(cultivated_fraction=1.5),
        lambda f: f.assign(lat=f.lat.where(f.index != 0)),
        lambda f: f.iloc[0:0],
    ],
)
def test_bad_candidates_are_rejected(break_it):
    with pytest.raises(ValueError):
        candidates.validate_candidates(break_it(_frame()))


def test_tiles_cover_the_search_area_without_gaps():
    tiles = list(candidates._tiles(config.SEARCH_BBOX))
    west, south, east, north = config.SEARCH_BBOX
    area = sum((e - w) * (n - s) for w, s, e, n in tiles)
    assert area == pytest.approx((east - west) * (north - south))
    assert min(t[0] for t in tiles) == west and max(t[2] for t in tiles) == east


def test_cell_id_is_stable():
    assert candidates.cell_id(-117.12345, 46.98765) == "46.9877_-117.1235"
