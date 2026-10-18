import { AppState } from 'react-native';
import Constants from 'expo-constants';
import { useReadiness } from '@devorchestrator/shared';
import { StatusView } from '@/components/status-view';
import { API_BASE_URL, apiClient } from '@/lib/api';

/** Re-check when the app comes back to the foreground. */
function onForeground(trigger: () => void) {
  const subscription = AppState.addEventListener('change', (state) => {
    if (state === 'active') trigger();
  });
  return () => subscription.remove();
}

const APP_VERSION = Constants.expoConfig?.version ?? '0.0.0';

export function StatusPage({
  client = apiClient,
  baseUrl = API_BASE_URL,
}: {
  client?: typeof apiClient;
  baseUrl?: string;
}) {
  const { loading, result, check } = useReadiness(client, baseUrl, onForeground);
  return <StatusView loading={loading} result={result} onRetry={check} appVersion={APP_VERSION} />;
}
