import { create } from 'zustand';

import { dashboardApi } from '@/data/api/endpoints';
import { getErrorMessage } from '@/data/api/client';
import type { DashboardData } from '@/domain/types';

interface DashboardState {
  data: DashboardData | null;
  isLoading: boolean;
  error: string | null;
  fetchDashboard: () => Promise<void>;
  clearActivities: () => Promise<void>;
  deleteActivity: (refId: string, type: string) => Promise<void>;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  data: null,
  isLoading: false,
  error: null,

  fetchDashboard: async () => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await dashboardApi.get();
      set({ data: data.data, isLoading: false });
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
    }
  },

  clearActivities: async () => {
    try {
      const { data } = await dashboardApi.clearActivities();
      set({ data: data.data });
    } catch (error) {
      set({ error: getErrorMessage(error) });
      throw error;
    }
  },

  deleteActivity: async (refId, type) => {
    try {
      const { data } = await dashboardApi.deleteActivity(refId, type);
      set({ data: data.data });
    } catch (error) {
      set({ error: getErrorMessage(error) });
      throw error;
    }
  },
}));
