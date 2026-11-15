import pytest

from farm_analog import config, pipeline, saved
from farm_analog.match import palouse_demo


@pytest.fixture
def folder(tmp_path):
    """A saved Colfax result (the offline demo's numbers, relabelled) in a temp folder."""
    result, _ = palouse_demo(top_n=20)
    result = result.model_copy(update={"field_id": "test-colfax", "notes": ["live caveat"]})
    saved.path_for("colfax", "ssp245", tmp_path).write_text(result.model_dump_json())
    return tmp_path


def test_test_field_request_is_a_small_square_on_the_point():
    request = saved.test_field_request("lind", "ssp585")
    _, lat, lon = config.TEST_FIELDS["lind"]
    assert request.scenario == "ssp585"
    assert pipeline.field_area_km2(request.field) == pytest.approx(0.19, abs=0.03)
    ring = request.field.coordinates[0]
    assert ring[0][0] < lon < ring[1][0] and ring[0][1] < lat < ring[2][1]


def test_nearby_field_gets_the_saved_result_with_a_note(folder):
    near = saved.test_field_request("colfax", "ssp245").field  # same spot
    result, km = saved.nearest_saved(near, "ssp245", top_n=5, folder=folder)
    assert km < 0.1 and len(result.analogs) == 5
    assert result.notes[0].startswith("Saved live result for the Colfax test field")
    assert result.notes[1] == "live caveat"


def test_far_field_or_missing_scenario_gets_nothing(folder):
    lind = saved.test_field_request("lind", "ssp245").field  # ~100 km away
    assert saved.nearest_saved(lind, "ssp245", 5, folder=folder) is None
    colfax = saved.test_field_request("colfax", "ssp585").field
    assert saved.nearest_saved(colfax, "ssp585", 5, folder=folder) is None


def test_distance_km():
    # Colfax to the Cook Farm near Pullman is about 23 km.
    assert saved.distance_km(46.88, -117.36, 46.78, -117.09) == pytest.approx(23, abs=3)


def test_write_summaries_uses_the_number_check(tmp_path):
    """M18: summaries for the online demo; a reply with an unchecked number falls back."""
    import json as _json

    from farm_analog import saved

    src = saved.path_for("colfax", "ssp245")
    (tmp_path / src.name).write_text(src.read_text())

    class Fake:
        def generate(self, system, prompt):
            return "The best match gets 99 more hot days."  # 99 is not in the input

    report = saved.write_summaries(Fake(), folder=tmp_path)
    assert report == [{"file": "colfax_ssp245", "source": "template",
                       "error": "number not in the input: 99"}]
    out = saved.summary_path("colfax", "ssp245", tmp_path / "summaries")
    written = _json.loads(out.read_text())
    assert written["source"] == "template" and written["model"] is None
    assert "used in 0 of 5 matching areas" in written["text"]
    assert set(written) == {"text", "source", "notices", "model", "generated"}
