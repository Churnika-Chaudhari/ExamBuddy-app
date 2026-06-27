import { create } from 'zustand';

import { checkBackendHealth, type HealthCheckResult, type HealthStatus } from '@/data/api/health';
import { ENV } from '@/core/config/apiConfig';

interface NetworkState {
  healthStatus: HealthStatus;
  healthMessage: string;
  healthDetail: string | null;
  latencyMs: number | null;
  lastCheckedAt: number | null;
  isChecking: boolean;
  runHealthCheck: () => Promise<HealthCheckResult>;
}

export const useNetworkStore = create<NetworkState>((set) => ({
  healthStatus: 'checking',
  healthMessage: 'Checking backend…',
  healthDetail: null,
  latencyMs: null,
  lastCheckedAt: null,
  isChecking: false,

  runHealthCheck: async () => {
    set({ isChecking: true, healthStatus: 'checking', healthMessage: 'Checking backend…' });

    const result = await checkBackendHealth();

    set({
      isChecking: false,
      healthStatus: result.status,
      healthMessage: result.message,
      healthDetail: result.detail ?? null,
      latencyMs: result.latencyMs ?? null,
      lastCheckedAt: Date.now(),
    });

    if (__DEV__) {
      // eslint-disable-next-line no-console
      console.log(
        `[SmartStudy] Health: ${result.status} — ${result.message}`,
        result.detail ?? '',
        `(${ENV.API_URL})`
      );
    }

    return result;
  },
}));
