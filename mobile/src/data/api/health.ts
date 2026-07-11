import axios, { AxiosError } from 'axios';

import {
  ENV,
  getHealthCheckAttempts,
  getHealthCheckTimeoutMs,
  isRemoteProductionApi,
} from '@/core/config/apiConfig';

export type HealthStatus = 'checking' | 'connected' | 'offline' | 'timeout' | 'invalid_url' | 'error';

export interface HealthCheckResult {
  status: HealthStatus;
  message: string;
  detail?: string;
  latencyMs?: number;
}

function remoteUnreachableDetail(): string {
  return (
    'The exam server may be waking up (free hosting can take 30–60 seconds). ' +
    'Check your internet connection, wait a moment, then tap Retry.'
  );
}

function devUnreachableDetail(): string {
  return (
    `Cannot reach ${ENV.HEALTH_URL}. Start the backend from the project root: npm run backend. ` +
    'Ensure your phone and PC share the same Wi-Fi.'
  );
}

function unreachableDetail(): string {
  return isRemoteProductionApi() ? remoteUnreachableDetail() : devUnreachableDetail();
}

async function sleep(ms: number): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function checkBackendHealthOnce(timeoutMs: number): Promise<HealthCheckResult> {
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
        detail: isRemoteProductionApi()
          ? 'The deployed API is missing /health. Redeploy the latest backend on Render.'
          : `GET ${ENV.HEALTH_URL} returned 404. Update or restart the backend.`,
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

export async function checkBackendHealth(timeoutMs?: number): Promise<HealthCheckResult> {
  const effectiveTimeout = timeoutMs ?? getHealthCheckTimeoutMs();
  const attempts = getHealthCheckAttempts();
  let lastResult: HealthCheckResult | null = null;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    lastResult = await checkBackendHealthOnce(effectiveTimeout);
    if (lastResult.status === 'connected') {
      return lastResult;
    }
    if (attempt < attempts) {
      await sleep(3000);
    }
  }

  return lastResult ?? {
    status: 'error',
    message: 'Health check failed',
    detail: unreachableDetail(),
  };
}

function mapHealthError(error: unknown, elapsedMs: number): HealthCheckResult {
  if (axios.isAxiosError(error)) {
    const ax = error as AxiosError;

    if (ax.code === 'ECONNABORTED' || ax.message.toLowerCase().includes('timeout')) {
      return {
        status: 'timeout',
        message: isRemoteProductionApi() ? 'Server is waking up' : 'Connection timed out',
        detail: isRemoteProductionApi()
          ? `No response within ${Math.round(elapsedMs / 1000)}s. ${remoteUnreachableDetail()}`
          : `No response from ${ENV.HEALTH_URL} within ${elapsedMs}ms. Backend may be offline.`,
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
        message: isRemoteProductionApi() ? 'Cannot reach exam server' : 'Server offline or unreachable',
        detail: unreachableDetail(),
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
