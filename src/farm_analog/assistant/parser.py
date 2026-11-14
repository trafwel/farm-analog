"""Bill's first job: turn a farmer's free text into validated key-value pairs.

Problem: farmers describe their operation in their own words ("800 acres of dryland wheat and
peas, worried about drought"). The app needs fields it can use.

Approach: Gemini's structured output. We send the JSON Schema of ``FarmProfile`` and Gemini must
reply with JSON in that shape. Gemini only *extracts*: the system prompt forbids guessing,
inferring or advising. We never trust the reply: it is validated with Pydantic, and anything
invalid gives an empty profile plus an error message instead of a crash.

Why structured output instead of "please reply in JSON": the schema constrains the model's
decoding, so replies are almost always well formed; the Pydantic check covers the rest.
"""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from farm_analog.assistant.guard import UNTRUSTED_TEXT_RULE, clean_text, wrap_untrusted
from farm_analog.assistant.llm import LLM, LLMError

Worry = Literal[
    "drought", "heat", "frost", "erosion", "wind", "flooding", "pests", "disease",
    "soil_health", "water_supply", "markets", "other",
]


class FarmProfile(BaseModel):
    """What the farmer told us, as fields. Every field is optional: unknown stays empty."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    crops: list[str] = Field(default_factory=list, max_length=20,
                             description="Crops the farmer grows, as written, e.g. 'winter wheat'")
    acres: float | None = Field(default=None, ge=0, le=1_000_000,
                                description="Farm size in acres, only if stated")
    irrigated: bool | None = Field(default=None,
                                   description="true if irrigated, false if dryland, else null")
    worries: list[Worry] = Field(default_factory=list, max_length=12,
                                 description="Main concerns the farmer names")
    priorities: list[str] = Field(default_factory=list, max_length=10,
                                  description="Goals the farmer states, short phrases")
    unparsed_notes: str | None = Field(default=None, max_length=500,
                                       description="Anything relevant that fits no other field")


class ParseResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile: FarmProfile
    ok: bool
    error: str | None = None


PARSER_SYSTEM_PROMPT = f"""You are a data-entry tool for a farm climate app. Your only job is to
copy facts the farmer states into the JSON fields of the given schema.

Rules:
- Extract only what the farmer explicitly says. Do not guess, infer, calculate, or advise.
- Leave a field empty (null or []) when the farmer doesn't say it.
- acres: fill only if the farmer gives a size in acres. Never convert units: a size in hectares
  or any other unit goes into unparsed_notes as written.
- irrigated: true only if they say irrigated; false only if they say dryland or not irrigated.
- worries: pick from the allowed values; use "other" and unparsed_notes for anything else.
- Reply with JSON only, matching the schema.

{UNTRUSTED_TEXT_RULE}"""

# Cap the strings Gemini returns before validation, so one oversized item doesn't throw away
# the whole profile.
_MAX_ITEM_CHARS = 60


def _trim(data: dict) -> dict:
    for key in ("crops", "priorities"):
        if isinstance(data.get(key), list):
            data[key] = [s.strip()[:_MAX_ITEM_CHARS] for s in data[key] if isinstance(s, str)]
    if isinstance(data.get("unparsed_notes"), str):
        data["unparsed_notes"] = data["unparsed_notes"][:500]
    return data


def parse_farmer_text(text: str, llm: LLM) -> ParseResult:
    """Parse free text into a ``FarmProfile``. Never raises; failures come back as ``ok=False``."""
    if not clean_text(text):
        return ParseResult(profile=FarmProfile(), ok=True)
    try:
        reply = llm.generate(
            system=PARSER_SYSTEM_PROMPT,
            prompt=f"Extract the farm details from this message.\n\n{wrap_untrusted(text)}",
            json_schema=FarmProfile.model_json_schema(),
        )
    except LLMError as exc:
        return ParseResult(profile=FarmProfile(), ok=False, error=str(exc))
    try:
        data = json.loads(reply)
        if not isinstance(data, dict):
            raise ValueError("reply is not a JSON object")
        profile = FarmProfile.model_validate(_trim(data))
    except (ValueError, ValidationError) as exc:  # JSONDecodeError is a ValueError
        # Report the kind of failure, not the reply itself (it may echo farmer text).
        kind = "invalid JSON" if isinstance(exc, json.JSONDecodeError) else "schema mismatch"
        return ParseResult(profile=FarmProfile(), ok=False,
                           error=f"Bill couldn't read the model's reply ({kind})")
    return ParseResult(profile=profile, ok=True)
