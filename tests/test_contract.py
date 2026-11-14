from farm_analog.contract import CONTRACT_DIR, render_schemas


def test_committed_json_schemas_are_up_to_date():
    # If this fails, run: python scripts/export_contract.py
    for filename, text in render_schemas().items():
        assert (CONTRACT_DIR / filename).read_text() == text, f"{filename} is out of date"
