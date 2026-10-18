import { describe, expect, it } from 'vitest';
import { createApiClient } from '../src/index';

describe('createApiClient', () => {
  it('calls GET /health/ready under the base URL and returns the typed body', async () => {
    const seen: string[] = [];
    const client = createApiClient({
      baseUrl: 'http://api.test/api/v1',
      fetch: async (input) => {
        seen.push((input as Request).url);
        return Response.json({
          status: 'ok',
          checks: { database: 'ok' },
          version: '0.1.0+abc1234',
        });
      },
    });

    const { data, error, response } = await client.GET('/health/ready');

    expect(seen).toEqual(['http://api.test/api/v1/health/ready']);
    expect(response.status).toBe(200);
    expect(error).toBeUndefined();
    expect(data?.status).toBe('ok');
    expect(data?.checks?.database).toBe('ok');
  });

  it('returns the Health body as the error of a 503', async () => {
    const client = createApiClient({
      // openapi-fetch builds a Request, which needs an absolute URL outside a browser
      baseUrl: 'http://api.test/api/v1',
      fetch: async () =>
        Response.json({ status: 'down', checks: { database: 'failed' } }, { status: 503 }),
    });

    const { data, error } = await client.GET('/health/ready');

    expect(data).toBeUndefined();
    expect(error?.status).toBe('down');
  });
});
