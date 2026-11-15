"""Fake Gemini clients for the assistant tests. Nothing here touches the network."""

import json

from farm_analog.assistant.llm import LLMError
from farm_analog.fixtures import FIXTURE_PATH
from farm_analog.schema import AnalogResult


class FakeLLM:
    """Implements the ``LLM`` protocol: returns a canned reply and records every call."""

    def __init__(self, reply: str | dict | None = None, error: bool = False) -> None:
        self.reply = json.dumps(reply) if isinstance(reply, dict) else reply
        self.error = error
        self.calls: list[dict] = []

    def generate(self, *, system: str, prompt: str, json_schema: dict | None = None) -> str:
        self.calls.append({"system": system, "prompt": prompt, "json_schema": json_schema})
        if self.error:
            raise LLMError("Gemini call failed (FakeOutage)")
        return self.reply or ""


class FakeGenaiClient:
    """Stands in for ``genai.Client``: only ``.models.generate_content`` is used."""

    def __init__(self, text: str | None = "ok", exc: Exception | None = None) -> None:
        self.models = self
        self.text, self.exc = text, exc
        self.kwargs: dict = {}

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        if self.exc:
            raise self.exc
        return type("Response", (), {"text": self.text})()


def load_result(field_id: str) -> AnalogResult:
    for raw in json.loads(FIXTURE_PATH.read_text(encoding="utf-8")):
        if raw["field_id"] == field_id:
            return AnalogResult.model_validate(raw)
    raise KeyError(field_id)
