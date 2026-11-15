// Generate src/types/contract.ts from the backend's JSON Schema files in the repo's contract/ folder.
//
// Pydantic emits JSON Schema 2020-12, where fixed-length tuples are written as
// `prefixItems: [...]`. json-schema-to-typescript only understands the older draft-07
// tuple form (`items: [...]`), so out of the box it emits `[unknown, unknown]` for
// `baseline_years`, `future_years` and the GeoJSON `[lon, lat]` positions.
// We therefore rewrite every `prefixItems` into the draft-07 form before compiling:
//   { prefixItems: P, items?: X }  ->  { items: P, additionalItems: X ?? false }
// (minItems/maxItems are kept, so the result is an exact tuple like [number, number]).
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { compile } from 'json-schema-to-typescript';

const SCHEMAS = [
  ['../contract/analog_request.schema.json', 'AnalogRequest'],
  ['../contract/analog_result.schema.json', 'AnalogResult'],
];
const OUT = 'src/types/contract.ts';

export function prefixItemsToDraft7(node) {
  if (Array.isArray(node)) return node.map(prefixItemsToDraft7);
  if (node === null || typeof node !== 'object') return node;
  const out = {};
  for (const [k, v] of Object.entries(node)) out[k] = prefixItemsToDraft7(v);
  if (Array.isArray(out.prefixItems)) {
    const rest = out.items;
    out.items = out.prefixItems;
    out.additionalItems = rest === undefined ? false : rest;
    delete out.prefixItems;
  }
  return out;
}

const parts = [
  '/* eslint-disable */',
  '/**',
  ' * GENERATED FILE - do not edit by hand. Run `pnpm gen:types` to regenerate.',
  ' * Source: contract/*.schema.json (Pydantic, JSON Schema 2020-12), with',
  ' * `prefixItems` tuples rewritten to draft-07 `items` arrays (see scripts/gen-types.mjs).',
  ' */',
  '',
];
const seen = new Set();
for (const [file, name] of SCHEMAS) {
  const schema = prefixItemsToDraft7(JSON.parse(await readFile(file, 'utf8')));
  let ts = await compile(schema, name, {
    bannerComment: '',
    additionalProperties: false,
    strictIndexSignatures: true,
    format: true,
  });
  // Both schemas are compiled separately; drop declarations already emitted (e.g. `Scenario`).
  ts = ts
    .split(/\n(?=export )/)
    .filter((block) => {
      const m = block.match(/^export (?:type|interface) (\w+)/);
      if (!m) return true;
      if (seen.has(m[1])) return false;
      seen.add(m[1]);
      return true;
    })
    .join('\n');
  parts.push(`// ---- ${name} (${file}) ----`, ts.trim(), '');
}
// Guard: fail loudly if any tuple still came out as unknown.
const result = parts.join('\n');
if (/\[unknown, unknown\]/.test(result)) {
  throw new Error('gen:types: a tuple was generated as [unknown, unknown]; check prefixItems handling');
}
await mkdir('src/types', { recursive: true });
await writeFile(OUT, result);
console.log(`gen:types: wrote ${OUT}`);
