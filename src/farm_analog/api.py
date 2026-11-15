"""The HTTP API (M5). Run: ``uvicorn farm_analog.api:app --reload`` (port 8000).

Endpoints:

- ``GET /health``: is the API up, and is it in live or offline-demo mode.
- ``POST /analogs``: an ``AnalogRequest`` (the drawn field) in, an ``AnalogResult`` out.
- ``POST /bill/parse`` (M9): the farmer's free text in, Bill's ``ParseResult`` out.
- ``POST /bill/summary`` (M9): an ``AnalogResult`` in, Bill's plain-language ``BillSummary`` out.

Privacy: field coordinates and farmer text are never logged; results and summaries are cached
in memory by a hash, and only for the life of the process.

Bill's response models are deliberately not part of the JSON contract in ``contract/`` (the
frontend's generated types come from there); they appear only in this API's OpenAPI schema.

Data flow:
Inputs:  HTTP requests from the React app (frontend/src/lib/api.ts) at http://localhost:8000:
         POST /analogs body = AnalogRequest JSON; POST /bill/parse body = {"text": ...};
         POST /bill/summary body = AnalogResult JSON. Environment: FRONTEND_ORIGINS (CORS),
         GEMINI_API_KEY (Bill), plus pipeline.py's EE_PROJECT / FARM_ANALOG_OFFLINE.
Outputs: JSON responses: GET /health -> {"status", "mode"}; POST /analogs -> AnalogResult
         (or 400 with a reason / 503 with a generic message); POST /bill/parse ->
         assistant.ParseResult; POST /bill/summary -> assistant.BillSummary. Logs never
         contain field coordinates or farmer text.
Used by: the frontend (frontend/src/lib/api.ts calls /health and /analogs), uvicorn
         (``uvicorn farm_analog.api:app``), tests/test_api.py and
         tests/test_assistant_api.py.
"""

import hashlib
import logging
import os
from collections import OrderedDict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from farm_analog import pipeline
from farm_analog.assistant import (
    LLM,
    BillSummary,
    FarmProfile,
    GeminiLLM,
    LLMError,
    ParseResult,
    parse_farmer_text,
    summarize,
)
from farm_analog.schema import AnalogRequest, AnalogResult

log = logging.getLogger("farm_analog.api")
CACHE_SIZE = 64

app = FastAPI(
    title="farm-analog",
    description="Find places whose climate today matches a farm's projected 2050s climate.",
    version="0.1.0",
)

# Only the frontend may call the API from a browser. Set FRONTEND_ORIGINS (comma-separated)
# for a deployed frontend; the default is the Vite dev server.
_origins = os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_cache: OrderedDict = OrderedDict()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": pipeline.mode()}


@app.post("/analogs", response_model=AnalogResult)
def analogs(request: AnalogRequest) -> AnalogResult:
    key = (pipeline.field_id(request.field), request.scenario, request.top_n, pipeline.mode())
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    try:
        result = pipeline.analyze(request)
    except pipeline.FieldNotSupported as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # Log the error type for debugging, but never the request (it holds the farm's location).
        log.exception("analysis failed for %s: %s", key[0], type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="The climate analysis couldn't be completed right now. Please try again.",
        ) from exc
    _cache[key] = result
    if len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)
    return result


# ---------------------------------------------------------------------------
# Bill (M9)
# ---------------------------------------------------------------------------

# The request may be longer than Bill reads (guard.py cuts it to MAX_FARMER_TEXT_CHARS), but
# anything beyond this is refused outright.
MAX_BILL_TEXT_CHARS = 10_000


class BillParseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(max_length=MAX_BILL_TEXT_CHARS)


def make_bill_llm() -> LLM | None:
    """Gemini if ``GEMINI_API_KEY`` is set on the server; otherwise None (template only)."""
    try:
        return GeminiLLM()
    except LLMError:
        log.info("GEMINI_API_KEY is not set: Bill uses template summaries and can't parse text")
        return None


# Built once, when the API starts. Tests replace it with a fake.
bill_llm: LLM | None = make_bill_llm()
_summary_cache: OrderedDict[str, BillSummary] = OrderedDict()


@app.post("/bill/parse", response_model=ParseResult)
def bill_parse(request: BillParseRequest) -> ParseResult:
    # Never log request.text: it's the farmer's own words.
    if bill_llm is None:
        return ParseResult(profile=FarmProfile(), ok=False,
                           error="Bill can't read text right now (no Gemini key on the server)")
    return parse_farmer_text(request.text, bill_llm)


@app.post("/bill/summary", response_model=BillSummary)
def bill_summary(result: AnalogResult) -> BillSummary:
    # The result holds analog coordinates; it's hashed for the cache key and never logged.
    key = hashlib.sha256(result.model_dump_json().encode()).hexdigest()
    if key in _summary_cache:
        _summary_cache.move_to_end(key)
        return _summary_cache[key]
    summary = summarize(result, bill_llm)
    # Don't cache a fallback caused by a passing Gemini failure; the next request may succeed.
    if summary.source == "gemini" or bill_llm is None:
        _summary_cache[key] = summary
        if len(_summary_cache) > CACHE_SIZE:
            _summary_cache.popitem(last=False)
    return summary
