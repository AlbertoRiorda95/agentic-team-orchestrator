import createClient from 'openapi-fetch';
import type { components, paths } from './schema';

export type { components, paths };

export type Health = components['schemas']['Health'];
export type HealthStatus = components['schemas']['HealthStatus'];
export type CheckStatus = components['schemas']['CheckStatus'];

export interface ApiClientOptions {
  /** Base URL of the API, e.g. `/api/v1` (web, same origin) or `http://localhost:8000/api/v1`. */
  baseUrl: string;
  /** Custom fetch, for tests. */
  fetch?: typeof globalThis.fetch;
}

export function createApiClient({ baseUrl, fetch }: ApiClientOptions) {
  return createClient<paths>({ baseUrl, ...(fetch ? { fetch } : {}) });
}

export type ApiClient = ReturnType<typeof createApiClient>;
