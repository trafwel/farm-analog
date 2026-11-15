"""Bill, the Gemini assistant (M9).

Bill does exactly two things and never reasons or decides:

1. ``parse_farmer_text``: farmer's free text -> validated ``FarmProfile`` fields.
2. ``summarize``: computed ``AnalogResult`` -> plain-language ``BillSummary``, with a code-level
   grounding check and a deterministic fallback.

Both take an ``LLM`` (``GeminiLLM`` in the app, a fake in tests) and never raise on bad output.

Data flow:
Inputs:  what the submodules take: farmer text (parser) and AnalogResult (summarizer), plus
         an LLM object (GeminiLLM, or a fake in tests).
Outputs: re-exports LLM, GeminiLLM, LLMError, FarmProfile, ParseResult, parse_farmer_text,
         BillSummary, summarize.
Used by: api.py (/bill/parse, /bill/summary) and the assistant tests.
"""

from farm_analog.assistant.llm import LLM, GeminiLLM, LLMError
from farm_analog.assistant.parser import FarmProfile, ParseResult, parse_farmer_text
from farm_analog.assistant.summarizer import BillSummary, summarize

__all__ = [
    "LLM", "GeminiLLM", "LLMError",
    "FarmProfile", "ParseResult", "parse_farmer_text",
    "BillSummary", "summarize",
]
