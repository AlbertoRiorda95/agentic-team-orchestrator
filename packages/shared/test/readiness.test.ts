import { describe, expect, it } from 'vitest';
import { createApiClient } from '@devorchestrator/api-client';
import { formatVersions, loadReadiness, mapReadiness } from '../src/index';

const BASE = 'http://api.test/api/v1';
const URL_TRIED = `${BASE}/health/ready`;

function clientAnswering(respond: () => Response | Promise<Response>) {
  return createApiClient({ baseUrl: BASE, fetch: async () => respond() });
}

describe('mapReadiness', () => {
  it('maps ok to success with the checks and the version', () => {
    expect(
      mapReadiness(
        200,
        { status: 'ok', checks: { database: 'ok' }, version: '0.1.0+abc1234' },
        URL_TRIED,
      ),
    ).toEqual({
      kind: 'success',
      checks: [{ name: 'database', label: 'Database', ok: true }],
      version: '0.1.0+abc1234',
    });
  });

  it('maps degraded to degraded', () => {
    expect(mapReadiness(200, { status: 'degraded', checks: {} }, URL_TRIED).kind).toBe('degraded');
  });

  it('maps a 503 with status down to error, failed checks first', () => {
    const result = mapReadiness(
      503,
      { status: 'down', checks: { cache: 'ok', database: 'failed' } },
      URL_TRIED,
    );
    expect(result).toEqual({
      kind: 'error',
      checks: [
        { name: 'database', label: 'Database', ok: false },
        { name: 'cache', label: 'Cache', ok: true },
      ],
      version: undefined,
    });
  });

  it.each([
    ['a 500', 500, { type: 'about:blank', title: 'Internal Server Error', status: 500 }],
    ['a 404', 404, { type: 'about:blank', title: 'Not Found', status: 404 }],
    ['an HTML error page', 503, '<html>Bad gateway</html>'],
    ['an unknown status value', 200, { status: 'weird' }],
    ['an unknown check value', 200, { status: 'ok', checks: { database: 'maybe' } }],
    ['no body', 200, undefined],
  ])('maps %s to unreachable with the URL tried', (_label, status, body) => {
    expect(mapReadiness(status, body, URL_TRIED)).toEqual({ kind: 'unreachable', url: URL_TRIED });
  });
});

describe('loadReadiness', () => {
  it('reads a 200 through the client', async () => {
    const client = clientAnswering(() =>
      Response.json({ status: 'ok', checks: { database: 'ok' } }),
    );
    const result = await loadReadiness(client, { baseUrl: BASE });
    expect(result.kind).toBe('success');
  });

  it('reads the Health body of a 503 as error', async () => {
    const client = clientAnswering(() =>
      Response.json({ status: 'down', checks: { database: 'failed' } }, { status: 503 }),
    );
    const result = await loadReadiness(client, { baseUrl: `${BASE}/` });
    expect(result.kind).toBe('error');
  });

  it('treats a network error as unreachable', async () => {
    const client = clientAnswering(() => {
      throw new TypeError('fetch failed');
    });
    expect(await loadReadiness(client, { baseUrl: BASE })).toEqual({
      kind: 'unreachable',
      url: URL_TRIED,
    });
  });

  it('treats a request that outlives the timeout as unreachable', async () => {
    const client = createApiClient({
      baseUrl: BASE,
      fetch: (input) =>
        new Promise((_resolve, reject) => {
          (input as Request).signal.addEventListener('abort', () =>
            reject(new DOMException('Aborted', 'AbortError')),
          );
        }),
    });
    expect(await loadReadiness(client, { baseUrl: BASE, timeoutMs: 20 })).toEqual({
      kind: 'unreachable',
      url: URL_TRIED,
    });
  });
});

describe('formatVersions', () => {
  it('joins the API and app versions', () => {
    expect(formatVersions('0.1.0+abc1234', { name: 'Web', version: '0.1.0' })).toBe(
      'API 0.1.0+abc1234 · Web 0.1.0',
    );
  });

  it('shows a dash when the API version is unknown', () => {
    expect(formatVersions(undefined, { name: 'Mobile', version: '0.1.0' })).toBe(
      'API — · Mobile 0.1.0',
    );
  });
});
