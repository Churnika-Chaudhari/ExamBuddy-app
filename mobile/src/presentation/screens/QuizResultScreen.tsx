import { StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
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

type Route = RouteProp<RootStackParamList, 'QuizResult'>;
type Nav = NativeStackNavigationProp<RootStackParamList, 'QuizResult'>;

export default function QuizResultScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { quizId } = route.params;
  const { lastResult } = useQuizStore();

  if (!lastResult) {
    return (
      <View style={styles.centered}>
        <Text>No result available</Text>
      </View>
    );
  }

  const result = lastResult;
  const passed = result.score >= 60;
  const mistakes = result.answers.filter((a) => !a.is_correct);

  return (
    <ScreenWrapper>
      <View style={styles.scoreSection}>
        <View style={[styles.scoreCircle, { borderColor: passed ? colors.success : colors.warning }]}>
          <Text style={[styles.scoreValue, { color: passed ? colors.success : colors.warning }]}>
            {result.score}%
          </Text>
        </View>
        <Text style={styles.scoreLabel}>
          {passed ? 'Great job!' : 'Keep practicing!'}
        </Text>
        <Text style={styles.scoreDetail}>
          {result.correct_count} of {result.total_count} correct
        </Text>
        {result.subject ? (
          <Text style={styles.subject}>{result.subject} · {result.difficulty ?? 'medium'}</Text>
        ) : null}
      </View>

      {mistakes.length > 0 ? (
        <AppCard style={styles.mistakeCard}>
          <Text style={styles.mistakeTitle}>
            {mistakes.length} mistake{mistakes.length > 1 ? 's' : ''} to review
          </Text>
          {mistakes.slice(0, 3).map((m) => (
            <Text key={m.question_id} style={styles.mistakeItem}>
              • {m.topic ?? 'Question'} — correct: {m.correct_answer}
            </Text>
          ))}
        </AppCard>
      ) : null}

      <Text style={styles.sectionTitle}>Answer Review</Text>
      {result.answers.map((answer, index) => (
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
          <View style={styles.answerBody}>
            <Text style={styles.answerLabel}>Your answer:</Text>
            <Text style={styles.answerText}>{answer.user_answer || '—'}</Text>
            {!answer.is_correct ? (
              <>
                <Text style={[styles.answerLabel, { marginTop: spacing.sm }]}>
                  Correct answer:
                </Text>
                <Text style={[styles.answerText, { color: colors.success }]}>
                  {answer.correct_answer}
                </Text>
              </>
            ) : null}
            {answer.explanation ? (
              <Text style={styles.explanation}>{answer.explanation}</Text>
            ) : null}
          </View>
        </AppCard>
      ))}

      <AppButton
        label="Retake Quiz"
        onPress={() => navigation.replace('QuizPlay', { quizId })}
        icon="refresh"
        style={styles.button}
      />
      <AppButton
        label="View Analysis"
        mode="outlined"
        onPress={() => navigation.navigate('QuizAnalysis', { subject: result.subject ?? 'General' })}
        icon="analytics-outline"
        style={styles.button}
      />
      <AppButton
        label="Back to Quizzes"
        mode="outlined"
        onPress={() => navigation.navigate('Main', { screen: 'Quiz' })}
        style={styles.button}
      />
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scoreSection: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
  },
  scoreCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    borderWidth: 4,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  scoreValue: {
    fontSize: 32,
    fontWeight: '700',
  },
  scoreLabel: {
    ...typography.h3,
    color: colors.text,
  },
  scoreDetail: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  subject: {
    ...typography.caption,
    color: colors.primary,
    marginTop: spacing.xs,
    fontWeight: '600',
  },
  mistakeCard: {
    padding: spacing.md,
    marginBottom: spacing.md,
    backgroundColor: colors.errorLight,
    borderColor: colors.errorLight,
  },
  mistakeTitle: {
    ...typography.label,
    color: colors.error,
    marginBottom: spacing.sm,
  },
  mistakeItem: {
    ...typography.caption,
    color: colors.text,
    lineHeight: 18,
    marginBottom: 2,
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
  answerBody: {},
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
    lineHeight: 18,
  },
  button: {
    marginBottom: spacing.sm,
  },
});
