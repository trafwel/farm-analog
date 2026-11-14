What's up? It's us. The farm guys

Farming it so hard rn

## Import NASA SMAP soil moisture

A small, real Palouse sample is included in `data/samples/`: July 1–7, 2025,
with 56 three-hour readings of regional surface and root-zone moisture.
The CSV and matching provenance JSON can be used without Earth Engine sign-in.
Only small CSV/JSON samples are allowed through Git's data ignore rules;
bulk downloads remain ignored.

The importer downloads SMAP L4 v8 surface (0–5 cm) and root-zone (0–100 cm)
soil moisture, averaged over an approximate Washington Palouse bounding box.
It saves a CSV and provenance JSON in `data/smap/` (gitignored).

Activate the environment described in SETUP.md, set `EE_PROJECT` in `.env`,
then run:

```bash
earthengine authenticate
PYTHONPATH=src python -m farm_analog.data --start 2025-07-01 --end 2025-07-08
```

The end date is exclusive. Override the region with
`--bounds WEST SOUTH EAST NORTH`; requests are limited to 366 days.
The default is a historical one-week sample, not live conditions.

Each row represents a three-hour timestamp, with regional mean moisture in
m³/m³ and valid-pixel counts. Missing values remain empty. SMAP L4 combines
satellite observations with a land model on a native 9 km grid; Earth Engine
reprojects it and lists approximately 11 km pixels. These are regional estimates,
not measurements of individual fields or projections for 2050.

Source: [NASA SMAP L4 v8 on Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/NASA_SMAP_SPL4SMGP_008).
DOI: [10.5067/T5RUATAQREF8](https://doi.org/10.5067/T5RUATAQREF8).

## First 2050 climate comparison

Run `PYTHONPATH=src python -m farm_analog.climate` after Earth Engine setup.
This downloads monthly Palouse summaries for ACCESS-CM2: a 1995–2014 historical
model baseline and a 2041–2060 projection under SSP2-4.5. Small CSV/JSON outputs
are saved in `data/samples/`. This first prototype uses one model, not an ensemble.
The baseline is modeled climate, not observed weather. Temperature is converted
from kelvin to Celsius; precipitation flux is integrated into mean monthly totals
in millimetres. Both periods must contain complete, unique daily timestamps.
