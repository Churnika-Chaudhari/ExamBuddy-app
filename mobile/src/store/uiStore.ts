import { create } from 'zustand';

interface UIState {
  globalLoading: boolean;
  snackbar: { visible: boolean; message: string; type: 'success' | 'error' | 'info' };
  setGlobalLoading: (loading: boolean) => void;
  showSnackbar: (message: string, type?: 'success' | 'error' | 'info') => void;
  hideSnackbar: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  globalLoading: false,
  snackbar: { visible: false, message: '', type: 'info' },

  setGlobalLoading: (loading) => set({ globalLoading: loading }),

  showSnackbar: (message, type = 'info') =>
    set({ snackbar: { visible: true, message, type } }),

  hideSnackbar: () =>
    set((state) => ({ snackbar: { ...state.snackbar, visible: false } })),
}));
