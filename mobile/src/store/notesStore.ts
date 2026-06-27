import { create } from 'zustand';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';

import { notesApi } from '@/data/api/endpoints';
import { getErrorMessage, tokenStorage } from '@/data/api/client';
import type { GeneratedTopicNote, Note } from '@/domain/types';

export interface TopicNoteParams {
  topic: string;
  analysisId?: string;
  subject?: string;
  unit?: string;
  frequency?: number;
  regenerate?: boolean;
}

interface NotesState {
  notes: Note[];
  selectedNote: Note | null;
  topicNote: GeneratedTopicNote | null;
  cachedTopicKeys: string[];
  isLoading: boolean;
  isGenerating: boolean;
  isExporting: boolean;
  error: string | null;
  fetchNotes: () => Promise<void>;
  fetchNote: (id: string) => Promise<Note>;
  generateNotes: (analysisId: string, topics?: string[]) => Promise<Note>;
  simplifyNotes: (documentId: string) => Promise<Note>;
  exportNotePdf: (noteId: string) => Promise<string>;
  generateTopicNotes: (params: TopicNoteParams) => Promise<GeneratedTopicNote>;
  regenerateTopicNotes: (params: TopicNoteParams) => Promise<GeneratedTopicNote>;
  saveTopicNotes: (noteId: string, isSaved: boolean) => Promise<GeneratedTopicNote>;
  exportTopicNotePdf: (noteId: string) => Promise<string>;
  fetchCachedTopics: (analysisId: string) => Promise<string[]>;
  clearTopicNote: () => void;
  clearNotes: () => Promise<number>;
}

export const useNotesStore = create<NotesState>((set, get) => ({
  notes: [],
  selectedNote: null,
  topicNote: null,
  cachedTopicKeys: [],
  isLoading: false,
  isGenerating: false,
  isExporting: false,
  error: null,

  fetchNotes: async () => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await notesApi.list();
      set({ notes: data.data, isLoading: false });
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
    }
  },

  fetchNote: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await notesApi.get(id);
      set({ selectedNote: data.data, isLoading: false });
      return data.data;
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
      throw error;
    }
  },

  generateNotes: async (analysisId, topics) => {
    set({ isGenerating: true, error: null });
    try {
      const { data } = await notesApi.generate({ analysis_id: analysisId, topics });
      const note = data.data as Note;
      set({
        notes: [note, ...get().notes],
        selectedNote: note,
        isGenerating: false,
      });
      return note;
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false, isGenerating: false });
      throw error;
    }
  },

  simplifyNotes: async (documentId) => {
    set({ isGenerating: true, error: null });
    try {
      const { data } = await notesApi.simplify({ document_id: documentId });
      const note = data.data;
      set({
        notes: [note, ...get().notes],
        selectedNote: note,
        isGenerating: false,
      });
      return note;
    } catch (error) {
      set({ error: getErrorMessage(error), isGenerating: false });
      throw error;
    }
  },

  exportNotePdf: async (noteId) => {
    set({ isExporting: true, error: null });
    try {
      const token = await tokenStorage.getAccessToken();
      const fileUri = `${FileSystem.cacheDirectory}note-${noteId}.pdf`;
      const download = await FileSystem.downloadAsync(
        notesApi.exportPdfUrl(noteId),
        fileUri,
        token ? { headers: { Authorization: `Bearer ${token}` } } : undefined
      );

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(download.uri, {
          mimeType: 'application/pdf',
          dialogTitle: 'Share study notes PDF',
        });
      }

      set({ isExporting: false });
      return download.uri;
    } catch (error) {
      set({ error: getErrorMessage(error), isExporting: false });
      throw error;
    }
  },

  generateTopicNotes: async (params) => {
    set({ isGenerating: true, error: null });
    try {
      const { data } = await notesApi.generateTopic({
        topic: params.topic,
        analysis_id: params.analysisId,
        subject: params.subject,
        unit: params.unit,
        frequency: params.frequency,
        regenerate: params.regenerate ?? false,
      });
      const note = data.data;
      set({ topicNote: note, isGenerating: false });
      return note;
    } catch (error) {
      set({ error: getErrorMessage(error), isGenerating: false });
      throw error;
    }
  },

  regenerateTopicNotes: async (params) => {
    set({ isGenerating: true, error: null });
    try {
      const { data } = await notesApi.regenerateTopic({
        topic: params.topic,
        analysis_id: params.analysisId,
        subject: params.subject,
        unit: params.unit,
        frequency: params.frequency,
      });
      const note = data.data;
      set({ topicNote: note, isGenerating: false });
      return note;
    } catch (error) {
      set({ error: getErrorMessage(error), isGenerating: false });
      throw error;
    }
  },

  saveTopicNotes: async (noteId, isSaved) => {
    try {
      const { data } = await notesApi.saveGenerated(noteId, isSaved);
      set({ topicNote: data.data });
      return data.data;
    } catch (error) {
      set({ error: getErrorMessage(error) });
      throw error;
    }
  },

  exportTopicNotePdf: async (noteId) => {
    set({ isExporting: true, error: null });
    try {
      const token = await tokenStorage.getAccessToken();
      const fileUri = `${FileSystem.cacheDirectory}topic-note-${noteId}.pdf`;
      const download = await FileSystem.downloadAsync(
        notesApi.exportGeneratedPdfUrl(noteId),
        fileUri,
        token ? { headers: { Authorization: `Bearer ${token}` } } : undefined
      );

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(download.uri, {
          mimeType: 'application/pdf',
          dialogTitle: 'Share topic notes PDF',
        });
      }

      set({ isExporting: false });
      return download.uri;
    } catch (error) {
      set({ error: getErrorMessage(error), isExporting: false });
      throw error;
    }
  },

  fetchCachedTopics: async (analysisId) => {
    try {
      const keys = await notesApi.listCachedTopicKeys(analysisId);
      set({ cachedTopicKeys: keys });
      return keys;
    } catch {
      return [];
    }
  },

  clearTopicNote: () => set({ topicNote: null }),

  clearNotes: async () => {
    try {
      const { data } = await notesApi.clearAll();
      set({ notes: [], selectedNote: null, topicNote: null });
      return data.data?.deleted ?? 0;
    } catch (error) {
      set({ error: getErrorMessage(error) });
      throw error;
    }
  },
}));
