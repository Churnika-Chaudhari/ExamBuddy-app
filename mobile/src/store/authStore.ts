import { create } from 'zustand';

import { authApi } from '@/data/api/endpoints';
import { getErrorMessage, tokenStorage } from '@/data/api/client';
import type { User } from '@/domain/types';
import { startupMark } from '@/utils/startupPerf';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitialized: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  initialize: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  isInitialized: false,
  error: null,

  clearError: () => set({ error: null }),

  initialize: async () => {
    startupMark('TOKEN LOADING STARTED');
    try {
      const token = await tokenStorage.getAccessToken();
      startupMark('TOKEN LOADED');
      if (!token) {
        set({ isInitialized: true, isAuthenticated: false, user: null });
        return;
      }

      // Stored token is enough to enter the app. /auth/me can lag on a cold
      // Render start and must not keep the splash screen open.
      set({ isAuthenticated: true, isInitialized: true });
      const meStarted = Date.now();
      void authApi
        .me()
        .then(({ data }) => {
          startupMark(`API /auth/me done in ${Date.now() - meStarted}ms (background)`);
          set({ user: data.data, isAuthenticated: true });
        })
        .catch(async () => {
          startupMark(`API /auth/me failed in ${Date.now() - meStarted}ms (background)`);
          await tokenStorage.clear();
          set({ user: null, isAuthenticated: false });
        });
    } catch {
      startupMark('TOKEN LOADED');
      await tokenStorage.clear();
      set({ user: null, isAuthenticated: false, isInitialized: true });
    }
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await authApi.login(email, password);
      await tokenStorage.setTokens(data.data.access_token, data.data.refresh_token);
      set({ user: data.data.user, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
      throw error;
    }
  },

  register: async (email, password, fullName) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await authApi.register(email, password, fullName);
      await tokenStorage.setTokens(data.data.access_token, data.data.refresh_token);
      set({ user: data.data.user, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
      throw error;
    }
  },

  logout: async () => {
    await tokenStorage.clear();
    set({ user: null, isAuthenticated: false, error: null });
  },
}));
