import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator, Chip, SegmentedButtons } from 'react-native-paper';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';

import { colors, spacing, typography } from '@/core/theme';
import { getErrorMessage } from '@/data/api/client';
import type { QuizDifficulty, QuizQuestionType } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import { useQuizStore } from '@/store/quizStore';
import { useUIStore } from '@/store/uiStore';

type Route = RouteProp<RootStackParamList, 'QuizConfig'>;
type Nav = NativeStackNavigationProp<RootStackParamList, 'QuizConfig'>;

const QUIZ_TYPES: { value: QuizQuestionType; label: string }[] = [
  { value: 'mixed', label: 'Mixed' },
  { value: 'mcq', label: 'MCQ' },
  { value: 'true_false', label: 'T/F' },
  { value: 'fill_blank', label: 'Fill' },
  { value: 'short_answer', label: 'Short' },
];

const DIFFICULTIES: { value: QuizDifficulty; label: string }[] = [
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
];

const QUESTION_COUNTS = [5, 10, 15, 20];

export default function QuizConfigScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { subject, subjectId } = route.params;

  const { subjectTopics, isLoading, isGenerating, fetchSubjectTopics, generateQuiz } =
    useQuizStore();
  const showSnackbar = useUIStore((s) => s.showSnackbar);

  const [quizType, setQuizType] = useState<QuizQuestionType>('mixed');
  const [difficulty, setDifficulty] = useState<QuizDifficulty>('medium');
  const [numQuestions, setNumQuestions] = useState(10);
  const [analysisId, setAnalysisId] = useState<string | undefined>();

  useEffect(() => {
    fetchSubjectTopics(subjectId)
      .then(({ analysisIds }) => setAnalysisId(analysisIds[0]))
      .catch((err) => showSnackbar(getErrorMessage(err), 'error'));
  }, [subjectId, fetchSubjectTopics, showSnackbar]);

  const handleGenerate = async () => {
    try {
      const topics = subjectTopics.map((t) => t.topic);
      const quiz = await generateQuiz({
        subject,
        analysis_id: analysisId,
        topics,
        quiz_type: quizType,
        difficulty,
        num_questions: numQuestions,
        title: `${subject} Quiz`,
      });
      showSnackbar('Quiz generated!', 'success');
      navigation.replace('QuizPlay', { quizId: quiz.id });
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    }
  };

  if (isLoading && !subjectTopics.length) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading topics for {subject}...</Text>
      </View>
    );
  }

  return (
    <ScreenWrapper>
      <Text style={styles.title}>{subject}</Text>
      <Text style={styles.subtitle}>
        {subjectTopics.length} repeated topics will be used for this quiz
      </Text>

      <AppCard style={styles.section}>
        <Text style={styles.sectionLabel}>Topics included</Text>
        <View style={styles.chips}>
          {subjectTopics.slice(0, 12).map((t) => (
            <Chip key={t.topic} style={styles.chip} textStyle={styles.chipText}>
              {t.topic}
              {t.frequency > 1 ? ` (${t.frequency})` : ''}
            </Chip>
          ))}
          {subjectTopics.length > 12 ? (
            <Chip style={styles.chip}>+{subjectTopics.length - 12} more</Chip>
          ) : null}
        </View>
      </AppCard>

      <Text style={styles.sectionLabel}>Question type</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.typeRow}>
        {QUIZ_TYPES.map((t) => (
          <Chip
            key={t.value}
            selected={quizType === t.value}
            onPress={() => setQuizType(t.value)}
            style={styles.typeChip}
          >
            {t.label}
          </Chip>
        ))}
      </ScrollView>

      <Text style={styles.sectionLabel}>Difficulty</Text>
      <SegmentedButtons
        value={difficulty}
        onValueChange={(v) => setDifficulty(v as QuizDifficulty)}
        buttons={DIFFICULTIES.map((d) => ({ value: d.value, label: d.label }))}
        style={styles.segment}
      />

      <Text style={styles.sectionLabel}>Number of questions</Text>
      <View style={styles.countRow}>
        {QUESTION_COUNTS.map((n) => (
          <Chip
            key={n}
            selected={numQuestions === n}
            onPress={() => setNumQuestions(n)}
            style={styles.countChip}
          >
            {n}
          </Chip>
        ))}
      </View>

      <AppButton
        label="Generate Quiz"
        onPress={handleGenerate}
        loading={isGenerating}
        icon="lightning-bolt"
        style={styles.generateBtn}
      />
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
    padding: spacing.xl,
  },
  loadingText: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: spacing.md,
    textAlign: 'center',
  },
  title: {
    ...typography.h2,
    color: colors.text,
  },
  subtitle: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: spacing.xs,
    marginBottom: spacing.md,
  },
  section: {
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  sectionLabel: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '700',
    textTransform: 'uppercase',
    marginBottom: spacing.sm,
    marginTop: spacing.sm,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
  },
  chip: {
    backgroundColor: colors.surface,
  },
  chipText: {
    fontSize: 12,
  },
  typeRow: {
    marginBottom: spacing.sm,
  },
  typeChip: {
    marginRight: spacing.xs,
  },
  segment: {
    marginBottom: spacing.md,
  },
  countRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  countChip: {
    minWidth: 48,
  },
  generateBtn: {
    marginBottom: spacing.xl,
  },
});
