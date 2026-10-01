import { create } from 'zustand';

import { analysisApi } from '@/data/api/endpoints';
import { getErrorMessage } from '@/data/api/client';
import type { PYQAnalysis } from '@/domain/types';
import { pollWithBackoff } from '@/utils/pollWithBackoff';
import { startupDuration, nowMs } from '@/utils/startupPerf';

interface AnalysisState {
  analyses: PYQAnalysis[];
  currentAnalysis: PYQAnalysis | null;
  isLoading: boolean;
  isCreating: boolean;
  error: string | null;
  fetchAnalyses: () => Promise<void>;
  createAnalysis: (documentIds: string[], subject?: string, title?: string) => Promise<PYQAnalysis>;
  fetchAnalysis: (id: string) => Promise<PYQAnalysis>;
  pollAnalysis: (id: string) => Promise<PYQAnalysis>;
}

export const useAnalysisStore = create<AnalysisState>((set, get) => ({
  analyses: [],
  currentAnalysis: null,
  isLoading: false,
  isCreating: false,
  error: null,

  fetchAnalyses: async () => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await analysisApi.list();
      set({ analyses: data.data, isLoading: false });
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
    }
  },

  createAnalysis: async (documentIds, subject, title) => {
    set({ isCreating: true, error: null });
    try {
      const { data } = await analysisApi.create(documentIds, subject, title);
      const analysis = data.data;
      set({
        currentAnalysis: analysis,
        analyses: [analysis, ...get().analyses],
        isCreating: false,
      });
      return analysis;
    } catch (error) {
      set({ error: getErrorMessage(error), isCreating: false });
      throw error;
    }
  },

  fetchAnalysis: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await analysisApi.get(id);
      set({ currentAnalysis: data.data, isLoading: false });
      return data.data;
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
      throw error;
    }
  },

  pollAnalysis: async (id) => {
    const started = nowMs();
    try {
      const analysis = await pollWithBackoff({
        fn: async () => {
          const { data } = await analysisApi.get(id);
          return data.data;
        },
        isDone: (item) => item.status !== 'processing' && item.status !== 'pending',
        intervalsMs: [2000, 3000, 5000, 8000],
        maxAttempts: 40,
        timeoutMs: 180_000,
        onAttempt: (_attempt, item) => {
          set({ currentAnalysis: item });
        },
      });
      startupDuration(`analysis poll ${id}`, started);
      return analysis;
    } catch (error) {
      set({ error: getErrorMessage(error) });
      throw error;
    }
  },
}));
