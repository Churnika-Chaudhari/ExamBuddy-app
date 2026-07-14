import { create } from 'zustand';

import { quizApi } from '@/data/api/endpoints';
import { getErrorMessage } from '@/data/api/client';
import type {
  Quiz,
  QuizAnalysis,
  QuizAttempt,
  QuizGenerateParams,
  QuizSubject,
  QuizSubmitResult,
  SubjectTopic,
} from '@/domain/types';

interface QuizState {
  quizzes: Quiz[];
  subjects: QuizSubject[];
  subjectTopics: SubjectTopic[];
  selectedSubject: string | null;
  history: QuizAttempt[];
  analysis: QuizAnalysis | null;
  activeQuiz: Quiz | null;
  lastResult: QuizSubmitResult | null;
  selectedAttempt: QuizAttempt | null;
  isLoading: boolean;
  isGenerating: boolean;
  isSubmitting: boolean;
  error: string | null;

  fetchQuizzes: (subject?: string) => Promise<void>;
  fetchSubjects: () => Promise<QuizSubject[]>;
  fetchSubjectTopics: (subjectId: string) => Promise<{
    topics: SubjectTopic[];
    subject: string;
    analysisIds: string[];
  }>;
  deleteSubject: (subjectId: string) => Promise<void>;
  generateQuiz: (params: QuizGenerateParams) => Promise<Quiz>;
  loadQuiz: (id: string) => Promise<Quiz>;
  submitQuiz: (
    id: string,
    answers: { question_id: string; user_answer: string }[],
    timeTaken?: number
  ) => Promise<QuizSubmitResult>;
  fetchHistory: (subject?: string, search?: string) => Promise<void>;
  fetchAnalysis: (subject: string) => Promise<QuizAnalysis | null>;
  fetchAttempt: (attemptId: string) => Promise<QuizAttempt>;
  deleteAttempt: (attemptId: string) => Promise<void>;
  deleteQuiz: (quizId: string) => Promise<void>;
  clearQuizzes: () => Promise<void>;
  setSelectedSubject: (subject: string | null) => void;
  clearLastResult: () => void;
}

export const useQuizStore = create<QuizState>((set, get) => ({
  quizzes: [],
  subjects: [],
  subjectTopics: [],
  selectedSubject: null,
  history: [],
  analysis: null,
  activeQuiz: null,
  lastResult: null,
  selectedAttempt: null,
  isLoading: false,
  isGenerating: false,
  isSubmitting: false,
  error: null,

  fetchQuizzes: async (subject) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await quizApi.list(1, subject);
      set({ quizzes: data.data, isLoading: false });
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
    }
  },

  fetchSubjects: async () => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await quizApi.listSubjects();
      set({ subjects: data.data, isLoading: false });
      return data.data;
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
      throw error;
    }
  },

  fetchSubjectTopics: async (subjectId) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await quizApi.getSubjectTopics(subjectId);
      const payload = data.data;
      set({
        subjectTopics: payload.topics,
        selectedSubject: payload.subject,
        isLoading: false,
      });
      return {
        topics: payload.topics,
        subject: payload.subject,
        analysisIds: payload.analysis_ids ?? [],
      };
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
      throw error;
    }
  },

  deleteSubject: async (subjectId) => {
    await quizApi.deleteSubject(subjectId);
    set({ subjects: get().subjects.filter((s) => s.id !== subjectId) });
  },

  generateQuiz: async (params) => {
    set({ isGenerating: true, error: null });
    try {
      const { data } = await quizApi.generate(params);
      const quiz = data.data;
      set({
        activeQuiz: quiz,
        quizzes: [quiz, ...get().quizzes],
        isGenerating: false,
      });
      return quiz;
    } catch (error) {
      set({ error: getErrorMessage(error), isGenerating: false });
      throw error;
    }
  },

  loadQuiz: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await quizApi.get(id);
      set({ activeQuiz: data.data, isLoading: false });
      return data.data;
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
      throw error;
    }
  },

  submitQuiz: async (id, answers, timeTaken) => {
    set({ isSubmitting: true, error: null });
    try {
      const { data } = await quizApi.submit(id, answers, timeTaken);
      set({ lastResult: data.data, isSubmitting: false });
      return data.data;
    } catch (error) {
      set({ error: getErrorMessage(error), isSubmitting: false });
      throw error;
    }
  },

  fetchHistory: async (subject, search) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await quizApi.listHistory(1, subject, search);
      set({ history: data.data, isLoading: false });
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
    }
  },

  fetchAnalysis: async (subject) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await quizApi.getAnalysis(subject);
      set({ analysis: data.data, isLoading: false });
      return data.data;
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
      return null;
    }
  },

  fetchAttempt: async (attemptId) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await quizApi.getAttempt(attemptId);
      set({ selectedAttempt: data.data, isLoading: false });
      return data.data;
    } catch (error) {
      set({ error: getErrorMessage(error), isLoading: false });
      throw error;
    }
  },

  deleteAttempt: async (attemptId) => {
    await quizApi.deleteAttempt(attemptId);
    set({ history: get().history.filter((h) => h.id !== attemptId) });
  },

  deleteQuiz: async (quizId) => {
    await quizApi.delete(quizId);
    set({ quizzes: get().quizzes.filter((q) => q.id !== quizId) });
  },

  clearQuizzes: async () => {
    await quizApi.clearAll();
    set({ quizzes: [] });
  },

  setSelectedSubject: (subject) => set({ selectedSubject: subject }),
  clearLastResult: () => set({ lastResult: null }),
}));
