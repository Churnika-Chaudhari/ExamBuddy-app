import { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, spacing, typography } from '@/core/theme';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import { useQuizStore } from '@/store/quizStore';

type Route = RouteProp<RootStackParamList, 'QuizAttemptReview'>;
type Nav = NativeStackNavigationProp<RootStackParamList, 'QuizAttemptReview'>;

export default function QuizAttemptReviewScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { attemptId } = route.params;
  const { selectedAttempt, isLoading, fetchAttempt } = useQuizStore();

  useEffect(() => {
    fetchAttempt(attemptId);
  }, [attemptId, fetchAttempt]);

  if (isLoading || !selectedAttempt) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  const attempt = selectedAttempt;
  const answers = attempt.answers ?? [];

  return (
    <ScreenWrapper>
      <View style={styles.header}>
        <Text style={styles.title}>{attempt.quiz_title ?? 'Quiz Review'}</Text>
        <Text style={styles.meta}>
          {attempt.subject ?? 'General'} · {Math.round(attempt.score)}% ·{' '}
          {attempt.correct_count}/{attempt.total_count}
        </Text>
      </View>

      <Text style={styles.sectionTitle}>Your Answers</Text>
      {answers.map((answer, index) => (
        <AppCard key={answer.question_id} style={styles.answerCard}>
          <View style={styles.answerHeader}>
            <Ionicons
              name={answer.is_correct ? 'checkmark-circle' : 'close-circle'}
              size={22}
              color={answer.is_correct ? colors.success : colors.error}
            />
            <Text style={styles.questionNum}>Q{index + 1}</Text>
            {answer.topic ? <Text style={styles.topic}>{answer.topic}</Text> : null}
          </View>
          <Text style={styles.answerLabel}>Your answer</Text>
          <Text style={styles.answerText}>{answer.user_answer || '—'}</Text>
          {!answer.is_correct ? (
            <>
              <Text style={[styles.answerLabel, { marginTop: spacing.sm }]}>Correct answer</Text>
              <Text style={[styles.answerText, { color: colors.success }]}>
                {answer.correct_answer}
              </Text>
            </>
          ) : null}
          {answer.explanation ? (
            <Text style={styles.explanation}>{answer.explanation}</Text>
          ) : null}
        </AppCard>
      ))}

      {attempt.quiz_id ? (
        <AppButton
          label="Retake Quiz"
          onPress={() => navigation.navigate('QuizPlay', { quizId: attempt.quiz_id })}
          icon="refresh"
          style={styles.btn}
        />
      ) : null}
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
  },
  header: {
    marginBottom: spacing.md,
  },
  title: {
    ...typography.h2,
    color: colors.text,
  },
  meta: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  sectionTitle: {
    ...typography.h3,
    color: colors.text,
    marginBottom: spacing.md,
  },
  answerCard: {
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  answerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  questionNum: {
    ...typography.label,
    color: colors.text,
  },
  topic: {
    ...typography.caption,
    color: colors.primary,
    marginLeft: 'auto',
  },
  answerLabel: {
    ...typography.caption,
    color: colors.textMuted,
  },
  answerText: {
    ...typography.bodySmall,
    color: colors.text,
    marginTop: 2,
  },
  explanation: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: spacing.sm,
    fontStyle: 'italic',
  },
  btn: {
    marginBottom: spacing.xl,
  },
});
