import type { NavigatorScreenParams } from '@react-navigation/native';

export type AuthStackParamList = {
  Login: undefined;
  Signup: undefined;
};

export type MainTabParamList = {
  Dashboard: undefined;
  Notes: undefined;
  Quiz: undefined;
  Profile: undefined;
};

export type RootStackParamList = {
  Splash: undefined;
  Auth: NavigatorScreenParams<AuthStackParamList>;
  Main: NavigatorScreenParams<MainTabParamList>;
  /** Dedicated upload entry — pass initialCategory to open PYQ or Syllabus mode. */
  UploadPYQ: { initialCategory?: 'pyq' | 'syllabus' } | undefined;
  UploadedDocuments: undefined;
  DocumentViewer: { documentId: string; title: string; fileUrl: string };
  AnalysisResult: { analysisId: string };
  SubjectNotes: { subjectId: string; subjectName?: string };
  ModuleTopics: {
    subjectId: string;
    subjectName: string;
    moduleId?: string;
    moduleIds?: string[];
    moduleName?: string;
    moduleNumber?: number | null;
    analysisIds?: string[];
  };
  TopicStudyNotes: {
    topic: string;
    analysisId?: string;
    subject?: string;
    subjectId?: string;
    unit?: string;
    moduleId?: string;
    moduleName?: string;
    moduleNumber?: number | null;
    topicId?: string;
    frequency?: number;
    occurrenceCount?: number;
    paperCount?: number;
    totalMarks?: number;
    priority?: string;
  };
  NoteDetail: { noteId: string };
  QuizPlay: { quizId: string };
  QuizResult: { quizId: string };
  QuizSubjectSelect: undefined;
  QuizConfig: { subject: string; subjectId: string };
  QuizHistory: undefined;
  QuizAnalysis: { subject: string };
  QuizAttemptReview: { attemptId: string };
};

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
