import type { Analog, SeasonalFingerprint } from '../types/contract';
import type { AnalogResultView } from '../types/extensions';

const FP_KEYS: (keyof SeasonalFingerprint)[] = [
  'tmean_jfm',
  'tmean_amj',
  'tmean_jas',
  'tmean_ond',
  'ppt_jfm',
  'ppt_amj',
  'ppt_jas',
  'ppt_ond',
];
const QUALITIES = ['strong', 'good', 'weak', 'none'];

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null;
const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const isYears = (v: unknown) => Array.isArray(v) && v.length === 2 && v.every(isNum);

export function isFingerprint(v: unknown): v is SeasonalFingerprint {
  return isObj(v) && FP_KEYS.every((k) => isNum(v[k]));
}

export function isAnalog(v: unknown): v is Analog {
  return (
    isObj(v) &&
    isNum(v.rank) &&
    isNum(v.lon) &&
    isNum(v.lat) &&
    isNum(v.sigma) &&
    typeof v.match_quality === 'string' &&
    QUALITIES.includes(v.match_quality) &&
    isNum(v.models_agree) &&
    isNum(v.models_total) &&
    isFingerprint(v.fingerprint)
  );
}

/**
 * Light runtime check of the fields the UI relies on (not a full schema validation;
 * the backend validates with Pydantic before sending).
 */
export function isAnalogResult(v: unknown): v is AnalogResultView {
  return (
    isObj(v) &&
    (v.source === 'computed' || v.source === 'fixture') &&
    typeof v.field_id === 'string' &&
    (v.scenario === 'ssp245' || v.scenario === 'ssp585') &&
    isYears(v.baseline_years) &&
    isYears(v.future_years) &&
    Array.isArray(v.models) &&
    isFingerprint(v.farm_today) &&
    isFingerprint(v.farm_future) &&
    typeof v.novel_climate === 'boolean' &&
    Array.isArray(v.analogs) &&
    v.analogs.every(isAnalog) &&
    (v.notes === undefined || v.notes === null || (Array.isArray(v.notes) && v.notes.every((n) => typeof n === 'string')))
  );
}
