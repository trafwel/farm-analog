"""Export the JSON contract as JSON Schema files for the frontend.

The Pydantic models in ``farm_analog.schema`` are the single source of truth. This module
writes them out as JSON Schema in ``contract/``; the React app generates its TypeScript
types from those files (M6), so a field renamed in Python shows up as a type error in the
frontend instead of a silent bug. A test fails if the committed files fall out of date.

Data flow:
Inputs:  the Pydantic models ``AnalogRequest`` and ``AnalogResult`` from schema.py.
Outputs: contract/analog_request.schema.json and contract/analog_result.schema.json.
Used by: scripts/export_contract.py (writes the files); tests/test_contract.py (fails if
         the committed files are stale); frontend/scripts/gen-types.mjs (reads contract/ to
         generate frontend/src/types/contract.ts; CI checks that file is up to date).
"""

import json
from pathlib import Path

from farm_analog.schema import AnalogRequest, AnalogResult

CONTRACT_DIR = Path(__file__).resolve().parents[2] / "contract"
MODELS = {"analog_request": AnalogRequest, "analog_result": AnalogResult}


def render_schemas() -> dict[str, str]:
    """File name -> JSON Schema text for every contract model."""
    schemas = {}
    for name, model in MODELS.items():
        text = json.dumps(model.model_json_schema(), indent=2, sort_keys=True)
        schemas[f"{name}.schema.json"] = text + "\n"
    return schemas


def write_schemas(directory: Path = CONTRACT_DIR) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename, text in render_schemas().items():
        path = directory / filename
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths
