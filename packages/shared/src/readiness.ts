import type { ApiClient, Health } from '@devorchestrator/api-client';

/** The request times out after 10 s and counts as unreachable. */
export const READINESS_TIMEOUT_MS = 10_000;

export interface CheckRow {
  /** Key of the check in `Health.checks`, e.g. `database`. */
  name: string;
  /** Capitalized name for display, e.g. `Database`. */
  label: string;
  ok: boolean;
}

/** What the status page shows once the API answered or failed to answer. */
export type ReadinessResult =
  | {
      kind: 'success' | 'degraded' | 'error';
      checks: CheckRow[];
      /** API version, when the API sent one. */
      version: string | undefined;
    }
  | {
      kind: 'unreachable';
      /** The URL that was tried. */
      url: string;
    };

const HEALTH_STATUSES = new Set(['ok', 'degraded', 'down']);
const CHECK_STATUSES = new Set(['ok', 'failed']);

function isHealth(body: unknown): body is Health {
  if (typeof body !== 'object' || body === null) return false;
  const { status, checks, version } = body as Record<string, unknown>;
  if (typeof status !== 'string' || !HEALTH_STATUSES.has(status)) return false;
  if (version !== undefined && typeof version !== 'string') return false;
  if (checks === undefined) return true;
  if (typeof checks !== 'object' || checks === null) return false;
  return Object.values(checks).every((v) => typeof v === 'string' && CHECK_STATUSES.has(v));
}

function capitalize(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1);
}

/** Failed rows first, then alphabetical. */
export function toCheckRows(checks: Health['checks']): CheckRow[] {
  return Object.entries(checks ?? {})
    .map(([name, status]) => ({ name, label: capitalize(name), ok: status === 'ok' }))
    .sort((a, b) => Number(a.ok) - Number(b.ok) || a.name.localeCompare(b.name));
}

const KIND_BY_STATUS = { ok: 'success', degraded: 'degraded', down: 'error' } as const;

/**
 * Maps an HTTP answer of `GET /health/ready` to the page state. Anything that is not
 * a `Health` body (a proxy error page, a problem+json, a wrong status) is unreachable.
 */
export function mapReadiness(httpStatus: number, body: unknown, url: string): ReadinessResult {
  if ((httpStatus !== 200 && httpStatus !== 503) || !isHealth(body)) {
    return { kind: 'unreachable', url };
  }
  return {
    kind: KIND_BY_STATUS[body.status],
    checks: toCheckRows(body.checks),
    version: body.version,
  };
}

export interface LoadReadinessOptions {
  /** Same base URL the client was created with; only used to tell the user what was tried. */
  baseUrl: string;
  timeoutMs?: number;
  /** Aborts the request, e.g. when the page unmounts. */
  signal?: AbortSignal;
}

/** Calls `readiness` through the generated client. Never throws. */
export async function loadReadiness(
  client: ApiClient,
  { baseUrl, timeoutMs = READINESS_TIMEOUT_MS, signal }: LoadReadinessOptions,
): Promise<ReadinessResult> {
  const url = `${baseUrl.replace(/\/+$/, '')}/health/ready`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const onAbort = () => controller.abort();
  signal?.addEventListener('abort', onAbort);
  try {
    const { data, error, response } = await client.GET('/health/ready', {
      signal: controller.signal,
    });
    return mapReadiness(response.status, data ?? error, url);
  } catch {
    return { kind: 'unreachable', url };
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', onAbort);
  }
}

/** "API 0.1.0+abc1234 · Web 0.1.0"; "API —" when the API version is unknown. */
export function formatVersions(
  apiVersion: string | undefined,
  app: { name: 'Web' | 'Mobile'; version: string },
): string {
  return `API ${apiVersion ?? '—'} · ${app.name} ${app.version}`;
}
