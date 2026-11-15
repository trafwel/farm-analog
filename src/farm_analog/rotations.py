"""Rotation strategies (M12): what farmers in the analog areas actually rotate, compared with
the field's current rotation.

The challenge asks for at least three rotation strategies, including the existing one, each
with why it was suggested, the evidence, benefits, information gaps and risks. Our evidence is
observed practice: the USDA Cropland Data Layer (CDL) labels every 30 m pixel's crop every
year, so a pixel's sequence over ``ROTATION_YEARS`` shows the rotation grown there. Places
whose climate *today* matches the field's 2050 climate show which rotations already work in
that climate.

Steps:

1. ``crop_group`` turns CDL codes into a few agronomic groups (winter wheat, pulses, fallow...).
2. ``rotation_of`` finds a pixel's repeating cycle (period 1-4 years); a pixel without a clear
   cycle is labelled by its main crops ("flexible").
3. ``rotation_shares`` gives each rotation's share of an area's sampled cropland.
4. ``strategies`` ranks the analog areas' rotations, puts the field's current rotation first,
   and writes why / evidence / benefits / risks / gaps for each from ``TRAITS``.

``TRAITS`` holds general agronomy for the inland Northwest (sources noted beside it). It is
deliberately qualitative: the tool compares options; it does not predict yields or profit.

Data flow:
Inputs:  per-pixel CDL crop codes by year for the field and the top analog areas, fetched from
         Earth Engine (``USDA/NASS/CDL``, ``ROTATION_YEARS``) by ``fetch_sequences``; the
         ``AnalogResult`` from match.to_result / evidence.attach (for ranks and model agreement).
Outputs: a list of schema.RotationStrategy (current rotation first), attached to
         ``AnalogResult.rotations`` by ``add_rotations``.
Used by: pipeline._analyze_live (wrapped so a failure only adds a note); the frontend and Bill
         read ``rotations`` from the result.
"""

from collections import Counter
from dataclasses import dataclass

import numpy as np

from farm_analog.schema import AnalogResult, RotationStrategy

ROTATION_YEARS = (2016, 2023)  # 8 years: two full cycles of a 2-, 3- or 4-year rotation
ANALOGS_FOR_ROTATIONS = 5  # top analog areas sampled
ANALOG_RADIUS_M = 2000  # sample within this distance of each analog point
PIXELS_PER_AREA = 400  # random 30 m pixels sampled per area
MIN_CROPPED_YEARS = 5  # a pixel needs at least this many cropped years to read a rotation
CYCLE_MATCH = 0.8  # share of years that must repeat for a cycle to count
MIN_SHARE = 0.05  # rotations below this share of an area's cropland are ignored
USED_SHARE = 0.10  # an analog area "uses" a rotation at or above this share

# CDL codes -> agronomic group. Codes not listed are either non-crop land (None) or, if they
# are crops, "Other crops".
_GROUPS = {
    "Winter wheat": [24],
    "Spring wheat": [22, 23],
    "Barley": [21],
    "Other small grains": [25, 27, 28, 29, 205],
    "Pulses": [51, 52, 53, 42],  # chickpeas, lentils, peas, dry beans
    "Canola": [31, 32, 33, 34, 35, 38],  # canola, flax, safflower, rapeseed, mustard, camelina
    "Fallow": [61],
    "Hay and forage": [36, 37, 58, 59, 60],  # alfalfa, hay, clover, grass seed, switchgrass
    "Corn": [1, 12, 13],
    "Potatoes and beets": [41, 43],
}
_CODE_TO_GROUP = {code: group for group, codes in _GROUPS.items() for code in codes}
CROP_CODES = set(range(1, 62)) | set(range(66, 78)) | set(range(204, 255))


def crop_group(code: int | None) -> str | None:
    """CDL code -> group name, "Other crops" for other crop codes, None for non-crop land."""
    if code is None or (isinstance(code, float) and np.isnan(code)):
        return None
    code = int(code)
    if code in _CODE_TO_GROUP:
        return _CODE_TO_GROUP[code]
    if 225 <= code <= 254 or code == 26:
        return "Double crop"
    return "Other crops" if code in CROP_CODES else None


# General agronomy for inland Northwest dryland systems, by group: nitrogen fixing, residue
# left for soil cover, relative water use, and short notes. Sources: WSU Extension dryland
# cropping-systems publications and USDA-NRCS conservation crop rotation guidance (general
# statements only; local conditions vary).
TRAITS = {
    "Winter wheat": {"n_fixing": False, "residue": "high", "water": "medium",
                     "benefit": "Main cash crop of the region; heavy residue protects the soil",
                     "risk": "Yield depends on spring rain and suffers from heat during grain "
                             "fill in early summer"},
    "Spring wheat": {"n_fixing": False, "residue": "medium", "water": "medium",
                     "benefit": "Spring planting breaks winter-annual weed cycles",
                     "risk": "Shorter season; more exposed to early-summer heat and drought"},
    "Barley": {"n_fixing": False, "residue": "medium", "water": "medium",
               "benefit": "Shorter season than wheat; feed or malt market",
               "risk": "Shares several diseases with wheat"},
    "Other small grains": {"n_fixing": False, "residue": "medium", "water": "medium",
                           "benefit": "Adds a different cereal to the rotation",
                           "risk": "Smaller, less certain markets"},
    "Pulses": {"n_fixing": True, "residue": "low", "water": "low",
               "benefit": "Fixes nitrogen for the next wheat crop and breaks cereal disease "
                          "and weed cycles",
               "risk": "Low residue leaves soil more exposed to erosion"},
    "Canola": {"n_fixing": False, "residue": "medium", "water": "medium",
               "benefit": "Broadleaf break crop; deep taproot",
               "risk": "Stand establishment is difficult in dry falls; needs a crusher or "
                       "buyer nearby"},
    "Fallow": {"n_fixing": False, "residue": "low", "water": "none",
               "benefit": "Stores soil water for the next crop in the driest areas",
               "risk": "No crop that year, and bare or thin cover raises wind and water "
                       "erosion risk"},
    "Hay and forage": {"n_fixing": True, "residue": "high", "water": "high",
                       "benefit": "Year-round cover builds organic matter and cuts erosion; "
                                  "forage income",
                       "risk": "Uses more water than grain crops; needs a livestock market"},
    "Corn": {"n_fixing": False, "residue": "high", "water": "high",
             "benefit": "High residue",
             "risk": "Usually needs irrigation in this region"},
    "Potatoes and beets": {"n_fixing": False, "residue": "low", "water": "high",
                           "benefit": "High-value crops",
                           "risk": "Need irrigation; low residue leaves soil exposed"},
    "Double crop": {"n_fixing": False, "residue": "medium", "water": "high",
                    "benefit": "Two harvests in one year",
                    "risk": "Rarely possible without irrigation in dryland areas"},
    "Other crops": {"n_fixing": False, "residue": "medium", "water": "medium",
                    "benefit": "Diversifies the rotation",
                    "risk": "Markets and practices not assessed here"},
}

ALWAYS_GAPS = (
    "Pest and disease pressure, yields and prices are not measured here.",
    "Analog areas' rotations also reflect their markets, equipment and soils, not only climate.",
)
CHECK_LOCALLY = "Check with your county extension agent before changing a rotation."


@dataclass(frozen=True)
class Rotation:
    """One rotation: a repeating cycle (``kind="cycle"``) or a crop mix with no fixed order
    (``kind="flexible"``)."""

    kind: str
    crops: tuple[str, ...]

    @property
    def name(self) -> str:
        if self.kind == "cycle" and len(self.crops) == 1:
            return f"Continuous {self.crops[0].lower()}"
        if self.kind == "cycle":
            return " → ".join(self.crops)
        return "Flexible mix of " + ", ".join(c.lower() for c in self.crops)


def _canonical(cycle: tuple[str, ...]) -> tuple[str, ...]:
    """The same cycle always written the same way: start at winter wheat if present (the
    region's anchor crop), with back-to-back wheat years first ("Winter wheat → Winter wheat →
    Fallow"), otherwise at the alphabetically first rotation."""
    turns = [cycle[i:] + cycle[:i] for i in range(len(cycle))]
    with_wheat = [t for t in turns if t[0] == "Winter wheat"]
    ends_off_wheat = [t for t in with_wheat if t[-1] != "Winter wheat"]
    return min(ends_off_wheat or with_wheat or turns)


def rotation_of(sequence: list[str | None]) -> Rotation | None:
    """A pixel's rotation from its yearly crop groups (None = not cropped that year)."""
    cropped = [g for g in sequence if g is not None]
    if len(cropped) < MIN_CROPPED_YEARS:
        return None
    for period in (1, 2, 3, 4):
        pairs = [(a, b) for a, b in zip(sequence, sequence[period:], strict=False)
                 if a is not None and b is not None]
        if len(pairs) >= 3 and sum(a == b for a, b in pairs) / len(pairs) >= CYCLE_MATCH:
            # Read the cycle from the latest ``period`` consecutive cropped years (a gap year
            # would shift the order); a cycle of one repeated crop is that crop alone.
            for end in range(len(sequence), period - 1, -1):
                window = sequence[end - period:end]
                if None not in window:
                    if len(set(window)) == 1:
                        return Rotation("cycle", (window[0],))
                    return Rotation("cycle", _canonical(tuple(window)))
    top = [crop for crop, _ in Counter(cropped).most_common(3)]
    return Rotation("flexible", tuple(sorted(top)))


def rotation_shares(sequences: list[list[str | None]]) -> dict[Rotation, float]:
    """Each rotation's share of an area's pixels that have a readable rotation."""
    found = [r for r in (rotation_of(s) for s in sequences) if r is not None]
    if not found:
        return {}
    counts = Counter(found)
    return {r: n / len(found) for r, n in counts.most_common() if n / len(found) >= MIN_SHARE}


def _traits_text(rotation: Rotation):
    benefits, risks = [], []
    for crop in dict.fromkeys(rotation.crops):  # unique, in order
        t = TRAITS[crop]
        benefits.append(f"{crop}: {t['benefit']}.")
        risks.append(f"{crop}: {t['risk']}.")
    groups = set(rotation.crops)
    if any(TRAITS[c]["n_fixing"] for c in groups):
        benefits.append("Includes a nitrogen-fixing crop, which can cut fertilizer needs.")
    if len(groups) == 1:
        risks.append("A single crop every year gives pests, diseases and grassy weeds no "
                     "break.")
    if "Fallow" not in groups and all(TRAITS[c]["residue"] != "low" for c in groups):
        benefits.append("Every year leaves crop residue, which protects the soil.")
    return benefits, risks


def strategies(
    field: dict[Rotation, float],
    analogs: dict[int, dict[Rotation, float]],
    models_agree: dict[int, tuple[int, int]],
    years: tuple[int, int] = ROTATION_YEARS,
    minimum: int = 3,
) -> list[RotationStrategy]:
    """The field's current rotation first, then the analog areas' most used rotations.

    ``field``: the field's rotation shares (empty if its pixels show no readable rotation).
    ``analogs``: analog rank -> that area's rotation shares.
    ``models_agree``: analog rank -> (models agreeing, models total), for the evidence text.
    Returns at least ``minimum`` strategies when the analogs show that many rotations.
    """
    checked = len(analogs)
    pooled: Counter = Counter()
    for shares in analogs.values():
        for rotation, share in shares.items():
            pooled[rotation] += share / max(checked, 1)

    current = max(field, key=field.get) if field else None
    order = ([current] if current else []) + [r for r, _ in pooled.most_common() if r != current]
    widely_used = {r for r in order if any(s.get(r, 0.0) >= USED_SHARE for s in analogs.values())}
    # Rotations used widely somewhere come first; if that gives fewer than ``minimum``, rarer
    # ones fill in, labelled as such (the challenge asks for at least three to compare).
    order = ([current] if current else []) + [r for r in order if r != current and r in
                                              widely_used]
    rare = [r for r, _ in pooled.most_common() if r != current and r not in widely_used]
    order += rare[:max(0, minimum - len(order))]
    out = []
    for rotation in order:
        using = [rank for rank, shares in analogs.items()
                 if shares.get(rotation, 0.0) >= USED_SHARE]
        is_current = rotation == current
        share = pooled.get(rotation, 0.0)
        span = f"{years[0]}–{years[1]}"
        if is_current:
            why = (f"Your field's current rotation: {round(100 * field[rotation])}% of its "
                   f"sampled cropland followed it in {span}.")
        else:
            why = (f"Used on {round(100 * share)}% of sampled cropland across the top "
                   f"{checked} analog areas, whose climate today matches your field's 2050s "
                   "climate.")
        evidence = [f"USDA Cropland Data Layer, {span}: {round(100 * share)}% of analog-area "
                    f"cropland; used in {len(using)} of {checked} analog areas."]
        if using:
            agree = [models_agree[r] for r in using if r in models_agree]
            if agree:
                best = max(a for a, _ in agree)
                evidence.append(f"Those analog areas match your 2050s climate in up to {best} "
                                f"of {agree[0][1]} climate models.")
        benefits, risks = _traits_text(rotation)
        gaps = list(ALWAYS_GAPS)
        if not using:
            gaps.insert(0, "None of the top analog areas use this rotation on 10% or more of "
                           "their cropland, so the evidence that it suits your 2050s climate "
                           "is thin.")
        out.append(RotationStrategy(
            name=rotation.name,
            crops=list(rotation.crops),
            flexible=rotation.kind == "flexible",
            current=is_current,
            field_share=round(field[rotation], 3) if rotation in field else None,
            analog_share=round(share, 3),
            analogs_using=len(using),
            analogs_checked=checked,
            why=why,
            evidence=evidence,
            benefits=benefits,
            risks=risks,
            gaps=gaps + [CHECK_LOCALLY],
        ))
        if len(out) >= max(minimum, 4):
            break
    return out


def attach(result: AnalogResult, rotations: list[RotationStrategy]) -> AnalogResult:
    return result.model_copy(update={"rotations": rotations})


# ---------------------------------------------------------------------------
# Earth Engine (needs login and network)
# ---------------------------------------------------------------------------


def fetch_sequences(areas: dict[str, object], years=ROTATION_YEARS, pixels=PIXELS_PER_AREA,
                    seed=0) -> dict[str, list[list[str | None]]]:
    """Per area key -> list of per-pixel yearly crop groups. ``areas`` maps a key to an
    ee.Geometry (built by the caller after ``initialize``)."""
    from farm_analog.earthengine import initialize

    ee = initialize()
    first, last = years
    bands = []
    for year in range(first, last + 1):
        image = (ee.ImageCollection("USDA/NASS/CDL").filterDate(f"{year}-01-01",
                                                                 f"{year + 1}-01-01")
                 .first().select("cropland").rename(f"y{year}"))
        bands.append(image)
    stack = ee.Image.cat(bands)
    out = {}
    for key, region in areas.items():
        features = stack.sample(region=region, scale=30, numPixels=pixels, seed=seed,
                                geometries=False).getInfo()["features"]
        out[key] = [[crop_group(f["properties"].get(f"y{y}")) for y in range(first, last + 1)]
                    for f in features]
    return out


def add_rotations(result: AnalogResult, field_polygon,
                  top: int = ANALOGS_FOR_ROTATIONS) -> AnalogResult:
    """Fetch crop sequences for the field and the top analog areas and attach strategies."""
    from farm_analog.earthengine import field_geometry, initialize

    ee = initialize()
    areas = {"field": field_geometry(ee, field_polygon)}
    for a in result.analogs[:top]:
        areas[f"a{a.rank}"] = ee.Geometry.Point([a.lon, a.lat]).buffer(ANALOG_RADIUS_M)
    sequences = fetch_sequences(areas)
    field = rotation_shares(sequences.pop("field"))
    analogs = {int(k[1:]): rotation_shares(v) for k, v in sequences.items()}
    agree = {a.rank: (a.models_agree, a.models_total) for a in result.analogs[:top]}
    return attach(result, strategies(field, analogs, agree))
