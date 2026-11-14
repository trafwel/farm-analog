"""The JSON contract between the analog pipeline, the API and the frontend.

Every part of the app builds against these models:

- the pipeline (M1-M4, M7) produces an ``AnalogResult``,
- the API (M5) accepts an ``AnalogRequest`` and returns an ``AnalogResult``,
- the frontend (M6, M8) and Bill (M9) read the same shape, using the JSON Schema files
  exported to ``contract/`` (see ``farm_analog.contract``).

Units are fixed so nobody has to guess: temperatures in °C, precipitation in mm,
coordinates as (longitude, latitude) in degrees, as GeoJSON requires.
"""

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from farm_analog import config

Scenario = Literal["ssp245", "ssp585"]
MatchQuality = Literal["strong", "good", "weak", "none"]
Position = tuple[float, float]  # (longitude, latitude)


def match_quality(sigma: float) -> MatchQuality:
    """Plain-language label for a sigma dissimilarity value."""
    if sigma < config.STRONG_SIGMA:
        return "strong"
    if sigma < config.GOOD_SIGMA:
        return "good"
    if sigma < config.NOVEL_SIGMA:
        return "weak"
    return "none"


class _Model(BaseModel):
    # Reject unknown fields (catches typos on both sides) and make results immutable.
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------------------
# Request: what the frontend sends
# ---------------------------------------------------------------------------


class PolygonGeometry(_Model):
    """A GeoJSON Polygon: the farmer's field as drawn on the map."""

    type: Literal["Polygon"]
    coordinates: list[list[Position]] = Field(min_length=1)

    @field_validator("coordinates")
    @classmethod
    def _check_rings(cls, rings: list[list[Position]]) -> list[list[Position]]:
        total = 0
        for ring in rings:
            if len(ring) < 4:
                raise ValueError("each ring needs at least 4 positions (a closed triangle)")
            if ring[0] != ring[-1]:
                raise ValueError("each ring must be closed: first and last positions must match")
            for lon, lat in ring:
                if not (math.isfinite(lon) and math.isfinite(lat)):
                    raise ValueError("coordinates must be finite numbers")
                if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                    raise ValueError(f"position out of range: ({lon}, {lat})")
            total += len(ring)
        if total > config.MAX_POLYGON_VERTICES:
            raise ValueError(
                f"polygon has {total} vertices; the limit is {config.MAX_POLYGON_VERTICES}"
            )
        return rings


class AnalogRequest(_Model):
    """Find analogs for one field."""

    field: PolygonGeometry
    scenario: Scenario = config.DEFAULT_SCENARIO
    top_n: int = Field(default=config.DEFAULT_TOP_N, ge=1, le=config.MAX_TOP_N)


# ---------------------------------------------------------------------------
# Response: what the pipeline and API return
# ---------------------------------------------------------------------------


class SeasonalFingerprint(_Model):
    """The 8 climate values used for matching (definition in ``farm_analog.fingerprint``).

    For each calendar quarter: average temperature (``tmean_``, the mean of the three monthly
    mean temperatures, °C) and total precipitation (``ppt_``, mm). Quarters: ``jfm`` =
    Jan-Mar, ``amj`` = Apr-Jun, ``jas`` = Jul-Sep, ``ond`` = Oct-Dec.
    """

    tmean_jfm: float
    tmean_amj: float
    tmean_jas: float
    tmean_ond: float
    ppt_jfm: float = Field(ge=0)
    ppt_amj: float = Field(ge=0)
    ppt_jas: float = Field(ge=0)
    ppt_ond: float = Field(ge=0)


class MonthlyClimate(_Model):
    """Twelve monthly values, January first: mean temperature in °C, precipitation in mm."""

    tmean: list[float] = Field(min_length=12, max_length=12)
    ppt: list[float] = Field(min_length=12, max_length=12)


class Climograph(_Model):
    """Data for the comparison chart: the farm today, the farm in the future, the analog today."""

    farm_today: MonthlyClimate
    farm_future: MonthlyClimate
    analog_today: MonthlyClimate


class CropShare(_Model):
    crop: str
    share: float = Field(ge=0, le=1)  # fraction of cropland in the analog area


class SoilProfile(_Model):
    """Soil summary; any value can be missing where the soil survey has no data."""

    available_water_capacity_cm: float | None = Field(default=None, ge=0)
    clay_pct: float | None = Field(default=None, ge=0, le=100)
    sand_pct: float | None = Field(default=None, ge=0, le=100)
    organic_matter_pct: float | None = Field(default=None, ge=0, le=100)
    depth_to_restrictive_layer_cm: float | None = Field(default=None, ge=0)


class Analog(_Model):
    """One place whose climate today matches the farm's future climate."""

    rank: int = Field(ge=1)
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    place_name: str | None = None
    sigma: float = Field(ge=0)  # median across climate models
    match_quality: MatchQuality
    models_agree: int = Field(ge=0)  # models where this place is a good analog (sigma < 2)
    models_total: int = Field(ge=1)
    fingerprint: SeasonalFingerprint
    # Filled in by M7 (evidence); absent until then.
    crops: list[CropShare] | None = None
    soil: SoilProfile | None = None
    climograph: Climograph | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> "Analog":
        if self.match_quality != match_quality(self.sigma):
            raise ValueError(
                f"match_quality {self.match_quality!r} does not fit sigma "
                f"{self.sigma}; expected {match_quality(self.sigma)!r}"
            )
        if self.models_agree > self.models_total:
            raise ValueError("models_agree cannot exceed models_total")
        return self


class AnalogResult(_Model):
    """Everything the app shows for one field."""

    source: Literal["computed", "fixture"]  # "fixture" = fake demo data; the UI says so
    field_id: str
    scenario: Scenario
    baseline_years: tuple[int, int]
    future_years: tuple[int, int]
    models: list[str] = Field(min_length=1)
    farm_today: SeasonalFingerprint
    farm_future: SeasonalFingerprint
    farm_soil: SoilProfile | None = None
    novel_climate: bool  # True when the best analog's sigma is at or above NOVEL_SIGMA
    analogs: list[Analog]

    @model_validator(mode="after")
    def _check_consistency(self) -> "AnalogResult":
        ranks = [a.rank for a in self.analogs]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("analog ranks must run 1, 2, 3, ... in order")
        sigmas = [a.sigma for a in self.analogs]
        if sigmas != sorted(sigmas):
            raise ValueError("analogs must be sorted by sigma, best first")
        expected_novel = not self.analogs or self.analogs[0].sigma >= config.NOVEL_SIGMA
        if self.novel_climate != expected_novel:
            raise ValueError(
                f"novel_climate should be {expected_novel} for best sigma "
                f"{sigmas[0] if sigmas else 'n/a'}"
            )
        if any(a.models_total != len(self.models) for a in self.analogs):
            raise ValueError("each analog's models_total must equal the number of models")
        return self
