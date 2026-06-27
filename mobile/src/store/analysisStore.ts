import { create } from 'zustand';

import { analysisApi } from '@/data/api/endpoints';
import { getErrorMessage } from '@/data/api/client';
import type { PYQAnalysis } from '@/domain/types';

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
    const poll = async (): Promise<PYQAnalysis> => {
      const { data } = await analysisApi.get(id);
      const analysis = data.data;
      set({ currentAnalysis: analysis });
      if (analysis.status === 'processing' || analysis.status === 'pending') {
        await new Promise((r) => setTimeout(r, 3000));
        return poll();
      }
      return analysis;
    };
    return poll();
  },
}));
