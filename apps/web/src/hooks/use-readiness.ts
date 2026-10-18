import { useCallback, useEffect, useRef, useState } from 'react';
import type { ApiClient } from '@devorchestrator/api-client';
import { loadReadiness, type ReadinessResult } from '@devorchestrator/shared';

export interface ReadinessState {
  loading: boolean;
  /** Last answer; kept while a re-check is running, null before the first one. */
  result: ReadinessResult | null;
  check: () => void;
}

/**
 * Checks the API readiness on mount, on window focus and on demand (`check`).
 * No polling.
 */
export function useReadiness(client: ApiClient, baseUrl: string): ReadinessState {
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<ReadinessResult | null>(null);
  const inFlight = useRef(false);
  const controller = useRef<AbortController | null>(null);

  const check = useCallback(() => {
    if (inFlight.current) return;
    inFlight.current = true;
    setLoading(true);
    const abort = new AbortController();
    controller.current = abort;
    void loadReadiness(client, { baseUrl, signal: abort.signal }).then((next) => {
      if (abort.signal.aborted || controller.current !== abort) return;
      inFlight.current = false;
      setResult(next);
      setLoading(false);
    });
  }, [client, baseUrl]);

  useEffect(() => {
    check();
    window.addEventListener('focus', check);
    return () => {
      window.removeEventListener('focus', check);
      controller.current?.abort();
      inFlight.current = false;
    };
  }, [check]);

  return { loading, result, check };
}
