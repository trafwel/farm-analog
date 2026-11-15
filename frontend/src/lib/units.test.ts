import { cToF, deltaCToF, formatPrecip, formatTemp, formatTempChange, mmToInches } from './units';

describe('unit conversion', () => {
  it('converts °C to °F', () => {
    expect(cToF(0)).toBe(32);
    expect(cToF(100)).toBe(212);
    expect(cToF(-40)).toBe(-40);
    expect(cToF(19.4)).toBeCloseTo(66.92, 2);
  });

  it('converts temperature differences without the +32 offset', () => {
    expect(deltaCToF(2.5)).toBeCloseTo(4.5, 10);
    expect(deltaCToF(0)).toBe(0);
  });

  it('converts mm to inches', () => {
    expect(mmToInches(25.4)).toBe(1);
    expect(mmToInches(0)).toBe(0);
    expect(mmToInches(148)).toBeCloseTo(5.83, 2);
  });

  it('formats values in both unit systems', () => {
    expect(formatTemp(2.6)).toBe('2.6 °C (36.7 °F)');
    expect(formatPrecip(148)).toBe('148 mm (5.83 in)');
    expect(formatTempChange(2.5)).toBe('+2.5 °C (+4.5 °F)');
  });
});
