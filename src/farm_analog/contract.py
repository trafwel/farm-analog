"""Export the JSON contract as JSON Schema files for the frontend.

The Pydantic models in ``farm_analog.schema`` are the single source of truth. This module
writes them out as JSON Schema in ``contract/``; the React app generates its TypeScript
types from those files (M6), so a field renamed in Python shows up as a type error in the
frontend instead of a silent bug. A test fails if the committed files fall out of date.
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
        path.write_text(text)
        paths.append(path)
    return paths
