# The JSON Contract

What the backend sends and receives, in plain words. The source of truth is
[`src/farm_analog/schema.py`](../src/farm_analog/schema.py); the machine-readable versions are in
[`contract/`](../contract/) (JSON Schema, used to generate the frontend's TypeScript types in M6).

**Units everywhere:** temperatures in °C, precipitation in mm, coordinates as `[longitude, latitude]` (GeoJSON order, longitude first).

## Request: `AnalogRequest`

| Field | Type | Notes |
|---|---|---|
| `field` | GeoJSON Polygon | The drawn field. Rings must be closed (first point = last point), at least 4 points, at most 1,000 vertices in total |
| `scenario` | `"ssp245"` or `"ssp585"` | Default `"ssp245"` |
| `top_n` | integer, 1–100 | How many analogs to return. Default 20 |

Unknown fields are rejected, so typos fail loudly instead of being ignored.

## Response: `AnalogResult`

| Field | Meaning |
|---|---|
| `source` | `"computed"` (real results) or `"fixture"` (fake demo data; the UI must say so) |
| `field_id` | Which field this is |
| `scenario`, `baseline_years`, `future_years` | The settings used, for example `"ssp245"`, `[1995, 2014]`, `[2041, 2060]` (IPCC AR6 periods) |
| `models` | Names of the climate models used |
| `farm_today`, `farm_future` | The farm's 8-number climate fingerprint now and in the future |
| `farm_soil` | The farm's soil summary (optional) |
| `novel_climate` | `true` when even the best analog has sigma of 4 or more: no real match exists today |
| `analogs` | List of matches, best first |

**The fingerprint** (`SeasonalFingerprint`) is 8 numbers: average temperature (`tmean_`, °C) and total precipitation (`ppt_`, mm) for each calendar quarter: `jfm` (Jan–Mar), `amj` (Apr–Jun), `jas` (Jul–Sep), `ond` (Oct–Dec). The definition lives in [`src/farm_analog/fingerprint.py`](../src/farm_analog/fingerprint.py) and is shared by the farm, the candidates and the future climate. (Changed in M1 from 12 seasonal highs, lows and rain, to match the team's working search.)

### Each analog

| Field | Meaning |
|---|---|
| `rank` | 1 = best match |
| `lon`, `lat`, `place_name` | Where it is |
| `sigma` | How different it is, in units of the farm's normal year-to-year swings (median across models). Lower is better |
| `match_quality` | `strong` (below 1), `good` (1–2), `weak` (2–4), `none` (4 or more). Always consistent with `sigma` |
| `models_agree` / `models_total` | How many climate models call this a good analog |
| `fingerprint` | The analog's climate today, to compare with `farm_future` |
| `crops` | Share of cropland in each crop (optional until M7) |
| `soil` | Soil summary (optional until M7) |
| `climograph` | Monthly mean temperature (`tmean`) and precipitation (`ppt`) for the comparison chart: farm today, farm future, analog today (optional until M7) |

**Map colors (M6):** shade analogs by `match_quality`, darkest blue for `strong` to lightest for `weak`; draw the farm polygon in green.

## Fake data

[`fixtures/fake_results.json`](../fixtures/fake_results.json) has two fake results that follow the contract:

- `fake-colfax`: a normal case with 20 analogs (the top 3 include crops, soil and a climograph).
- `fake-lind`: a novel-climate case, for building the warning.

Regenerate it with `python scripts/make_fake_results.py`. If you change the contract, also run `python scripts/export_contract.py`; tests fail if either file is out of date.
