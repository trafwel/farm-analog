"""Proof (M10): numbers that show the analogs mean something.

Three checks, from cheapest to most convincing:

1. **Self-check.** Match the farm's climate *today* against every place today. The farm's own
   area should come out as a strong match; if it doesn't, the matching is broken.
2. **Sigma vs. a plain baseline.** How much the sigma-dissimilarity ranking differs from a
   plain standardized distance, and (live, with several climate models) how many models
   agree on the top analogs.
3. **Backtest.** Treat ``BACKTEST_THEN_YEARS`` as "then" and ``BACKTEST_NOW_YEARS`` as "now".
   For each test cell, find analogs for its climate *now* among every cell's climate
   *then*, and check whether those places grew *then* what the test cell grows *now*
   (crop-mix similarity, 1 - Bray-Curtis). Compare with random farmland cells and with
   the test cell's own past ("nothing changed"). Cells within ``BACKTEST_EXCLUDE_KM`` are
   skipped, so an analog can't simply be a neighbor.

Checks 1 and 2 run offline on the team's data (``python -m farm_analog.proof``). The
backtest needs Earth Engine; its arithmetic is plain functions tested offline.

Data flow:
Inputs:  offline: the team's committed data via match.palouse_demo and
         candidates.load_candidates; live (EE_PROJECT set): the candidate cache
         (data/candidates/candidates.parquet) plus Earth Engine PRISM and CDL for
         config.BACKTEST_THEN_YEARS and BACKTEST_NOW_YEARS.
Outputs: dicts of numbers (self_check, rank_agreement), a ``BacktestResult``; ``main`` prints
         them and writes data/proof/proof.json (ignored by git).
Used by: ``python -m farm_analog.proof``; tests/test_proof.py; the numbers are quoted in
         docs/REVIEWS.md (M10).
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from farm_analog import candidates as cand
from farm_analog import config, fingerprint
from farm_analog.analogs import sigma_dissimilarity
from farm_analog.evidence import CROP_CODES
from farm_analog.farm_today import FarmToday

PROOF_DIR = cand.REPO / "data" / "proof"
EARTH_RADIUS_KM = 6371.0


# ---------------------------------------------------------------------------
# 1-2. Climate checks (offline)
# ---------------------------------------------------------------------------


def self_check(
    today: FarmToday, candidates: pd.DataFrame, home=config.PALOUSE_BOUNDS
) -> dict:
    """Match the farm today against every place today. ``home`` is the farm's own area
    (west, south, east, north); its cells should be strong matches."""
    target = fingerprint.from_contract(today.normal)
    sigma = sigma_dissimilarity(target, today.yearly_matrix, cand.matrix(candidates))
    west, south, east, north = home
    inside = candidates["lon"].between(west, east) & candidates["lat"].between(south, north)
    if not inside.any():
        raise ValueError("no candidate cells inside the farm's own area")
    return {
        "cells": int(len(candidates)),
        "home_cells": int(inside.sum()),
        "best_sigma": round(float(sigma.min()), 3),
        "best_is_home": bool(inside.iloc[int(np.argmin(sigma))]),
        "home_median_sigma": round(float(np.median(sigma[inside])), 3),
        "elsewhere_median_sigma": round(float(np.median(sigma[~inside])), 3)
        if (~inside).any()
        else None,
        "home_share_strong": round(float((sigma[inside] < config.STRONG_SIGMA).mean()), 3),
        "home_share_good": round(float((sigma[inside] < config.GOOD_SIGMA).mean()), 3),
    }


def rank_agreement(table: pd.DataFrame, top: int = config.DEFAULT_TOP_N) -> dict:
    """How the sigma ranking compares with the plain standardized-distance baseline, and how
    many climate models agree on the top analogs (``table`` from ``match.match``)."""
    by_baseline = table.sort_values(["standardized_euclidean", "cell_id"], kind="mergesort")
    top_sigma = set(table.head(top)["cell_id"])
    top_baseline = set(by_baseline.head(top)["cell_id"])
    rho = spearmanr(table["sigma"], table["standardized_euclidean"]).statistic
    head = table.head(top)
    return {
        "top": int(min(top, len(table))),
        "spearman": round(float(rho), 3),
        "top_overlap": len(top_sigma & top_baseline),
        "models_total": int(table["models_total"].iloc[0]),
        "top_mean_models_agree": round(float(head["models_agree"].mean()), 2),
        "top_all_models_agree": int((head["models_agree"] == head["models_total"]).sum()),
    }


def palouse_proof() -> dict:
    """Checks 1 and 2 on the offline Palouse demo (the team's committed data)."""
    from farm_analog.match import palouse_demo, palouse_today_from_cache

    _, table = palouse_demo()
    today = palouse_today_from_cache(json.loads(cand.TEAM_CACHE.read_text()))
    candidates, note = cand.load_candidates()
    return {
        "data": f"offline Palouse demo; candidates: {note}",
        "self_check": self_check(today, candidates),
        "rank_agreement": rank_agreement(table),
    }


# ---------------------------------------------------------------------------
# 3. Backtest arithmetic (offline)
# ---------------------------------------------------------------------------


def crop_mix(counts: dict[int, float]) -> dict[int, float]:
    """Cropland Data Layer pixel counts -> share of cropland by crop code (non-crop land
    such as forest or towns left out). Empty if there's no cropland."""
    crops = {int(c): float(n) for c, n in counts.items() if int(c) in CROP_CODES and n > 0}
    total = sum(crops.values())
    return {c: n / total for c, n in crops.items()} if total else {}


def similarity(a: dict[int, float], b: dict[int, float]) -> float:
    """Crop-mix similarity, 1 - Bray-Curtis: 1 = the same crops in the same shares,
    0 = nothing in common. For shares that each sum to 1 it is the overlap sum(min)."""
    if not a or not b:
        return float("nan")
    return float(sum(min(a.get(c, 0.0), b.get(c, 0.0)) for c in set(a) | set(b)))


def average_mix(mixes: list[dict[int, float]]) -> dict[int, float]:
    mixes = [m for m in mixes if m]
    if not mixes:
        return {}
    codes = set().union(*mixes)
    return {c: sum(m.get(c, 0.0) for m in mixes) / len(mixes) for c in codes}


def distance_km(lon, lat, lons, lats) -> np.ndarray:
    """Great-circle distance from one point to many (haversine)."""
    lon, lat, lons, lats = (np.radians(np.asarray(v, dtype=float)) for v in (lon, lat, lons, lats))
    h = np.sin((lats - lat) / 2) ** 2 + np.cos(lat) * np.cos(lats) * np.sin((lons - lon) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


@dataclass(frozen=True)
class Picks:
    """For one test cell: its best analogs "then" and the same number of random cells."""

    analogs: tuple[str, ...]
    random: tuple[str, ...]
    best_sigma: float


def pick_cells(
    now: pd.DataFrame,
    then: pd.DataFrame,
    yearly: dict[str, np.ndarray],
    k: int = config.BACKTEST_ANALOGS,
    exclude_km: float = config.BACKTEST_EXCLUDE_KM,
    seed: int = 0,
) -> dict[str, Picks]:
    """Choose analogs (lowest sigma) and random cells for each test cell.

    ``now``: test cells (``cell_id``, ``lon``, ``lat``, FEATURES) with their climate now.
    ``then``: every cell, same columns, with its climate then.
    ``yearly``: per test cell, its (years x features) year-to-year values, which set the
    sigma scale. Cells within ``exclude_km`` of the test cell are never picked.
    """
    rng = np.random.default_rng(seed)
    pool = then.reset_index(drop=True)
    places = cand.matrix(pool)
    picks = {}
    for row in now.itertuples(index=False):
        far = distance_km(row.lon, row.lat, pool["lon"], pool["lat"]) > exclude_km
        if far.sum() < k:
            continue
        target = np.array([getattr(row, f) for f in fingerprint.FEATURES], dtype=float)
        sigma = sigma_dissimilarity(target, yearly[row.cell_id], places[far])
        ids = pool.loc[far, "cell_id"].to_numpy()
        order = np.argsort(sigma, kind="mergesort")[:k]
        picks[row.cell_id] = Picks(
            analogs=tuple(ids[order]),
            random=tuple(rng.choice(ids, size=k, replace=False)),
            best_sigma=float(sigma[order[0]]),
        )
    return picks


@dataclass(frozen=True)
class BacktestResult:
    test_cells: int
    analog_similarity: float  # mean crop-mix similarity: analogs then vs. test cell now
    random_similarity: float  # the same for random farmland cells (the baseline to beat)
    persistence_similarity: float  # the test cell then vs. now ("nothing changed")
    analog_beats_random: float  # share of test cells where analogs beat random cells
    median_best_sigma: float


def score_backtest(
    picks: dict[str, Picks],
    crops_then: dict[str, dict[int, float]],
    crops_now: dict[str, dict[int, float]],
) -> BacktestResult:
    """Crop-mix similarity of analogs vs. random cells vs. persistence (shares, by cell)."""
    rows = []
    for cell, p in picks.items():
        now = crops_now.get(cell, {})
        analog = similarity(now, average_mix([crops_then.get(c, {}) for c in p.analogs]))
        random = similarity(now, average_mix([crops_then.get(c, {}) for c in p.random]))
        persistence = similarity(now, crops_then.get(cell, {}))
        if np.isfinite(analog) and np.isfinite(random):
            rows.append((analog, random, persistence, p.best_sigma))
    if not rows:
        raise ValueError("no test cell had crop data for both its analogs and random cells")
    a, r, s, best = (np.array(col, dtype=float) for col in zip(*rows, strict=True))
    return BacktestResult(
        test_cells=len(rows),
        analog_similarity=round(float(a.mean()), 3),
        random_similarity=round(float(r.mean()), 3),
        persistence_similarity=round(float(np.nanmean(s)), 3),
        analog_beats_random=round(float((a > r).mean()), 3),
        median_best_sigma=round(float(np.median(best)), 3),
    )


# ---------------------------------------------------------------------------
# Earth Engine (needs login and network)
# ---------------------------------------------------------------------------


def _points(ee, frame: pd.DataFrame):
    return ee.FeatureCollection(
        [
            ee.Feature(ee.Geometry.Point([r.lon, r.lat]), {"cell_id": r.cell_id})
            for r in frame.itertuples(index=False)
        ]
    )


def _chunks(frame: pd.DataFrame, size: int = 500):
    for start in range(0, len(frame), size):
        yield frame.iloc[start : start + size]


def fetch_yearly(cells: pd.DataFrame, years=config.BASELINE_YEARS) -> dict[str, np.ndarray]:
    """Each cell's yearly fingerprints (years x features) from PRISM."""
    from farm_analog.earthengine import initialize

    ee = initialize()
    prism = ee.ImageCollection(config.PRISM_COLLECTION).filter(
        ee.Filter.eq("dataset_type", config.PRISM_DATASET_TYPE)
    )
    bands = []
    for year in range(years[0], years[1] + 1):
        months = prism.filterDate(f"{year}-01-01", f"{year + 1}-01-01")
        for q, (lo, hi) in enumerate(fingerprint.QUARTERS.values()):
            quarter = months.filter(ee.Filter.calendarRange(lo, hi, "month"))
            bands.append(quarter.select("tmean").mean().rename(f"temperature_{q}_{year}"))
            bands.append(quarter.select("ppt").sum().rename(f"precipitation_{q}_{year}"))
    image = ee.Image.cat(bands)
    out = {}
    for chunk in _chunks(cells):
        features = image.reduceRegions(
            collection=_points(ee, chunk), reducer=ee.Reducer.first(), scale=config.GRID_SCALE_M
        ).getInfo()["features"]
        for f in features:
            p = f["properties"]
            out[p["cell_id"]] = np.array(
                [[p[f"{name}_{y}"] for name in fingerprint.FEATURES]
                 for y in range(years[0], years[1] + 1)],
                dtype=float,
            )
    return out


def fetch_crop_mix(cells: pd.DataFrame, years: tuple[int, int]) -> dict[str, dict[int, float]]:
    """Each ~4 km cell's crop mix over ``years`` (CDL pixel counts within half a cell)."""
    from farm_analog.earthengine import initialize

    ee = initialize()
    cdl = ee.ImageCollection("USDA/NASS/CDL").filterDate(
        f"{years[0]}-01-01", f"{years[1] + 1}-01-01"
    )
    images = [ee.Image(i["id"]).select("cropland") for i in cdl.toList(cdl.size()).getInfo()]
    counts: dict[str, dict[int, float]] = {c: {} for c in cells["cell_id"]}
    for chunk in _chunks(cells):
        areas = _points(ee, chunk).map(lambda f: f.buffer(config.GRID_SCALE_M / 2))
        for image in images:
            for f in image.reduceRegions(
                collection=areas, reducer=ee.Reducer.frequencyHistogram(), scale=30
            ).getInfo()["features"]:
                cell = counts[f["properties"]["cell_id"]]
                for code, n in (f["properties"].get("histogram") or {}).items():
                    cell[int(float(code))] = cell.get(int(float(code)), 0) + n
    return {c: crop_mix(n) for c, n in counts.items()}


def run_backtest(n_cells: int = config.BACKTEST_TEST_CELLS, seed: int = 0) -> BacktestResult:
    """The full backtest on the real candidate cache (live mode only)."""
    if not cand.CACHE_FILE.exists():
        raise RuntimeError("build the candidate cache first: python -m farm_analog.candidates")
    pool, _ = cand.load_candidates()
    then = cand.fetch_candidates(years=config.BACKTEST_THEN_YEARS)
    now = cand.fetch_candidates(years=config.BACKTEST_NOW_YEARS)
    shared = sorted(set(then["cell_id"]) & set(now["cell_id"]) & set(pool["cell_id"]))
    test_ids = set(np.random.default_rng(seed).choice(shared, min(n_cells, len(shared)), False))
    then = then[then["cell_id"].isin(shared)]
    test_now = now[now["cell_id"].isin(test_ids)]
    picks = pick_cells(test_now, then, fetch_yearly(test_now), seed=seed)
    needed = set(picks) | {c for p in picks.values() for c in (*p.analogs, *p.random)}
    then_cells = then[then["cell_id"].isin(needed)]
    return score_backtest(
        picks,
        fetch_crop_mix(then_cells, config.BACKTEST_THEN_YEARS),
        fetch_crop_mix(test_now[test_now["cell_id"].isin(picks)], config.BACKTEST_NOW_YEARS),
    )


def main() -> Path:
    from farm_analog import pipeline

    report = {"palouse": palouse_proof()}
    if pipeline.mode() == "live":
        report["backtest"] = {
            "then_years": list(config.BACKTEST_THEN_YEARS),
            "now_years": list(config.BACKTEST_NOW_YEARS),
            "exclude_km": config.BACKTEST_EXCLUDE_KM,
            **asdict(run_backtest()),
        }
    else:
        report["backtest"] = "not run: needs Earth Engine (set EE_PROJECT)"
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    path = PROOF_DIR / "proof.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return path


if __name__ == "__main__":
    main()
