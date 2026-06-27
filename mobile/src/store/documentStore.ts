import { create } from 'zustand';

import { documentsApi } from '@/data/api/endpoints';
import { getErrorMessage } from '@/data/api/client';
import type { Document } from '@/domain/types';

export interface PickedFile {
  uri: string;
  name: string;
  mimeType?: string | null;
}

interface DocumentState {
  documents: Document[];
  isLoading: boolean;
  isUploading: boolean;
  uploadProgress: string | null;
  error: string | null;
  fetchDocuments: () => Promise<void>;
  uploadDocument: (
    file: PickedFile,
    fields: { title?: string; subject?: string; exam_year?: number }
  ) => Promise<Document>;
  uploadDocuments: (
    files: PickedFile[],
    fields?: { subject?: string; exam_year?: number; category?: string }
  ) => Promise<Document[]>;
  clearDocuments: (category?: string) => Promise<number>;
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  documents: [],
  isLoading: false,
  isUploading: false,
  uploadProgress: null,
  error: null,

  fetchDocuments: async () => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await documentsApi.list();
      set({ documents: data.data, isLoading: false });
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
    }
  },

  uploadDocument: async (file, fields) => {
    set({ isUploading: true, error: null, uploadProgress: null });
    try {
      const { data } = await documentsApi.upload(file, { ...fields, category: 'pyq' });
      const doc = data.data.document;
      set({
        documents: [doc, ...get().documents],
        isUploading: false,
        uploadProgress: null,
      });
      return doc;
    } catch (error) {
      set({ error: getErrorMessage(error), isUploading: false, uploadProgress: null });
      throw error;
    }
  },

  uploadDocuments: async (files, fields = {}) => {
    if (!files.length) return [];

    const category = fields.category ?? 'pyq';

    set({ isUploading: true, error: null, uploadProgress: `Uploading ${files.length} file(s)...` });

    try {
      if (files.length > 1) {
        try {
          set({ uploadProgress: `Uploading ${files.length} files in batch...` });
          const { data } = await documentsApi.uploadBatch(files, { ...fields, category });
          const uploaded = data.data.documents;
          set({
            documents: [...uploaded, ...get().documents],
            isUploading: false,
            uploadProgress: null,
          });
          return uploaded;
        } catch {
          // Fall back to sequential uploads if batch fails
        }
      }

      const uploaded: Document[] = [];
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        set({ uploadProgress: `Uploading ${i + 1}/${files.length}: ${file.name}` });
        const title = file.name.replace(/\.[^/.]+$/, '');
        const { data } = await documentsApi.upload(file, {
          ...fields,
          title,
          category,
        });
        uploaded.push(data.data.document);
      }

      set({
        documents: [...uploaded, ...get().documents],
        isUploading: false,
        uploadProgress: null,
      });
      return uploaded;
    } catch (error) {
      set({ error: getErrorMessage(error), isUploading: false, uploadProgress: null });
      throw error;
    }
  },

  clearDocuments: async (category) => {
    try {
      const { data } = await documentsApi.clearAll(category);
      set({ documents: [] });
      return data.data?.deleted ?? 0;
    } catch (error) {
      set({ error: getErrorMessage(error) });
      throw error;
    }
  },
}));
