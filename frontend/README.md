# farm-analog frontend (M6)

Single-page map app: draw your field, pick an emissions scenario, and see places in the
US Pacific Northwest whose climate today matches your field's projected ~2050 climate.

Stack: Vite + React 18 + TypeScript, Leaflet / react-leaflet, Geoman (drawing), Vitest, ESLint. Package manager: pnpm.

## Run

```sh
pnpm install
pnpm dev            # http://localhost:5173
```

The app calls the backend at `VITE_API_BASE` (default `http://localhost:8000`):
`POST /analogs` and `GET /health`. To point elsewhere, copy `.env.example` to `.env.local`
and set `VITE_API_BASE`. `VITE_` variables are bundled into the public page, so never put
secrets there (none are needed).

No backend? Click **Show demo data** (also offered whenever a request fails). It loads the
bundled fixture `src/fixtures/fake_results.json` (`fake-colfax` normal case, with a toggle
for the `fake-lind` novel-climate case) and shows a "Demo data — not a real analysis" banner.

## Scripts

| Script | What it does |
|---|---|
| `pnpm dev` | Vite dev server |
| `pnpm build` | Type-check, then production build to `dist/` |
| `pnpm typecheck` | `tsc --noEmit` |
| `pnpm lint` | ESLint (typescript-eslint + react-hooks) |
| `pnpm test` | Vitest, single run (no watch) |
| `pnpm gen:types` | Regenerate `src/types/contract.ts` from the repo's `../contract/*.schema.json` |

## Contract types

Types are generated from the repo's `contract/analog_request.schema.json` and
`contract/analog_result.schema.json` (the backend's Pydantic-generated JSON Schema; no copies).
When the backend contract changes, run `pnpm gen:types` and commit `src/types/contract.ts`;
CI fails if the committed file is out of date (script: `scripts/gen-types.mjs`, using
`json-schema-to-typescript`).

**About `prefixItems`:** Pydantic emits JSON Schema 2020-12, where fixed-length tuples are
`prefixItems: [...]`. `json-schema-to-typescript` only understands the draft-07 tuple form
(`items: [...]`), so unpatched it generates `baseline_years: [unknown, unknown]` (same for
`future_years` and GeoJSON `[lon, lat]` positions). The script rewrites every
`prefixItems` to `items` (+ `additionalItems: false`) before compiling, which yields
`BaselineYears = [number, number]`, `FutureYears = [number, number]` and
`[number, number]` positions. The script fails if any `[unknown, unknown]` remains.

The contract's optional `notes: string[]` (caveats about how a result was produced) is shown
as "About this result" when present.

## Layout

- `src/lib/` — pure logic: request builder (`[lon, lat]`, closed ring), API client and 422
  messages, match-quality colours, unit conversion, headline/novel-climate logic, fixture loading.
- `src/components/` — `MapView` (Leaflet + Geoman), `ResultsPanel` (headline, accessible text
  list, metadata, notes), `FingerprintTable`, `Legend`.
- Accessibility: all controls are keyboard-usable buttons/selects with labels; the results text
  list is the non-map alternative (selecting an item pans to and highlights its marker);
  "Use example field" lets you run everything without drawing.
