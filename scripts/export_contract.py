"""Regenerate the JSON Schema files in contract/. Run: python scripts/export_contract.py"""

from farm_analog.contract import write_schemas

if __name__ == "__main__":
    for path in write_schemas():
        print(f"wrote {path}")
