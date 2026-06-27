export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  institution?: string | null;
  course?: string | null;
  preferences?: {
    ai_provider?: string;
    theme?: string;
    notifications?: boolean;
  };
  is_active?: boolean;
  created_at?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Document {
  id: string;
  user_id: string;
  title: string;
  description?: string | null;
  category: 'pyq' | 'notes' | 'study_material' | 'other';
  subject?: string | null;
  exam_year?: number | null;
  file_type: 'pdf' | 'docx' | 'image';
  file_url: string;
  file_public_id: string;
  file_size_bytes?: number | null;
  page_count?: number | null;
  extracted_text?: string | null;
  status: 'uploading' | 'processing' | 'ready' | 'failed';
  error_message?: string | null;
  tags?: string[];
  created_at?: string;
}

export interface TopicTableRow {
  topic: string;
  frequency: number;
  importance?: 'High' | 'Medium' | 'Low' | string;
}

export interface TopicFrequencyRow {
  topic: string;
  unit: string;
  frequency: number;
}

export interface AcademicTopicRow {
  topic: string;
  frequency: number;
  unit?: string;
}

export interface TopicGroup {
  group: string;
  topics: string[];
}

export interface ImportantTopic {
  topic: string;
  score: number;
  reason?: string | null;
}

export interface RepeatedQuestion {
  text: string;
  occurrences: string[];
  frequency: number;
}

export interface ExamPattern {
  pattern: string;
  description: string;
  confidence: number;
}

export interface PYQAnalysis {
  id: string;
  user_id: string;
  document_ids: string[];
  subject?: string | null;
  title: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  repeated_questions: RepeatedQuestion[];
  topic_frequency: Record<string, number>;
  important_topics: ImportantTopic[];
  topic_table?: TopicTableRow[];
  academic_topic_table?: AcademicTopicRow[];
  topic_frequency_table?: TopicFrequencyRow[];
  high_priority_topics?: TopicFrequencyRow[];
  medium_priority_topics?: TopicFrequencyRow[];
  low_priority_topics?: TopicFrequencyRow[];
  predicted_important_topics?: TopicFrequencyRow[];
  most_important_topics?: TopicTableRow[];
  frequently_asked_topics?: TopicTableRow[];
  rarely_asked_topics?: TopicTableRow[];
  topic_groups?: TopicGroup[];
  syllabus_topics?: string[];
  exam_patterns: ExamPattern[];
  summary?: string | null;
  error_message?: string | null;
  created_at?: string;
  completed_at?: string | null;
}

export interface GeneratedTopicNote {
  id: string;
  user_id: string;
  topic: string;
  notes: string;
  summary?: string | null;
  subject?: string | null;
  unit?: string | null;
  frequency?: number | null;
  analysis_id?: string | null;
  is_saved: boolean;
  cached: boolean;
  ai_metadata?: {
    provider?: string | null;
    model?: string | null;
    tokens_used?: number | null;
    generation_mode?: string | null;
    rag_chunk_count?: number | null;
    generation_error?: string | null;
    ai_error?: string | null;
  } | null;
  rag_sources?: { title?: string; category?: string; relevance_score?: number }[];
  generated_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface Note {
  id: string;
  user_id: string;
  title: string;
  type: 'generated' | 'simplified' | 'manual';
  source_type?: string | null;
  source_id?: string | null;
  content: string;
  summary?: string | null;
  topics: string[];
  is_favorite: boolean;
  ai_metadata?: {
    provider?: string | null;
    model?: string | null;
    tokens_used?: number | null;
  } | null;
  created_at?: string;
  updated_at?: string;
}

export type QuizQuestionType = 'mcq' | 'true_false' | 'short_answer' | 'fill_blank' | 'mixed';
export type QuizDifficulty = 'easy' | 'medium' | 'hard';

export interface QuizQuestion {
  id: string;
  question_text: string;
  question_type: QuizQuestionType;
  options: string[];
  correct_answer: string;
  explanation?: string | null;
  topic?: string | null;
}

export interface Quiz {
  id: string;
  user_id: string;
  title: string;
  subject?: string | null;
  difficulty?: QuizDifficulty | null;
  source_notes_id?: string | null;
  source_analysis_id?: string | null;
  source_topics: string[];
  quiz_type: QuizQuestionType;
  questions: QuizQuestion[];
  total_questions: number;
  time_limit_minutes?: number | null;
  created_at?: string;
}

export interface QuizSubmitResult {
  attempt_id: string;
  quiz_id: string;
  subject?: string | null;
  difficulty?: QuizDifficulty | null;
  quiz_title?: string | null;
  score: number;
  correct_count: number;
  total_count: number;
  answers: {
    question_id: string;
    user_answer: string;
    correct_answer: string;
    is_correct: boolean;
    explanation?: string | null;
    topic?: string | null;
  }[];
  completed_at: string;
}

export interface QuizAttempt {
  id: string;
  user_id: string;
  quiz_id: string;
  quiz_title?: string | null;
  subject?: string | null;
  difficulty?: QuizDifficulty | null;
  quiz_type?: QuizQuestionType | null;
  score: number;
  correct_count: number;
  total_count: number;
  time_taken_seconds?: number | null;
  completed_at: string;
  answers?: QuizSubmitResult['answers'];
}

export interface QuizSubject {
  id: string;
  name: string;
  pyq_count: number;
  topic_count: number;
  last_updated?: string | null;
  created_at?: string | null;
}

export interface SubjectTopic {
  topic: string;
  unit?: string | null;
  frequency: number;
  importance?: string | null;
}

export interface SubjectSourceDocument {
  id: string;
  title: string;
  category: string;
  status?: string | null;
  page_count?: number | null;
}

export interface SubjectOverview {
  subject_id: string;
  subject: string;
  topics: SubjectTopic[];
  analysis_ids: string[];
  source_documents: SubjectSourceDocument[];
  pyq_count: number;
  notes_count: number;
  study_material_count: number;
  total_sources: number;
}

export interface TopicPerformance {
  topic: string;
  subject?: string | null;
  accuracy_percentage: number;
  attempts: number;
  correct: number;
  total: number;
}

export interface SubjectPerformance {
  subject: string;
  accuracy_percentage: number;
  attempts: number;
  quizzes: number;
}

export interface WeeklyProgressPoint {
  week: string;
  average_score: number;
  quizzes: number;
}

export interface ScoreTrendPoint {
  date: string;
  score: number;
  subject?: string | null;
}

export interface QuizAnalysis {
  subject?: string | null;
  total_quizzes_attempted: number;
  average_score: number;
  highest_score: number;
  lowest_score: number;
  total_questions_solved: number;
  weak_topics: TopicPerformance[];
  strong_topics: TopicPerformance[];
  improvement_suggestions: string[];
  weekly_progress: WeeklyProgressPoint[];
  score_trend: ScoreTrendPoint[];
  topic_strength_distribution: TopicPerformance[];
}

export interface QuizGenerateParams {
  subject: string;
  analysis_id?: string;
  topics?: string[];
  notes_id?: string;
  title?: string;
  quiz_type?: QuizQuestionType;
  difficulty?: QuizDifficulty;
  num_questions?: number;
  time_limit_minutes?: number;
}

export interface DashboardStats {
  documents_count: number;
  analyses_count: number;
  notes_count: number;
  quizzes_taken: number;
  avg_quiz_score: number;
}

export interface RecentActivity {
  type: string;
  ref_id: string;
  title: string;
  timestamp: string;
}

export interface DashboardData {
  stats: DashboardStats;
  recent_activity: RecentActivity[];
}

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  has_next: boolean;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface PaginatedApiResponse<T> {
  success: boolean;
  data: T[];
  pagination: Pagination;
  message?: string;
}

export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
    details?: unknown[];
  };
}
