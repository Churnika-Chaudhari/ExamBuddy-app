import { create } from 'zustand';

import { syllabusApi } from '@/data/api/endpoints';
import { getErrorMessage } from '@/data/api/client';
import type { SavedSyllabus } from '@/domain/types';

interface SyllabusState {
  syllabi: SavedSyllabus[];
  isLoading: boolean;
  error: string | null;
  fetchSyllabi: () => Promise<SavedSyllabus[]>;
  deleteSyllabus: (id: string) => Promise<void>;
  findForSubject: (subject: string) => SavedSyllabus | undefined;
}

/** Subject names differ between screens ("DBMS" vs "Database Management
 *  System"), so local lookups compare a punctuation-free lowercase form. The
 *  authoritative alias matching lives on the backend. */
function loosenSubject(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

export const useSyllabusStore = create<SyllabusState>((set, get) => ({
  syllabi: [],
  isLoading: false,
  error: null,

  fetchSyllabi: async () => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await syllabusApi.list();
      const syllabi = data.data.syllabi ?? [];
      set({ syllabi, isLoading: false });
      return syllabi;
    } catch (error) {
      // Home must still render when the syllabus fetch fails.
      set({ error: getErrorMessage(error), isLoading: false });
      return get().syllabi;
    }
  },

  deleteSyllabus: async (id) => {
    try {
      await syllabusApi.delete(id);
      set({ syllabi: get().syllabi.filter((s) => s.id !== id) });
    } catch (error) {
      set({ error: getErrorMessage(error) });
      throw error;
    }
  },

  findForSubject: (subject) => {
    const target = loosenSubject(subject ?? '');
    if (!target) return undefined;
    return get().syllabi.find((s) => loosenSubject(s.subject) === target);
  },
}));
