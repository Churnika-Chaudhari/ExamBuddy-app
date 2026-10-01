import { create } from 'zustand';

import { dashboardApi } from '@/data/api/endpoints';
import { getErrorMessage } from '@/data/api/client';
import type { DashboardData } from '@/domain/types';
import { readDashboardCache, writeDashboardCache } from '@/utils/dashboardCache';
import { startupApiMark } from '@/utils/startupPerf';

interface DashboardState {
  data: DashboardData | null;
  isLoading: boolean;
  isStale: boolean;
  error: string | null;
  fetchDashboard: () => Promise<void>;
  clearActivities: () => Promise<void>;
  deleteActivity: (refId: string, type: string) => Promise<void>;
  reset: () => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  data: null,
  isLoading: false,
  isStale: false,
  error: null,

  fetchDashboard: async () => {
    if (!get().data) {
      const cached = await readDashboardCache();
      if (cached) {
        set({ data: cached, isLoading: true, isStale: true, error: null });
      } else {
        set({ isLoading: true, error: null });
      }
    } else {
      set({ isLoading: true, isStale: true, error: null });
    }

    const started = Date.now();
    try {
      const { data } = await dashboardApi.get();
      startupApiMark('/dashboard', started);
      set({ data: data.data, isLoading: false, isStale: false, error: null });
      void writeDashboardCache(data.data);
    } catch (error) {
      startupApiMark('/dashboard failed', started);
      set({
        error: getErrorMessage(error),
        isLoading: false,
        isStale: Boolean(get().data),
      });
    }
  },

  reset: () => set({ data: null, isLoading: false, isStale: false, error: null }),

  clearActivities: async () => {
    try {
      const { data } = await dashboardApi.clearActivities();
      set({ data: data.data, isStale: false });
      void writeDashboardCache(data.data);
    } catch (error) {
      set({ error: getErrorMessage(error) });
      throw error;
    }
  },

  deleteActivity: async (refId, type) => {
    try {
      const { data } = await dashboardApi.deleteActivity(refId, type);
      set({ data: data.data, isStale: false });
      void writeDashboardCache(data.data);
    } catch (error) {
      set({ error: getErrorMessage(error) });
      throw error;
    }
  },
}));
