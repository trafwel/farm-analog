import { ApiError, describeValidationDetail, fetchAnalogs } from './api';
import { getDemoResult } from './fixtures';
import { buildAnalogRequest, EXAMPLE_FIELD } from './request';

const body = buildAnalogRequest(EXAMPLE_FIELD, 'ssp245');
const jsonResponse = (status: number, data: unknown) =>
  new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });

describe('API client', () => {
  it('POSTs to {base}/analogs and returns the parsed result', async () => {
    const fake = vi.fn(async () => jsonResponse(200, getDemoResult('fake-colfax')));
    const r = await fetchAnalogs(body, { base: 'http://api.test', fetchImpl: fake as unknown as typeof fetch });
    expect(r.field_id).toBe('fake-colfax');
    const [url, init] = fake.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('http://api.test/analogs');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual(body);
  });

  it('turns a 422 into plain-language validation messages', async () => {
    const detail = [{ loc: ['body', 'field', 'coordinates'], msg: 'Value error, ring must be closed', type: 'value_error' }];
    const fake = async () => jsonResponse(422, { detail });
    const err = await fetchAnalogs(body, { fetchImpl: fake as typeof fetch }).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.kind).toBe('validation');
    expect(err.details).toEqual(['Field outline, corners: ring must be closed']);
  });

  it('reports an unreachable server as a network error', async () => {
    const fake = async () => {
      throw new TypeError('Failed to fetch');
    };
    const err = await fetchAnalogs(body, { fetchImpl: fake as typeof fetch }).catch((e) => e);
    expect(err.kind).toBe('network');
  });

  it('reports other HTTP errors with their status', async () => {
    const fake = async () => jsonResponse(500, { detail: 'boom' });
    const err = await fetchAnalogs(body, { fetchImpl: fake as typeof fetch }).catch((e) => e);
    expect(err.kind).toBe('http');
    expect(err.status).toBe(500);
  });

  it('handles a string detail', () => {
    expect(describeValidationDetail('Too many vertices')).toEqual(['Too many vertices']);
  });
});
