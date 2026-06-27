import { apiClient } from './client';
import type {
  ApiResponse,
  AuthTokens,
  DashboardData,
  Document as AppDocument,
  Note,
  PaginatedApiResponse,
  GeneratedTopicNote,
  PYQAnalysis,
  Quiz,
  QuizAnalysis,
  QuizAttempt,
  QuizGenerateParams,
  QuizSubject,
  QuizSubmitResult,
  SubjectOverview,
  SubjectTopic,
  User,
} from '@/domain/types';

export const authApi = {
  register: (email: string, password: string, full_name: string) =>
    apiClient.post<ApiResponse<AuthTokens>>('/auth/register', { email, password, full_name }),

  login: (email: string, password: string) =>
    apiClient.post<ApiResponse<AuthTokens>>('/auth/login', { email, password }),

  me: () => apiClient.get<ApiResponse<User>>('/auth/me'),
};

export const dashboardApi = {
  get: () => apiClient.get<ApiResponse<DashboardData>>('/dashboard'),

  clearActivities: () =>
    apiClient.delete<ApiResponse<DashboardData>>('/dashboard/activities'),

  deleteActivity: (refId: string, type: string) =>
    apiClient.delete<ApiResponse<DashboardData>>(`/dashboard/activities/${refId}`, {
      params: { type },
    }),
};

export interface UploadFilePayload {
  uri: string;
  name: string;
  mimeType?: string | null;
}

export const documentsApi = {
  list: (params?: { page?: number; category?: string }) =>
    apiClient.get<PaginatedApiResponse<AppDocument>>('/documents', { params }),

  upload: (
    file: UploadFilePayload,
    fields: { title?: string; subject?: string; exam_year?: number; category?: string }
  ) => {
    const formData = new FormData();
    formData.append('file', {
      uri: file.uri,
      name: file.name,
      type: file.mimeType ?? 'application/pdf',
    } as unknown as Blob);
    if (fields.title) formData.append('title', fields.title);
    if (fields.subject) formData.append('subject', fields.subject);
    if (fields.exam_year) formData.append('exam_year', String(fields.exam_year));
    formData.append('category', fields.category ?? 'pyq');

    return apiClient.post<ApiResponse<{ document: AppDocument }>>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    });
  },

  uploadBatch: (
    files: UploadFilePayload[],
    fields: { subject?: string; exam_year?: number; category?: string }
  ) => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', {
        uri: file.uri,
        name: file.name,
        type: file.mimeType ?? 'application/pdf',
      } as unknown as Blob);
    });
    if (fields.subject) formData.append('subject', fields.subject);
    if (fields.exam_year) formData.append('exam_year', String(fields.exam_year));
    formData.append('category', fields.category ?? 'pyq');

    return apiClient.post<ApiResponse<{ documents: AppDocument[]; count: number }>>(
      '/documents/upload-batch',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000,
      }
    );
  },

  getStatus: (id: string) =>
    apiClient.get<ApiResponse<{ id: string; status: string; error_message?: string }>>(
      `/documents/${id}/status`
    ),

  clearAll: (category?: string) =>
    apiClient.delete<ApiResponse<{ deleted: number; message: string }>>('/documents', {
      params: category ? { category } : undefined,
    }),
};

export const analysisApi = {
  list: (page = 1) =>
    apiClient.get<PaginatedApiResponse<PYQAnalysis>>('/analysis/pyq', { params: { page } }),

  create: (document_ids: string[], subject?: string, title?: string) =>
    apiClient.post<ApiResponse<PYQAnalysis>>('/analysis/pyq', { document_ids, subject, title }),

  get: (id: string) => apiClient.get<ApiResponse<PYQAnalysis>>(`/analysis/pyq/${id}`),

  getStatus: (id: string) =>
    apiClient.get<ApiResponse<{ id: string; status: string; error_message?: string }>>(
      `/analysis/pyq/${id}/status`
    ),
};

export const notesApi = {
  list: (page = 1) =>
    apiClient.get<PaginatedApiResponse<Note>>('/notes', { params: { page } }),

  get: (id: string) => apiClient.get<ApiResponse<Note>>(`/notes/${id}`),

  exportPdfUrl: (id: string) => `${apiClient.defaults.baseURL}/notes/${id}/export/pdf`,

  generate: (payload: {
    analysis_id?: string;
    topics?: string[];
    topic?: string;
    title?: string;
    subject?: string;
    unit?: string;
    frequency?: number;
    regenerate?: boolean;
  }) => apiClient.post<ApiResponse<Note | GeneratedTopicNote>>('/notes/generate', payload),

  generateTopic: (payload: {
    topic: string;
    analysis_id?: string;
    subject?: string;
    unit?: string;
    frequency?: number;
    regenerate?: boolean;
  }) => apiClient.post<ApiResponse<GeneratedTopicNote>>('/notes/topic/generate', payload),

  regenerateTopic: (payload: {
    topic: string;
    analysis_id?: string;
    subject?: string;
    unit?: string;
    frequency?: number;
  }) => apiClient.post<ApiResponse<GeneratedTopicNote>>('/notes/topic/regenerate', payload),

  topicStatus: (topic: string, analysisId?: string) =>
    apiClient.get<ApiResponse<{ topic: string; has_notes: boolean; note_id?: string }>>(
      '/notes/topic/status',
      { params: { topic, analysis_id: analysisId } }
    ),

  listGenerated: (page = 1, analysisId?: string) =>
    apiClient.get<PaginatedApiResponse<GeneratedTopicNote>>('/notes/generated', {
      params: { page, analysis_id: analysisId },
    }),

  getGenerated: (id: string) =>
    apiClient.get<ApiResponse<GeneratedTopicNote>>(`/notes/generated/${id}`),

  saveGenerated: (id: string, is_saved: boolean) =>
    apiClient.patch<ApiResponse<GeneratedTopicNote>>(
      `/notes/generated/${id}/save`,
      {},
      { params: { is_saved } }
    ),

  exportGeneratedPdfUrl: (id: string) =>
    `${apiClient.defaults.baseURL}/notes/generated/${id}/export/pdf`,

  listCachedTopicKeys: async (analysisId: string): Promise<string[]> => {
    const { data } = await apiClient.get<PaginatedApiResponse<GeneratedTopicNote>>(
      '/notes/generated',
      { params: { page: 1, limit: 100, analysis_id: analysisId } }
    );
    return data.data.map((n) => n.topic.toLowerCase().trim());
  },

  simplify: (payload: { document_id?: string; text?: string; title?: string }) =>
    apiClient.post<ApiResponse<Note>>('/notes/simplify', payload),

  toggleFavorite: (id: string, is_favorite: boolean) =>
    apiClient.patch<ApiResponse<Note>>(`/notes/${id}`, { is_favorite }),

  clearAll: () =>
    apiClient.delete<ApiResponse<{ deleted: number; message: string }>>('/notes'),
};

export const subjectsApi = {
  list: () => apiClient.get<ApiResponse<QuizSubject[]>>('/subjects'),

  getTopics: (subjectId: string) =>
    apiClient.get<
      ApiResponse<{ subject_id: string; subject: string; topics: SubjectTopic[]; analysis_ids: string[] }>
    >(`/subjects/${subjectId}/topics`),

  getOverview: (subjectId: string) =>
    apiClient.get<ApiResponse<SubjectOverview>>(`/subjects/${subjectId}/overview`),

  delete: (subjectId: string) =>
    apiClient.delete<ApiResponse<{ message: string }>>(`/subjects/${subjectId}`),
};

export const quizApi = {
  list: (page = 1, subject?: string) =>
    apiClient.get<PaginatedApiResponse<Quiz>>('/quiz', { params: { page, subject } }),

  get: (id: string) => apiClient.get<ApiResponse<Quiz>>(`/quiz/${id}`),

  generate: (payload: QuizGenerateParams) =>
    apiClient.post<ApiResponse<Quiz>>('/quiz/generate', payload),

  submit: (
    id: string,
    answers: { question_id: string; user_answer: string }[],
    time_taken_seconds?: number
  ) =>
    apiClient.post<ApiResponse<QuizSubmitResult>>(`/quiz/${id}/submit`, {
      answers,
      time_taken_seconds,
    }),

  delete: (id: string) => apiClient.delete<ApiResponse<{ message: string }>>(`/quiz/${id}`),

  clearAll: () =>
    apiClient.delete<ApiResponse<{ deleted: number; message: string }>>('/quiz'),

  listSubjects: () => subjectsApi.list(),

  getSubjectTopics: (subjectId: string) => subjectsApi.getTopics(subjectId),

  deleteSubject: (subjectId: string) => subjectsApi.delete(subjectId),

  listHistory: (page = 1, subject?: string, search?: string) =>
    apiClient.get<PaginatedApiResponse<QuizAttempt>>('/quiz/history', {
      params: { page, subject, search },
    }),

  getAttempt: (attemptId: string) =>
    apiClient.get<ApiResponse<QuizAttempt>>(`/quiz/attempts/${attemptId}`),

  deleteAttempt: (attemptId: string) =>
    apiClient.delete<ApiResponse<{ message: string }>>(`/quiz/attempts/${attemptId}`),

  getAnalysis: (subject: string) =>
    apiClient.get<ApiResponse<QuizAnalysis>>(`/quiz/analysis/${encodeURIComponent(subject)}`),

  listAttempts: (quizId: string) =>
    apiClient.get<ApiResponse<QuizAttempt[]>>(`/quiz/${quizId}/attempts`),
};

export const profileApi = {
  get: () => apiClient.get<ApiResponse<User>>('/profile'),

  update: (data: { full_name?: string; institution?: string; course?: string }) =>
    apiClient.patch<ApiResponse<User>>('/profile', data),

  changePassword: (current_password: string, new_password: string) =>
    apiClient.patch<ApiResponse<{ message: string }>>('/profile/password', {
      current_password,
      new_password,
    }),
};
