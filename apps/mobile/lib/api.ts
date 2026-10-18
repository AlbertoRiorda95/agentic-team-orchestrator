import { createApiClient } from '@devorchestrator/api-client';

/**
 * Base URL of the API. Android emulator: http://10.0.2.2:8000/api/v1; a device: the host's
 * LAN or Tailscale address (see .env.example).
 */
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

export const apiClient = createApiClient({ baseUrl: API_BASE_URL });
