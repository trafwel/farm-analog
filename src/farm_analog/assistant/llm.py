"""The one place Bill talks to Gemini.

Problem: the parser and the summarizer both need "send a prompt, get text back", and the tests
must never call the network.

Approach: a tiny ``LLM`` protocol with a single ``generate`` method. ``GeminiLLM`` implements it
with Google's ``google-genai`` SDK; tests pass a fake object with the same method. Nothing else
in the package imports the SDK, so swapping models or providers touches only this file.

The API key is read on the server from ``GEMINI_API_KEY`` (``.env``) and never leaves it.
"""

import os
from typing import Any, Protocol

from farm_analog import config


class LLMError(RuntimeError):
    """Gemini could not be reached or returned nothing usable."""


class LLM(Protocol):
    def generate(self, *, system: str, prompt: str, json_schema: dict | None = None) -> str:
        """Return the model's text reply. With ``json_schema``, the reply is JSON text."""
        ...


# JSON Schema keywords Gemini's structured output accepts (from the SDK's
# ``GenerateContentConfig.response_json_schema`` docs). Pydantic also emits keywords such as
# ``maxLength`` and ``default``; we drop those and enforce them with Pydantic afterwards.
_SUPPORTED_SCHEMA_KEYS = {
    "$id", "$defs", "$ref", "$anchor", "type", "format", "title", "description", "enum",
    "items", "prefixItems", "minItems", "maxItems", "minimum", "maximum", "anyOf", "oneOf",
    "properties", "additionalProperties", "required",
}


def gemini_schema(schema: Any) -> Any:
    """Strip a Pydantic JSON Schema down to the keywords Gemini supports."""
    if isinstance(schema, list):
        return [gemini_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    out = {}
    for key, value in schema.items():
        if key not in _SUPPORTED_SCHEMA_KEYS:
            continue
        if key in ("properties", "$defs"):  # keys here are field names, not keywords
            out[key] = {name: gemini_schema(sub) for name, sub in value.items()}
        else:
            out[key] = gemini_schema(value)
    return out


class GeminiLLM:
    """``LLM`` backed by the Gemini API.

    ``client`` can be injected (tests use a fake with ``.models.generate_content``); otherwise a
    real ``genai.Client`` is built from ``GEMINI_API_KEY``.
    """

    def __init__(self, client: Any = None, model: str = config.GEMINI_MODEL) -> None:
        self.model = model
        if client is None:
            from dotenv import find_dotenv, load_dotenv
            from google import genai
            from google.genai import types

            load_dotenv(find_dotenv(usecwd=True))  # the .env where the server is started
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise LLMError("GEMINI_API_KEY is not set (add it to .env on the server)")
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=config.GEMINI_TIMEOUT_MS),
            )
        self._client = client

    def generate(self, *, system: str, prompt: str, json_schema: dict | None = None) -> str:
        from google.genai import types

        settings: dict[str, Any] = {
            "system_instruction": system,
            "max_output_tokens": config.GEMINI_MAX_OUTPUT_TOKENS,
            "thinking_config": types.ThinkingConfig(thinking_level=config.GEMINI_THINKING_LEVEL),
        }
        if json_schema is not None:
            settings["response_mime_type"] = "application/json"
            settings["response_json_schema"] = gemini_schema(json_schema)
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(**settings),
            )
        except Exception as exc:  # network, quota, safety block, bad request
            # Only the type and status code: SDK messages can echo the prompt, which holds farmer
            # text, so we also drop the chained exception (``from None``) to keep it out of logs.
            code = getattr(exc, "code", None)
            detail = f"{type(exc).__name__}, code {code}" if code else type(exc).__name__
            raise LLMError(f"Gemini call failed ({detail})") from None
        text = getattr(response, "text", None)
        if not text:
            raise LLMError("Gemini returned an empty reply")
        return text
