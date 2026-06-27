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
  UploadPYQ: undefined;
  UploadedDocuments: undefined;
  AnalysisResult: { analysisId: string };
  SubjectNotes: { subjectId: string; subjectName?: string };
  TopicStudyNotes: {
    topic: string;
    analysisId?: string;
    subject?: string;
    unit?: string;
    frequency?: number;
  };
  NoteDetail: { noteId: string };
  QuizPlay: { quizId: string };
  QuizResult: { quizId: string };
  QuizSubjectSelect: undefined;
  QuizConfig: { subject: string };
  QuizHistory: undefined;
  QuizAnalysis: { subject: string };
  QuizAttemptReview: { attemptId: string };
};

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
