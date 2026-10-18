import { useCallback, useEffect, useRef, useState } from 'react';
import type { ApiClient } from '@devorchestrator/api-client';
import { loadReadiness, type ReadinessResult } from './readiness';

export interface ReadinessState {
  loading: boolean;
  /** Last answer; kept while a re-check is running, null before the first one. */
  result: ReadinessResult | null;
  check: () => void;
}

/**
 * Subscribes to the event that should trigger a re-check (window focus on web, app
 * foreground on mobile). Calls `onTrigger` and returns the unsubscribe function.
 */
export type SubscribeToRecheck = (onTrigger: () => void) => () => void;

/**
 * Checks the API readiness on mount, whenever `subscribe` fires and on demand (`check`).
 * No polling. `subscribe` must be a stable reference (declare it at module level).
 */
export function useReadiness(
  client: ApiClient,
  baseUrl: string,
  subscribe: SubscribeToRecheck,
): ReadinessState {
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
    const unsubscribe = subscribe(check);
    return () => {
      unsubscribe();
      controller.current?.abort();
      inFlight.current = false;
    };
  }, [check, subscribe]);

  return { loading, result, check };
}
