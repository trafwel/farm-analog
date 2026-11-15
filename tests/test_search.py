import json
from pathlib import Path

import pandas as pd

from farm_analog import search

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


def test_search_reproduces_the_committed_rankings_from_cache(tmp_path):
    # Runs entirely from the committed cache (no Earth Engine) into a temp folder, then checks
    # the rankings match what the team committed: refactors must not change results.
    search.run(data_dir=SAMPLES, output_dir=tmp_path)
    new = pd.read_csv(tmp_path / "palouse_analog_candidates.csv")
    old = pd.read_csv(SAMPLES / "palouse_analog_candidates.csv")
    pd.testing.assert_frame_equal(new, old, check_exact=False, rtol=1e-12)

    new_summary = json.loads((tmp_path / "palouse_analog_summary.json").read_text(encoding="utf-8"))
    old_summary = json.loads((SAMPLES / "palouse_analog_summary.json").read_text(encoding="utf-8"))
    for key in old_summary:
        if key != "created_utc":
            assert new_summary[key] == old_summary[key], key
