/** Temperature in °C to °F. */
export function cToF(c: number): number {
  return (c * 9) / 5 + 32;
}

/** A temperature *difference* in °C to °F (no +32 offset). */
export function deltaCToF(dc: number): number {
  return (dc * 9) / 5;
}

export const MM_PER_INCH = 25.4;

/** Precipitation in millimetres to inches. */
export function mmToInches(mm: number): number {
  return mm / MM_PER_INCH;
}

function signed(n: number, digits: number): string {
  const s = n.toFixed(digits);
  return n > 0 ? `+${s}` : s === (-0).toFixed(digits) ? (0).toFixed(digits) : s;
}

export function formatTemp(c: number): string {
  return `${c.toFixed(1)} °C (${cToF(c).toFixed(1)} °F)`;
}

export function formatTempChange(dc: number): string {
  return `${signed(dc, 1)} °C (${signed(deltaCToF(dc), 1)} °F)`;
}

export function formatPrecip(mm: number): string {
  return `${mm.toFixed(0)} mm (${mmToInches(mm).toFixed(2)} in)`;
}

export function formatPrecipChange(dmm: number): string {
  return `${signed(dmm, 0)} mm (${signed(mmToInches(dmm), 2)} in)`;
}
