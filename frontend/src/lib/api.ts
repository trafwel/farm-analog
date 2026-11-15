import type { AnalogRequest } from '../types/contract';
import type { AnalogResultView } from '../types/extensions';
import { isAnalogResult } from './validate';

export const API_BASE: string = (import.meta.env.VITE_API_BASE || 'http://localhost:8000').replace(
  /\/+$/,
  '',
);

export type ApiErrorKind = 'network' | 'validation' | 'http' | 'bad_response';

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  /** Plain-language lines to show the user. */
  readonly details: string[];
  readonly status?: number;
  constructor(kind: ApiErrorKind, message: string, details: string[] = [], status?: number) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.details = details;
    this.status = status;
  }
}

const FIELD_NAMES: Record<string, string> = {
  field: 'Field outline',
  coordinates: 'corners',
  scenario: 'Scenario',
  top_n: 'Number of results',
  type: 'shape type',
};

/**
 * Turn a FastAPI/Pydantic 422 `detail` into plain sentences.
 * `detail` is usually [{loc: ["body", "field", "coordinates"], msg: "...", type: "..."}],
 * but may also be a plain string.
 */
export function describeValidationDetail(detail: unknown): string[] {
  if (typeof detail === 'string') return [detail];
  if (!Array.isArray(detail)) return ['The server could not accept this field.'];
  return detail.map((item) => {
    if (item && typeof item === 'object') {
      const { loc, msg } = item as { loc?: unknown; msg?: unknown };
      const where = Array.isArray(loc)
        ? loc
            .filter((p) => p !== 'body' && typeof p === 'string')
            .map((p) => FIELD_NAMES[p as string] ?? String(p))
            .join(', ')
        : '';
      const text = typeof msg === 'string' ? msg.replace(/^Value error, /, '') : 'is not valid';
      return where ? `${where}: ${text}` : text;
    }
    return String(item);
  });
}

async function readJson(res: Response): Promise<unknown> {
  try {
    return await res.json();
  } catch {
    return undefined;
  }
}

export async function fetchAnalogs(
  body: AnalogRequest,
  { base = API_BASE, signal, fetchImpl = fetch }: { base?: string; signal?: AbortSignal; fetchImpl?: typeof fetch } = {},
): Promise<AnalogResultView> {
  let res: Response;
  try {
    res = await fetchImpl(`${base}/analogs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    throw new ApiError('network', `Could not reach the analysis server at ${base}.`);
  }
  const data = await readJson(res);
  if (res.status === 422) {
    const detail = (data as { detail?: unknown } | undefined)?.detail;
    throw new ApiError(
      'validation',
      'The server could not use this field.',
      describeValidationDetail(detail),
      422,
    );
  }
  if (!res.ok) {
    const detail = (data as { detail?: unknown } | undefined)?.detail;
    throw new ApiError(
      'http',
      res.status === 400
        ? 'This field can’t be analyzed.'
        : `The analysis server returned an error (status ${res.status}).`,
      typeof detail === 'string' ? [detail] : [],
      res.status,
    );
  }
  if (!isAnalogResult(data)) {
    throw new ApiError('bad_response', 'The analysis server sent a reply this page does not understand.');
  }
  return data;
}

/** GET /health. Resolves true if the server answers 2xx within the timeout. */
export async function checkHealth(base = API_BASE, timeoutMs = 4000): Promise<boolean> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${base}/health`, { signal: ctrl.signal });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(t);
  }
}

/** Bill's plain-language summary (POST /bill/summary). Not part of the generated contract. */
export interface BillSummary {
  text: string;
  source: 'gemini' | 'template';
  notices: string[];
  error?: string | null;
}

/** Ask Bill to restate a result. Resolves null on any failure: the summary is optional. */
export async function fetchBillSummary(
  result: AnalogResultView,
  { base = API_BASE, signal, fetchImpl = fetch }: { base?: string; signal?: AbortSignal; fetchImpl?: typeof fetch } = {},
): Promise<BillSummary | null> {
  try {
    const res = await fetchImpl(`${base}/bill/summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(result),
      signal,
    });
    if (!res.ok) return null;
    const data = (await readJson(res)) as Partial<BillSummary> | undefined;
    if (!data || typeof data.text !== 'string' || (data.source !== 'gemini' && data.source !== 'template')) {
      return null;
    }
    return { text: data.text, source: data.source, notices: Array.isArray(data.notices) ? data.notices : [] };
  } catch {
    return null;
  }
}
