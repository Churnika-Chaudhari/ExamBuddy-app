import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, View, TouchableOpacity } from 'react-native';
import { Text, ActivityIndicator, RadioButton, TextInput } from 'react-native-paper';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';

import { colors, radius, spacing, typography } from '@/core/theme';
import type { QuizQuestion } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import ScreenWrapper, { STACK_SCREEN_EDGES } from '@/presentation/components/ScreenWrapper';
import { useQuizStore } from '@/store/quizStore';

type Route = RouteProp<RootStackParamList, 'QuizPlay'>;
type Nav = NativeStackNavigationProp<RootStackParamList, 'QuizPlay'>;

function isTextQuestion(type: string) {
  return type === 'short_answer' || type === 'fill_blank';
}

export default function QuizPlayScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { quizId } = route.params;

  const { activeQuiz, isLoading, isSubmitting, loadQuiz, submitQuiz } = useQuizStore();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [startTime] = useState(Date.now());

  useEffect(() => {
    loadQuiz(quizId);
  }, [quizId, loadQuiz]);

  if (isLoading || !activeQuiz) {
    return (
      <ScreenWrapper scrollable={false} edges={STACK_SCREEN_EDGES}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      </ScreenWrapper>
    );
  }

  const questions = activeQuiz.questions;
  const current: QuizQuestion = questions[currentIndex];
  const progress = ((currentIndex + 1) / questions.length) * 100;
  const qType = current.question_type === 'mixed' ? 'mcq' : current.question_type;
  const hasAnswer = Boolean(answers[current.id]?.trim());
  const subjectLabel =
    activeQuiz.subject?.trim() ||
    activeQuiz.title?.replace(/\s*—?\s*Quiz$/i, '').trim() ||
    'General';

  const selectAnswer = (answer: string) => {
    setAnswers((prev) => ({ ...prev, [current.id]: answer }));
  };

  const handleNext = async () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
      return;
    }

    const answerList = questions.map((q) => ({
      question_id: q.id,
      user_answer: answers[q.id] ?? '',
    }));

    const timeTaken = Math.round((Date.now() - startTime) / 1000);
    await submitQuiz(quizId, answerList, timeTaken);
    navigation.replace('QuizResult', { quizId });
  };

  return (
    <ScreenWrapper scrollable={false} padded={false}>
      <View style={styles.container}>
        <View style={styles.progressHeader}>
          <View style={styles.progressTop}>
            <Text style={styles.progressText}>
              Question {currentIndex + 1} of {questions.length}
            </Text>
            <Text style={styles.subject}>{subjectLabel}</Text>
          </View>
          <Text style={styles.quizTitle} numberOfLines={1}>
            {activeQuiz.title}
          </Text>
          <View style={styles.progressBar}>
            <View style={[styles.progressFill, { width: `${progress}%` }]} />
          </View>
        </View>

        <ScrollView
          style={styles.contentScroll}
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          <AppCard style={styles.questionCard}>
            {current.topic ? <Text style={styles.topic}>{current.topic}</Text> : null}
            <Text style={styles.typeBadge}>{qType.replace('_', ' ').toUpperCase()}</Text>
            <Text style={styles.question}>{current.question_text}</Text>
          </AppCard>

          <View style={styles.options}>
            {isTextQuestion(qType) ? (
              <TextInput
                mode="outlined"
                placeholder={
                  qType === 'fill_blank' ? 'Fill in the blank...' : 'Type your answer...'
                }
                value={answers[current.id] ?? ''}
                onChangeText={selectAnswer}
                style={styles.textInput}
                multiline={qType === 'short_answer'}
                numberOfLines={qType === 'short_answer' ? 3 : 1}
              />
            ) : current.options?.length ? (
              current.options.map((option) => {
                const selected = answers[current.id] === option;
                return (
                  <TouchableOpacity
                    key={option}
                    style={[styles.option, selected && styles.optionSelected]}
                    onPress={() => selectAnswer(option)}
                    activeOpacity={0.7}
                  >
                    <RadioButton
                      value={option}
                      status={selected ? 'checked' : 'unchecked'}
                      onPress={() => selectAnswer(option)}
                      color={colors.primary}
                    />
                    <Text style={[styles.optionText, selected && styles.optionTextSelected]}>
                      {option}
                    </Text>
                  </TouchableOpacity>
                );
              })
            ) : (
              <TextInput
                mode="outlined"
                placeholder="Type your answer..."
                value={answers[current.id] ?? ''}
                onChangeText={selectAnswer}
                style={styles.textInput}
              />
            )}
          </View>
        </ScrollView>

        <View style={styles.footer}>
          {currentIndex > 0 ? (
            <AppButton
              label="Previous"
              mode="outlined"
              onPress={() => setCurrentIndex(currentIndex - 1)}
              style={styles.navBtn}
            />
          ) : (
            <View style={styles.navBtn} />
          )}
          <AppButton
            label={currentIndex === questions.length - 1 ? 'Submit' : 'Next'}
            onPress={handleNext}
            loading={isSubmitting}
            disabled={!hasAnswer}
            style={styles.navBtn}
          />
        </View>
      </View>
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  container: {
    flex: 1,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
  },
  progressHeader: {
    marginBottom: spacing.lg,
  },
  progressTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  progressText: {
    ...typography.caption,
    color: colors.textSecondary,
  },
  subject: {
    ...typography.caption,
    color: colors.primary,
    fontWeight: '700',
    maxWidth: '50%',
    textAlign: 'right',
  },
  quizTitle: {
    ...typography.caption,
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  progressBar: {
    height: 6,
    backgroundColor: colors.surfaceAlt,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: colors.primary,
    borderRadius: 3,
  },
  contentScroll: {
    flex: 1,
  },
  content: {
    flexGrow: 1,
    paddingBottom: spacing.md,
  },
  questionCard: {
    padding: spacing.lg,
    marginBottom: spacing.lg,
  },
  topic: {
    ...typography.caption,
    color: colors.primary,
    fontWeight: '600',
    marginBottom: spacing.xs,
  },
  typeBadge: {
    ...typography.caption,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  question: {
    ...typography.h3,
    color: colors.text,
    lineHeight: 26,
  },
  options: {
    gap: spacing.sm,
  },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.white,
    flexShrink: 0,
  },
  optionSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.primaryLight,
  },
  optionText: {
    ...typography.bodySmall,
    color: colors.text,
    flex: 1,
  },
  optionTextSelected: {
    color: colors.primaryDark,
    fontWeight: '500',
  },
  textInput: {
    backgroundColor: colors.white,
  },
  footer: {
    flexDirection: 'row',
    gap: spacing.sm,
    paddingVertical: spacing.md,
    paddingBottom: spacing.sm,
  },
  navBtn: {
    flex: 1,
  },
});
