import axios, { AxiosError } from 'axios';

import { ENV } from '@/core/config/apiConfig';

export type HealthStatus = 'checking' | 'connected' | 'offline' | 'timeout' | 'invalid_url' | 'error';

export interface HealthCheckResult {
  status: HealthStatus;
  message: string;
  detail?: string;
  latencyMs?: number;
}

export async function checkBackendHealth(timeoutMs = 8000): Promise<HealthCheckResult> {
  const started = Date.now();

  try {
    const { data, status } = await axios.get(ENV.HEALTH_URL, {
      timeout: timeoutMs,
      validateStatus: () => true,
    });

    const latencyMs = Date.now() - started;

    if (status === 200 && (data?.success === true || data?.data?.status === 'healthy')) {
      return {
        status: 'connected',
        message: 'Backend connected',
        latencyMs,
      };
    }

    if (status === 404) {
      return {
        status: 'error',
        message: 'Health endpoint not found',
        detail: `GET ${ENV.HEALTH_URL} returned 404. Update or restart the backend.`,
        latencyMs,
      };
    }

    return {
      status: 'error',
      message: 'Server responded but health check failed',
      detail: `HTTP ${status} from ${ENV.HEALTH_URL}`,
      latencyMs,
    };
  } catch (error) {
    return mapHealthError(error, Date.now() - started);
  }
}

function mapHealthError(error: unknown, elapsedMs: number): HealthCheckResult {
  if (axios.isAxiosError(error)) {
    const ax = error as AxiosError;

    if (ax.code === 'ECONNABORTED' || ax.message.toLowerCase().includes('timeout')) {
      return {
        status: 'timeout',
        message: 'Connection timed out',
        detail: `No response from ${ENV.HEALTH_URL} within ${elapsedMs}ms. Backend may be offline or blocked by firewall.`,
      };
    }

    if (ax.code === 'ERR_NETWORK' || ax.message === 'Network Error') {
      if (ENV.API_URL.includes('localhost') && ENV.RUNTIME_PLATFORM !== 'web') {
        return {
          status: 'invalid_url',
          message: 'Invalid API URL for this device',
          detail:
            'localhost points to the phone itself, not your computer. Use Expo Go on the same Wi-Fi or an Android emulator.',
        };
      }

      return {
        status: 'offline',
        message: 'Server offline or unreachable',
        detail: `Cannot reach ${ENV.HEALTH_URL}. Start backend: npm run backend. Ensure phone and PC share the same Wi-Fi.`,
      };
    }

    return {
      status: 'error',
      message: 'Network error',
      detail: ax.message,
    };
  }

  return {
    status: 'error',
    message: 'Health check failed',
    detail: error instanceof Error ? error.message : String(error),
  };
}
