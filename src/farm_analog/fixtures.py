"""Fake analog results so the frontend and Bill can be built before the pipeline exists.

The numbers are believable but invented, and every result is marked ``source="fixture"``
so the app can show that it's demo data. Generation is deterministic (fixed random seed),
so rerunning the script produces exactly the committed file; a test checks that.
"""

import json
import math
from pathlib import Path

import numpy as np

from farm_analog import config
from farm_analog.schema import (
    Analog,
    AnalogResult,
    Climograph,
    CropShare,
    MonthlyClimate,
    SeasonalFingerprint,
    SoilProfile,
    match_quality,
)

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "fake_results.json"
FAKE_MODELS = ["fake-model-a", "fake-model-b", "fake-model-c", "fake-model-d", "fake-model-e"]

# Roughly Palouse-like seasonal climate (°C and mm), invented for the fixture.
_FARM_TODAY = {
    "tmax_djf": 3.0, "tmax_mam": 14.0, "tmax_jja": 28.0, "tmax_son": 16.0,
    "tmin_djf": -5.0, "tmin_mam": 1.0, "tmin_jja": 9.0, "tmin_son": 2.0,
    "ppt_djf": 190.0, "ppt_mam": 140.0, "ppt_jja": 50.0, "ppt_son": 110.0,
}
_WARMING_C = 2.5
_PPT_RATIO = {"djf": 1.08, "mam": 1.03, "jja": 0.85, "son": 1.0}


def _future(today: dict[str, float]) -> dict[str, float]:
    out = {}
    for key, value in today.items():
        kind, season = key.split("_")
        out[key] = value + _WARMING_C if kind in ("tmax", "tmin") else value * _PPT_RATIO[season]
    return out


def _round(d: dict[str, float]) -> dict[str, float]:
    return {k: round(v, 2) for k, v in d.items()}


def _monthly(fp: dict[str, float]) -> MonthlyClimate:
    """Spread seasonal values over 12 months: a smooth temperature curve, rain by season."""
    season_of = ["djf", "djf", "mam", "mam", "mam", "jja", "jja", "jja", "son", "son", "son", "djf"]
    tmax, tmin, ppt = [], [], []
    for month, season in enumerate(season_of):
        wiggle = 1.5 * math.sin(2 * math.pi * (month - 3) / 12)  # warmer mid-season shape
        tmax.append(round(fp[f"tmax_{season}"] + wiggle, 2))
        tmin.append(round(fp[f"tmin_{season}"] + wiggle, 2))
        ppt.append(round(fp[f"ppt_{season}"] / 3, 2))
    return MonthlyClimate(tmax=tmax, tmin=tmin, ppt=ppt)


def _fake_result(field_id: str, rng: np.random.Generator, novel: bool) -> AnalogResult:
    today = dict(_FARM_TODAY)
    if novel:  # a drier, hotter farm with no good match
        today = {k: (v * 0.5 if k.startswith("ppt") else v + 1.0) for k, v in today.items()}
    future = _future(today)

    sigmas = np.sort(rng.uniform(4.2, 6.5, 8) if novel else rng.uniform(0.5, 3.6, 20))
    analogs = []
    for i, sigma in enumerate(sigmas):
        sigma = round(float(sigma), 2)
        fp = {k: v + rng.normal(0, 0.4 * sigma) for k, v in future.items()}
        fp = {k: max(v, 0.0) if k.startswith("ppt") else v for k, v in fp.items()}
        top3 = i < 3
        analogs.append(Analog(
            rank=i + 1,
            lon=round(float(rng.uniform(-119.0, -118.0)), 4),
            lat=round(float(rng.uniform(45.5, 46.3)), 4),
            place_name=f"Example area {i + 1}",
            sigma=sigma,
            match_quality=match_quality(sigma),
            models_agree=int(sum(rng.uniform(0, 3) > sigma for _ in FAKE_MODELS)),
            models_total=len(FAKE_MODELS),
            fingerprint=SeasonalFingerprint(**_round(fp)),
            crops=[
                CropShare(crop="Winter wheat", share=0.45),
                CropShare(crop="Fallow", share=0.25),
                CropShare(crop="Dry peas", share=0.12),
                CropShare(crop="Chickpeas", share=0.08),
                CropShare(crop="Other", share=0.10),
            ] if top3 else None,
            soil=SoilProfile(available_water_capacity_cm=round(float(rng.uniform(12, 25)), 1),
                             clay_pct=round(float(rng.uniform(15, 25)), 1),
                             sand_pct=round(float(rng.uniform(10, 30)), 1),
                             organic_matter_pct=round(float(rng.uniform(1.5, 3.5)), 2),
                             depth_to_restrictive_layer_cm=150.0) if top3 else None,
            climograph=Climograph(farm_today=_monthly(today), farm_future=_monthly(future),
                                  analog_today=_monthly(fp)) if top3 else None,
        ))

    return AnalogResult(
        source="fixture",
        field_id=field_id,
        scenario=config.DEFAULT_SCENARIO,
        baseline_years=config.BASELINE_YEARS,
        future_years=config.FUTURE_YEARS,
        models=FAKE_MODELS,
        farm_today=SeasonalFingerprint(**_round(today)),
        farm_future=SeasonalFingerprint(**_round(future)),
        farm_soil=SoilProfile(available_water_capacity_cm=22.0, clay_pct=20.0, sand_pct=12.0,
                              organic_matter_pct=3.0, depth_to_restrictive_layer_cm=150.0),
        novel_climate=novel,
        analogs=analogs,
    )


def make_fake_results(seed: int = 484) -> list[AnalogResult]:
    """Two fields: a normal Palouse case and a novel-climate case (to build the warning)."""
    rng = np.random.default_rng(seed)
    return [_fake_result("fake-colfax", rng, novel=False),
            _fake_result("fake-lind", rng, novel=True)]


def to_json(results: list[AnalogResult]) -> str:
    return json.dumps([r.model_dump(mode="json") for r in results], indent=2) + "\n"


def load_fake_results(path: Path = FIXTURE_PATH) -> list[AnalogResult]:
    return [AnalogResult.model_validate(r) for r in json.loads(path.read_text())]
