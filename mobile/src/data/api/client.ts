import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import * as SecureStore from 'expo-secure-store';

import { ENV, isRemoteProductionApi } from '@/core/config/apiConfig';
import type { ApiError, ApiResponse } from '@/domain/types';

const TOKEN_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

export const tokenStorage = {
  async getAccessToken(): Promise<string | null> {
    return SecureStore.getItemAsync(TOKEN_KEY);
  },
  async getRefreshToken(): Promise<string | null> {
    return SecureStore.getItemAsync(REFRESH_KEY);
  },
  async setTokens(access: string, refresh: string): Promise<void> {
    await SecureStore.setItemAsync(TOKEN_KEY, access);
    await SecureStore.setItemAsync(REFRESH_KEY, refresh);
  },
  async clear(): Promise<void> {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    await SecureStore.deleteItemAsync(REFRESH_KEY);
  },
};

function logRequest(config: InternalAxiosRequestConfig) {
  if (!__DEV__) return;
  const method = (config.method ?? 'GET').toUpperCase();
  const url = `${config.baseURL ?? ''}${config.url ?? ''}`;
  // eslint-disable-next-line no-console
  console.log(`[API] → ${method} ${url}`);
}

function logResponse(status: number, config?: InternalAxiosRequestConfig, body?: unknown) {
  if (!__DEV__) return;
  const url = `${config?.baseURL ?? ''}${config?.url ?? ''}`;
  // eslint-disable-next-line no-console
  console.log(`[API] ← ${status} ${url}`, body !== undefined ? body : '');
}

function logError(error: AxiosError) {
  if (!__DEV__) return;
  const method = (error.config?.method ?? 'GET').toUpperCase();
  const url = `${error.config?.baseURL ?? ''}${error.config?.url ?? ''}`;
  // eslint-disable-next-line no-console
  console.warn(`[API] ✗ ${method} ${url}`, {
    code: error.code,
    status: error.response?.status,
    message: error.message,
    data: error.response?.data,
  });
}

export const apiClient = axios.create({
  baseURL: ENV.API_URL,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const token = await tokenStorage.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  logRequest(config);
  return config;
});

let isRefreshing = false;
let refreshQueue: Array<(token: string | null) => void> = [];

const processQueue = (token: string | null) => {
  refreshQueue.forEach((cb) => cb(token));
  refreshQueue = [];
};

apiClient.interceptors.response.use(
  (response) => {
    logResponse(response.status, response.config, response.data);
    return response;
  },
  async (error: AxiosError<ApiError>) => {
    logError(error);
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && original && !original._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshQueue.push((token) => {
            if (!token) {
              reject(error);
              return;
            }
            original.headers.Authorization = `Bearer ${token}`;
            resolve(apiClient(original));
          });
        });
      }

      original._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = await tokenStorage.getRefreshToken();
        if (!refreshToken) throw error;

        const { data } = await axios.post<ApiResponse<{
          access_token: string;
          refresh_token: string;
        }>>(`${ENV.API_URL}/auth/refresh`, { refresh_token: refreshToken });

        const { access_token, refresh_token } = data.data;
        await tokenStorage.setTokens(access_token, refresh_token);
        processQueue(access_token);
        original.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(original);
      } catch (refreshError) {
        processQueue(null);
        await tokenStorage.clear();
        throw refreshError;
      } finally {
        isRefreshing = false;
      }
    }

    throw error;
  }
);

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const ax = error as AxiosError<ApiError>;

    if (ax.code === 'ECONNABORTED' || ax.message.toLowerCase().includes('timeout')) {
      return 'Connection timed out. The backend took too long to respond.';
    }

    if (ax.response?.status === 401) {
      const apiMsg = ax.response.data?.error?.message;
      return apiMsg ?? 'Invalid email or password.';
    }

    if (ax.response?.status === 404) {
      const path = ax.config?.url ?? '';
      if (path.includes('/auth/')) {
        return 'Authentication endpoint not found. Restart the backend with the latest code.';
      }
      return 'API endpoint not found on the server.';
    }

    if (ax.response?.status === 403) {
      return ax.response.data?.error?.message ?? 'Access denied.';
    }

    if (ax.response?.status === 422) {
      return ax.response.data?.error?.message ?? 'Invalid request data.';
    }

    if (ax.response?.status === 500) {
      return ax.response.data?.error?.message ?? 'Server error. Check backend logs.';
    }

    if (ax.code === 'ERR_NETWORK' || ax.message === 'Network Error') {
      return classifyNetworkError(ax);
    }

    const apiError = ax.response?.data as ApiError | undefined;
    return apiError?.error?.message ?? ax.message ?? 'Something went wrong';
  }

  if (error instanceof Error) return error.message;
  return 'Something went wrong';
}

function classifyNetworkError(error: AxiosError): string {
  const target = error.config?.baseURL ?? ENV.API_URL;

  if (isRemoteProductionApi()) {
    return (
      'Cannot reach the exam server. Free hosting may need 30–60 seconds to wake up — ' +
      'check your internet and try again.'
    );
  }

  if (
    (target.includes('localhost') || target.includes('127.0.0.1')) &&
    ENV.RUNTIME_PLATFORM !== 'web' &&
    ENV.RUNTIME_PLATFORM !== 'ios-simulator' &&
    ENV.RUNTIME_PLATFORM !== 'android-emulator'
  ) {
    return 'Invalid API URL for this device. localhost refers to the phone, not your computer.';
  }

  if (ENV.RUNTIME_PLATFORM === 'expo-go' || ENV.RUNTIME_PLATFORM === 'android-device') {
    return `Cannot reach backend at ${target}. Ensure npm run backend is running, your phone and PC are on the same Wi-Fi, and Windows Firewall allows port 8000.`;
  }

  if (ENV.RUNTIME_PLATFORM === 'android-emulator') {
    return 'Backend is not running. Start it with: npm run backend (from project root).';
  }

  return `Cannot reach the backend at ${target}. Start the server: npm run backend --host 0.0.0.0 --port 8000`;
}

export function getErrorDetail(error: unknown): string | null {
  if (!axios.isAxiosError(error)) return null;
  const ax = error as AxiosError<ApiError>;
  if (ax.code === 'ERR_NETWORK') {
    return `Tried: ${ax.config?.baseURL ?? ENV.API_URL}${ax.config?.url ?? ''}`;
  }
  return ax.response?.data?.error?.message ?? null;
}
