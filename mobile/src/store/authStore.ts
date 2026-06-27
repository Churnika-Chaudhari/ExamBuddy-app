import { create } from 'zustand';

import { authApi } from '@/data/api/endpoints';
import { getErrorMessage, tokenStorage } from '@/data/api/client';
import type { User } from '@/domain/types';

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
    try {
      const token = await tokenStorage.getAccessToken();
      if (!token) {
        set({ isInitialized: true });
        return;
      }
      const { data } = await authApi.me();
      set({ user: data.data, isAuthenticated: true, isInitialized: true });
    } catch {
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
