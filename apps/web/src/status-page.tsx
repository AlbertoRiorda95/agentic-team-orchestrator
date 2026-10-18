import { useState } from 'react';
import { createApiClient } from '@devorchestrator/api-client';
import { StatusView } from '@/components/status-view';
import { useReadiness } from '@/hooks/use-readiness';

export interface StatusPageProps {
  /** Absolute API base URL; defaults to `/api/v1` on this origin (the Vite proxy in dev). */
  baseUrl?: string;
  /** Custom fetch, for tests. */
  fetch?: typeof globalThis.fetch;
}

function defaultBaseUrl() {
  // openapi-fetch needs an absolute URL; the page also shows it when the API is unreachable.
  return new URL('/api/v1', window.location.origin).href;
}

export function StatusPage({ baseUrl = defaultBaseUrl(), fetch }: StatusPageProps) {
  // The client is created once per mount: baseUrl and fetch do not change at runtime.
  const [client] = useState(() => createApiClient({ baseUrl, fetch }));
  const { loading, result, check } = useReadiness(client, baseUrl);
  return (
    <StatusView loading={loading} result={result} onRetry={check} appVersion={__APP_VERSION__} />
  );
}
