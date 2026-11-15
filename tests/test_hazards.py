import sys
import types

import numpy as np
import pandas as pd
import pytest

from farm_analog import hazards
from farm_analog.hazards import HazardProfile


def daily(years, value=0.0):
    index = pd.date_range(f"{years[0]}-01-01", f"{years[1]}-12-31", freq="D")
    return pd.Series(value, index=index, dtype=float)


def test_heat_days_counts_days_above_threshold_per_year():
    s = daily((2001, 2002), 20.0)
    s["2001-07-01":"2001-07-10"] = 35.0  # 10 hot days
    s["2002-07-01":"2002-07-20"] = 33.0  # 20 hot days
    s["2002-08-01"] = 32.0  # exactly at the threshold is not "above"
    assert hazards.heat_days(s) == 15.0
    assert hazards.heat_days(s, threshold_c=34.0) == 5.0


def test_heat_days_needs_a_datetime_index_and_data():
    with pytest.raises(ValueError):
        hazards.heat_days(pd.Series([40.0, 41.0]))
    assert hazards.heat_days(daily((2001, 2001), np.nan)) is None


def test_frost_dates_average_last_spring_and_first_fall_frost():
    s = daily((2001, 2002), 10.0)
    s["2001-04-10"] = -2.0  # doy 100
    s["2001-03-01"] = -5.0  # earlier frost, not the last one
    s["2001-10-08"] = 0.0  # doy 281; 0 C counts as frost
    s["2001-11-20"] = -8.0  # later frost, not the first one
    s["2002-04-20"] = -1.0  # doy 110
    s["2002-10-18"] = -1.0  # doy 291
    f = hazards.frost_dates(s)
    assert f.last_spring_doy == 105.0
    assert f.first_fall_doy == 286.0
    assert f.frost_free_days == 181.0


def test_frost_dates_skip_years_without_a_frost():
    s = daily((2001, 2002), 10.0)
    s["2001-04-10"] = -2.0  # doy 100, and no fall frost in 2001
    s["2002-04-20"] = -1.0  # doy 110
    s["2002-10-18"] = -1.0  # doy 291
    f = hazards.frost_dates(s)
    assert f.last_spring_doy == 105.0
    assert f.first_fall_doy == 291.0
    assert f.frost_free_days == 181.0  # only 2002 has both
    none = hazards.frost_dates(daily((2001, 2001), 5.0))
    assert none == hazards.FrostDates(None, None, None)


def test_extreme_rain_days_and_wettest_day():
    s = daily((2001, 2002), 1.0)
    s["2001-05-01"] = 25.0  # at the threshold counts
    s["2001-05-02"] = 40.0
    s["2002-06-01"] = 30.0
    days, wettest = hazards.extreme_rain_days(s)
    assert days == 1.5
    assert wettest == 35.0
    assert hazards.extreme_rain_days(s, threshold_mm=35.0)[0] == 0.5


def test_monthly_soil_moisture_gives_12_means_with_gaps_as_none():
    index = pd.date_range("2016-01-01", "2017-12-31", freq="D")
    s = pd.Series(index.month / 100.0, index=index)
    s[s.index.month == 2] = np.nan
    values = hazards.monthly_soil_moisture(s)
    assert len(values) == 12
    assert values[0] == pytest.approx(0.01)
    assert values[1] is None
    assert values[11] == pytest.approx(0.12)


def test_bare_months_uses_the_median_per_month():
    # Green spring, bare after harvest (Aug-Oct); one cloudy outlier in May doesn't count.
    values = {
        "2020-05-03": 0.7, "2020-05-19": 0.1, "2021-05-10": 0.8,
        "2020-08-05": 0.15, "2021-08-12": 0.2,
        "2020-09-06": 0.18, "2020-10-08": 0.22, "2021-10-15": 0.3, "2022-10-02": 0.2,
    }  # fmt: skip
    s = pd.Series(list(values.values()), index=pd.to_datetime(list(values)))
    assert hazards.bare_months(s) == [8, 9, 10]
    assert hazards.bare_months(s, threshold=0.18) == [8]
    # Indexed by month number works too.
    assert hazards.bare_months(pd.Series([0.6, 0.1], index=[6, 9])) == [9]


def test_compare_reports_farm_analog_and_change():
    farm = HazardProfile(
        heat_days=8.2,
        last_spring_frost_doy=130.0,
        max_1day_rain_mm=20.04,
        soil_moisture_monthly=[0.3] * 12,
        bare_months=[8, 9],
    )
    analog = HazardProfile(
        heat_days=21.0,
        last_spring_frost_doy=110.4,
        frost_free_days=180.0,  # farm has none: left out
        max_1day_rain_mm=24.0,
        soil_moisture_monthly=[0.25] * 11 + [None],
        bare_months=[7, 8, 9, 10],
    )
    out = hazards.compare(farm, analog)
    assert out["heat_days"] == {"farm": 8.0, "analog": 21.0, "change": 13.0}
    assert out["last_spring_frost_doy"]["change"] == -20.0
    assert out["max_1day_rain_mm"] == {"farm": 20.0, "analog": 24.0, "change": 4.0}
    assert "frost_free_days" not in out
    assert out["soil_moisture_monthly"]["change"][:2] == [-0.05, -0.05]
    assert out["soil_moisture_monthly"]["change"][11] is None
    assert out["bare_months"] == {
        "farm": [8, 9],
        "analog": [7, 8, 9, 10],
        "added": [7, 10],
        "removed": [],
    }
    assert hazards.compare(HazardProfile(), analog) == {}


def test_merge_fills_fields_and_combines_missing():
    base = HazardProfile(heat_days=5.0, missing=["a: x"])
    merged = hazards.merge(base, HazardProfile(extreme_rain_days=1.0, missing=["b: y"]))
    assert merged.heat_days == 5.0
    assert merged.extreme_rain_days == 1.0
    assert merged.missing == ["a: x", "b: y"]


@pytest.fixture
def fake_ee(monkeypatch):
    """A stand-in for farm_analog.earthengine.initialize, so no network is used."""
    fake = types.SimpleNamespace(data=types.SimpleNamespace(setDeadline=lambda ms: None))
    module = types.ModuleType("farm_analog.earthengine")
    module.initialize = lambda: fake
    monkeypatch.setitem(sys.modules, "farm_analog.earthengine", module)
    return fake


POINTS = [("farm", -117.36, 46.88), (2, -118.28, 46.25)]


def test_fetch_hazards_keeps_going_when_one_source_fails(fake_ee):
    def heat(ee, points):
        assert ee is fake_ee
        return {"farm": HazardProfile(heat_days=8.0), "2": HazardProfile(heat_days=21.0)}

    def broken(ee, points):
        raise TimeoutError("deadline exceeded")

    timings = {}
    out = hazards.fetch_hazards(POINTS, sources={"heat": heat, "rain": broken}, timings=timings)
    assert set(out) == {"farm", "2"}
    assert out["farm"].heat_days == 8.0
    assert out["2"].heat_days == 21.0
    assert out["2"].extreme_rain_days is None
    assert out["2"].missing == ["rain: TimeoutError: deadline exceeded"]
    assert set(timings) == {"heat", "rain"}


def test_fetch_hazards_without_earth_engine_returns_empty_profiles(monkeypatch):
    module = types.ModuleType("farm_analog.earthengine")

    def initialize():
        raise RuntimeError("not logged in")

    module.initialize = initialize
    monkeypatch.setitem(sys.modules, "farm_analog.earthengine", module)
    out = hazards.fetch_hazards(POINTS, sources={"heat": lambda ee, p: {}})
    assert out["farm"] == HazardProfile(missing=["earthengine: RuntimeError: not logged in"])
    assert hazards.fetch_hazards([]) == {}


def test_to_contract_keeps_numbers_and_only_source_names():
    profile = hazards.HazardProfile(heat_days=12.5, bare_months=[8, 9, 10],
                                    soil_moisture_monthly=[0.3] * 12,
                                    missing=["imerg: EEException: User memory limit exceeded"])
    c = hazards.to_contract(profile)
    assert c.heat_days == 12.5 and c.bare_months == [8, 9, 10]
    assert c.missing_sources == ["imerg"]


def test_add_hazards_attaches_farm_and_top_analogs(monkeypatch):
    from farm_analog.match import palouse_demo
    from farm_analog.schema import AnalogResult, PolygonGeometry

    result, _ = palouse_demo(top_n=5)
    field = PolygonGeometry.model_validate({"type": "Polygon", "coordinates": [
        [[-117.36, 46.88], [-117.35, 46.88], [-117.35, 46.89], [-117.36, 46.88]]]})

    def fake(points, **_):
        out = {str(k): hazards.HazardProfile(heat_days=float(i)) for i, (k, _, _) in
               enumerate(points)}
        out["2"].missing.append("smap: timeout")
        return out

    monkeypatch.setattr(hazards, "fetch_hazards", fake)
    enriched = hazards.add_hazards(result, field)
    AnalogResult.model_validate(enriched.model_dump())
    assert enriched.farm_hazards.heat_days == 0.0
    assert enriched.analogs[0].hazards.heat_days == 1.0
    assert enriched.analogs[3].hazards is None
    assert enriched.notes[-1] == "Some hazard data unavailable: smap."


def test_add_hazards_raises_when_nothing_came_back(monkeypatch):
    from farm_analog.match import palouse_demo
    from farm_analog.schema import PolygonGeometry

    result, _ = palouse_demo(top_n=3)
    field = PolygonGeometry.model_validate({"type": "Polygon", "coordinates": [
        [[-117.36, 46.88], [-117.35, 46.88], [-117.35, 46.89], [-117.36, 46.88]]]})
    monkeypatch.setattr(hazards, "fetch_hazards", lambda points, **_: {
        str(k): hazards.HazardProfile(missing=["prism: down"]) for k, _, _ in points})
    with pytest.raises(RuntimeError):
        hazards.add_hazards(result, field)


def test_surface_temperature_splits_june_from_july_august_and_drops_repeat_passes():
    """M17: overlapping ECOSTRESS tiles repeat a pass; June and Jul-Aug are kept apart."""
    t = pd.to_datetime(["2020-06-05 20:00", "2020-06-05 20:00", "2021-06-20 21:00",
                        "2020-07-10 19:00", "2022-08-02 22:00", "2023-08-20 20:00"])
    s = pd.Series([36.0, 99.0, 38.0, 41.0, 44.0, 47.0], index=t)
    out = hazards.surface_temperature(s)
    assert out == {"surface_temp_june_c": 37.0, "surface_temp_julaug_c": 44.0, "surface_passes": 5}
    only_june = hazards.surface_temperature(s.iloc[:3])
    assert only_june["surface_temp_julaug_c"] is None and only_june["surface_passes"] == 2
    assert hazards.surface_temperature(pd.Series(dtype=float))["surface_passes"] == 0


def test_surface_temperature_reaches_the_contract_and_compare():
    farm = hazards.HazardProfile(surface_temp_june_c=37.0, surface_temp_julaug_c=40.1,
                                 surface_passes=88)
    place = hazards.HazardProfile(surface_temp_june_c=36.9, surface_temp_julaug_c=43.7,
                                  surface_passes=87)
    c = hazards.compare(farm, place)
    assert c["surface_temp_julaug_c"] == {"farm": 40.1, "analog": 43.7, "change": 3.6}
    assert hazards.to_contract(place).surface_passes == 87
    assert "ecostress_surface_temp" in hazards.SOURCES
