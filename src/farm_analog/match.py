"""Matching (M4): rank candidate places by how closely their climate today matches a farm's
future climate, across every climate model.

For each model, sigma dissimilarity measures the distance from that model's version of the
farm's future to every candidate, in units of the farm's own year-to-year variation. The
headline score is the median across models; ``models_agree`` counts the models that call
the place a good analog (sigma below ``config.GOOD_SIGMA``). A plain standardized distance
is kept beside it as a baseline, so we can show sigma dissimilarity adds something.

``palouse_demo`` builds a complete result offline from the team's committed data, so the
app and API work without Earth Engine.

Data flow:
Inputs:  ``FarmToday`` (farm_today.py), ``FarmFuture`` (future.py), the candidates
         DataFrame (candidates.py). The offline demo reads
         data/samples/palouse_prism_analog_inputs.json and
         data/samples/palouse_climate_ACCESS-CM2_ssp245_2050.csv instead.
Outputs: ``match`` -> ranked DataFrame (candidate columns + sigma_<model>, sigma,
         models_agree, models_total, standardized_euclidean, rank); ``to_result`` -> the
         top N as a schema.AnalogResult; ``palouse_demo`` -> (AnalogResult, table).
Used by: pipeline.py (both modes), proof.py (palouse_proof uses the demo table),
         tests/test_match.py (regression against the team's committed rankings).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from farm_analog import candidates as cand
from farm_analog import config, fingerprint
from farm_analog.analogs import sigma_dissimilarity
from farm_analog.farm_today import FarmToday
from farm_analog.future import FarmFuture, farm_future, quarterly_change
from farm_analog.schema import Analog, AnalogResult, match_quality

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"
TEAM_MODEL_CSV = SAMPLES / "palouse_climate_ACCESS-CM2_ssp245_2050.csv"


def match(today: FarmToday, future: FarmFuture, candidates: pd.DataFrame) -> pd.DataFrame:
    """Score every candidate; return them ranked best first.

    Columns: the candidate's id, location, fingerprint and cultivated share, plus
    ``sigma_<model>`` per model, ``sigma`` (median), ``models_agree``, ``models_total``,
    ``standardized_euclidean`` (baseline) and ``rank``.
    """
    yearly = today.yearly_matrix
    places = cand.matrix(candidates)
    table = candidates.copy()
    scores = []
    for model, future_vector in future.per_model.items():
        sigma = sigma_dissimilarity(future_vector, yearly, places)
        table[f"sigma_{model}"] = sigma
        scores.append(sigma)
    scores = np.column_stack(scores)
    table["sigma"] = np.median(scores, axis=1)
    table["models_agree"] = (scores < config.GOOD_SIGMA).sum(axis=1)
    table["models_total"] = scores.shape[1]
    spread = yearly.std(axis=0, ddof=1)
    table["standardized_euclidean"] = np.linalg.norm((places - future.median) / spread, axis=1)
    table = table.sort_values(["sigma", "cell_id"], kind="mergesort").reset_index(drop=True)
    table.insert(0, "rank", np.arange(1, len(table) + 1))
    return table


def to_result(
    table: pd.DataFrame,
    today: FarmToday,
    future: FarmFuture,
    field_id: str,
    top_n: int = config.DEFAULT_TOP_N,
    notes: list[str] | None = None,
) -> AnalogResult:
    """The top ``top_n`` matches in the JSON contract."""
    analogs = []
    for row in table.head(top_n).itertuples(index=False):
        sigma = round(float(row.sigma), 3)
        values = np.array([getattr(row, f) for f in fingerprint.FEATURES], dtype=float)
        analogs.append(
            Analog(
                rank=int(row.rank),
                lon=float(row.lon),
                lat=float(row.lat),
                sigma=sigma,
                match_quality=match_quality(sigma),
                models_agree=int(row.models_agree),
                models_total=int(row.models_total),
                fingerprint=fingerprint.to_contract(values),
            )
        )
    best = analogs[0].sigma if analogs else None
    return AnalogResult(
        source="computed",
        field_id=field_id,
        scenario=future.scenario,
        baseline_years=today.years,
        future_years=future.future_years,
        models=future.models,
        farm_today=today.normal,
        farm_future=future.headline,
        novel_climate=best is None or best >= config.NOVEL_SIGMA,
        analogs=analogs,
        notes=list(notes or []),
    )


def palouse_today_from_cache(payload: dict) -> FarmToday:
    """The Palouse-wide present-day climate from the team's cached PRISM years."""
    yearly = pd.DataFrame(payload["annual"]).set_index("year")[fingerprint.FEATURES]
    first, last = payload["reference_years"]
    return FarmToday(
        normal=fingerprint.to_contract(fingerprint.normal(yearly)),
        yearly=yearly,
        years=(int(first), int(last)),
        support="palouse_regional_mean",
    )


def palouse_demo(top_n: int = config.DEFAULT_TOP_N) -> tuple[AnalogResult, pd.DataFrame]:
    """A real (not fake) result computed offline from the team's committed data.

    Limits, stated in the result's notes: the target is the Palouse-wide average rather than
    a drawn field, and only one climate model (ACCESS-CM2) is available offline.
    """
    payload = json.loads(cand.TEAM_CACHE.read_text())
    today = palouse_today_from_cache(payload)
    change = quarterly_change(pd.read_csv(TEAM_MODEL_CSV), "ACCESS-CM2")
    future = farm_future(fingerprint.from_contract(today.normal), [change])
    candidates, candidate_note = cand.team_candidates()
    table = match(today, future, candidates)
    notes = [
        "Offline Palouse demo: the target is the Palouse-wide average climate from cached "
        "PRISM data, not your drawn field.",
        "One climate model (ACCESS-CM2), which runs warmer than most; a full run uses "
        f"{len(config.CLIMATE_MODELS)} models.",
        f"Candidates: {candidate_note}.",
    ]
    return to_result(table, today, future, "palouse-demo", top_n, notes), table
