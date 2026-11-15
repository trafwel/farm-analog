"""The HTTP API (M5). Run: ``uvicorn farm_analog.api:app --reload`` (port 8000).

Endpoints:

- ``GET /health``: is the API up, and is it in live or offline-demo mode.
- ``POST /analogs``: an ``AnalogRequest`` (the drawn field) in, an ``AnalogResult`` out.

Privacy: field coordinates are never logged; results are cached in memory by a hash of the
field, and only for the life of the process.
"""

import logging
import os
from collections import OrderedDict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from farm_analog import pipeline
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
