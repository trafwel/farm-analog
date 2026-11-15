"""Regenerate fixtures/fake_results.json. Run: python scripts/make_fake_results.py"""

from farm_analog.fixtures import FIXTURE_PATH, make_fake_results, to_json

if __name__ == "__main__":
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(to_json(make_fake_results()))
    print(f"wrote {FIXTURE_PATH}")
