from farm_analog.fixtures import FIXTURE_PATH, load_fake_results, make_fake_results, to_json


def test_committed_fixture_matches_the_contract():
    results = load_fake_results()
    assert {r.field_id for r in results} == {"fake-colfax", "fake-lind"}
    assert all(r.source == "fixture" for r in results)
    novel = {r.field_id: r.novel_climate for r in results}
    assert novel == {"fake-colfax": False, "fake-lind": True}


def test_committed_fixture_is_up_to_date():
    # If this fails, run: python scripts/make_fake_results.py
    assert FIXTURE_PATH.read_text() == to_json(make_fake_results())
