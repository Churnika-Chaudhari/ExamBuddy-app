import { useCallback, useState } from 'react';
import { Alert, FlatList, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator, Chip, SegmentedButtons } from 'react-native-paper';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, spacing, typography } from '@/core/theme';
import { getErrorMessage } from '@/data/api/client';
import type { Quiz, QuizDifficulty, QuizSubject } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import EmptyState from '@/presentation/components/EmptyState';
import LoadingOverlay from '@/presentation/components/LoadingOverlay';
import ScreenWrapper, { TAB_SCREEN_EDGES } from '@/presentation/components/ScreenWrapper';
import { useQuizStore } from '@/store/quizStore';
import { useUIStore } from '@/store/uiStore';

type Nav = NativeStackNavigationProp<RootStackParamList>;

const DIFFICULTIES: { value: QuizDifficulty; label: string }[] = [
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
];

const QUESTION_COUNTS = [10, 20, 30];

function quizSubjectLabel(quiz: Quiz): string {
  if (quiz.subject?.trim()) return quiz.subject.trim();
  const fromTitle = quiz.title?.replace(/\s*—?\s*Quiz$/i, '').trim();
  return fromTitle || 'General';
}

export default function QuizScreen() {
  const navigation = useNavigation<Nav>();
  const {
    quizzes,
    subjects,
    isLoading,
    isGenerating,
    fetchQuizzes,
    fetchSubjects,
    fetchSubjectTopics,
    generateQuiz,
    deleteQuiz,
    clearQuizzes,
    deleteSubject,
  } = useQuizStore();
  const showSnackbar = useUIStore((s) => s.showSnackbar);

  const [selectedSubject, setSelectedSubject] = useState<QuizSubject | null>(null);
  const [difficulty, setDifficulty] = useState<QuizDifficulty>('medium');
  const [numQuestions, setNumQuestions] = useState(10);
  const [generatingLabel, setGeneratingLabel] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      fetchQuizzes();
      fetchSubjects().catch(() => undefined);
    }, [fetchQuizzes, fetchSubjects])
  );

  const handleGenerate = async () => {
    if (!selectedSubject?.name) return;
    try {
      setGeneratingLabel(`Generating ${selectedSubject.name} quiz…`);
      const { topics, subject, analysisIds } = await fetchSubjectTopics(selectedSubject.id);
      const topicNames = topics.map((t) => t.topic);
      const quiz = await generateQuiz({
        subject: subject || selectedSubject.name,
        analysis_id: analysisIds[0],
        topics: topicNames,
        difficulty,
        num_questions: numQuestions,
        quiz_type: 'mixed',
        title: `${subject || selectedSubject.name} Quiz`,
      });
      showSnackbar(`${quizSubjectLabel(quiz)} quiz generated!`, 'success');
      navigation.navigate('QuizPlay', { quizId: quiz.id });
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    } finally {
      setGeneratingLabel(null);
    }
  };

  const confirmDeleteSubject = (s: QuizSubject) => {
    Alert.alert(
      'Remove subject?',
      `Remove "${s.name}" from the subject list? This won't delete your uploaded papers.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteSubject(s.id);
              if (selectedSubject?.id === s.id) setSelectedSubject(null);
              showSnackbar('Subject removed', 'success');
            } catch (err) {
              showSnackbar(getErrorMessage(err), 'error');
            }
          },
        },
      ]
    );
  };

  const confirmClearAll = () => {
    if (!quizzes.length) return;
    Alert.alert(
      'Clear recent quizzes?',
      'This removes all generated quizzes from the list. Your quiz history and analytics stay intact.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear All',
          style: 'destructive',
          onPress: async () => {
            try {
              await clearQuizzes();
              showSnackbar('Recent quizzes cleared', 'success');
            } catch (err) {
              showSnackbar(getErrorMessage(err), 'error');
            }
          },
        },
      ]
    );
  };

  const confirmDelete = (item: Quiz) => {
    Alert.alert('Delete quiz?', `Remove "${item.title}" from recent quizzes?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await deleteQuiz(item.id);
            showSnackbar('Quiz deleted', 'success');
          } catch (err) {
            showSnackbar(getErrorMessage(err), 'error');
          }
        },
      },
    ]);
  };

  const renderQuiz = ({ item }: { item: Quiz }) => (
    <AppCard
      style={styles.quizCard}
      onPress={() => navigation.navigate('QuizPlay', { quizId: item.id })}
    >
      <View style={styles.quizRow}>
        <View style={styles.quizIcon}>
          <Ionicons name="help-circle" size={22} color={colors.primary} />
        </View>
        <View style={styles.quizInfo}>
          <Text style={styles.quizSubject} numberOfLines={1}>
            {quizSubjectLabel(item)}
          </Text>
          <Text style={styles.quizTitle} numberOfLines={1}>
            {item.title}
          </Text>
          <Text style={styles.quizMeta}>
            {item.total_questions} questions
            {item.difficulty ? ` · ${item.difficulty}` : ''}
          </Text>
        </View>
        <Pressable onPress={() => confirmDelete(item)} hitSlop={8} style={styles.quizDelete}>
          <Ionicons name="trash-outline" size={18} color={colors.textMuted} />
        </Pressable>
      </View>
    </AppCard>
  );

  const canGenerate = Boolean(selectedSubject?.name) && !isGenerating;

  const listHeader = (
    <>
      <LoadingOverlay visible={isGenerating} message={generatingLabel ?? 'Generating quiz…'} />

      <View style={styles.header}>
        <Text style={styles.title}>Quiz Generator</Text>
        <Text style={styles.subtitle}>
          Subjects are loaded automatically from your uploaded PYQ papers
        </Text>
      </View>

      <AppCard style={styles.configCard}>
        <Text style={styles.fieldLabel}>Subject</Text>
        {subjects.length === 0 ? (
          <Text style={styles.noSubjects}>No subjects yet — upload and analyze PYQ papers first</Text>
        ) : (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.subjectRow}
          >
            {subjects.map((s) => {
              const active = selectedSubject?.id === s.id;
              return (
                <View key={s.id} style={styles.subjectChipWrap}>
                  <Chip
                    selected={active}
                    onPress={() => setSelectedSubject(s)}
                    style={[styles.subjectChip, active && styles.subjectChipActive]}
                    textStyle={active ? styles.subjectChipTextActive : styles.subjectChipText}
                  >
                    {s.name}
                  </Chip>
                  <Pressable hitSlop={8} onPress={() => confirmDeleteSubject(s)} style={styles.chipDelete}>
                    <Ionicons name="close-circle" size={16} color={colors.textMuted} />
                  </Pressable>
                </View>
              );
            })}
          </ScrollView>
        )}

        {selectedSubject ? (
          <View style={styles.selectedSubjectBox}>
            <Ionicons name="school-outline" size={18} color={colors.primary} />
            <View style={styles.selectedSubjectInfo}>
              <Text style={styles.selectedSubjectName}>{selectedSubject.name}</Text>
              <Text style={styles.selectedSubjectMeta}>
                {selectedSubject.pyq_count} PYQ papers · {selectedSubject.topic_count} topics
              </Text>
            </View>
          </View>
        ) : subjects.length > 0 ? (
          <Text style={styles.pickHint}>Tap a subject above to start</Text>
        ) : null}

        <Text style={styles.fieldLabel}>Difficulty</Text>
        <SegmentedButtons
          value={difficulty}
          onValueChange={(v) => setDifficulty(v as QuizDifficulty)}
          buttons={DIFFICULTIES.map((d) => ({ value: d.value, label: d.label }))}
          style={styles.segment}
        />

        <Text style={styles.fieldLabel}>Number of Questions</Text>
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
          label={
            selectedSubject?.name
              ? `Generate ${selectedSubject.name} Quiz`
              : 'Generate Quiz'
          }
          onPress={handleGenerate}
          loading={isGenerating}
          disabled={!canGenerate}
          icon="lightning-bolt"
          style={styles.generateBtn}
        />
      </AppCard>

      <View style={styles.quickRow}>
        <AppButton
          label="History"
          mode="outlined"
          onPress={() => navigation.navigate('QuizHistory')}
          icon="time-outline"
          style={styles.quickBtn}
        />
        <AppButton
          label="Analysis"
          mode="outlined"
          onPress={() => {
            if (!selectedSubject?.name) {
              showSnackbar('Select a subject first for subject-wise analysis', 'error');
              return;
            }
            navigation.navigate('QuizAnalysis', { subject: selectedSubject.name });
          }}
          icon="analytics-outline"
          style={styles.quickBtn}
          disabled={!selectedSubject?.name}
        />
      </View>

      <View style={styles.recentHeader}>
        <Text style={styles.sectionLabel}>Recent Quizzes</Text>
        {quizzes.length > 0 ? (
          <Pressable onPress={confirmClearAll} hitSlop={8} style={styles.clearAllBtn}>
            <Ionicons name="trash-outline" size={14} color={colors.error} />
            <Text style={styles.clearAllText}>Clear All</Text>
          </Pressable>
        ) : null}
      </View>
    </>
  );

  return (
    <ScreenWrapper scrollable={false} padded={false} edges={TAB_SCREEN_EDGES}>
      {isLoading && !quizzes.length ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : (
        <FlatList
          data={quizzes}
          keyExtractor={(item) => item.id}
          renderItem={renderQuiz}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          onRefresh={fetchQuizzes}
          refreshing={isLoading}
          ListHeaderComponent={listHeader}
          ListEmptyComponent={
            <EmptyState
              icon="help-circle-outline"
              title="No quizzes yet"
              subtitle="Select a subject and tap Generate Quiz"
            />
          }
        />
      )}
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  header: {
    padding: spacing.md,
    paddingBottom: 0,
  },
  title: {
    ...typography.h2,
    color: colors.text,
  },
  subtitle: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: 4,
    marginBottom: spacing.md,
    lineHeight: 20,
  },
  configCard: {
    marginHorizontal: spacing.md,
    marginBottom: spacing.md,
    padding: spacing.md,
  },
  fieldLabel: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '700',
    textTransform: 'uppercase',
    marginBottom: spacing.sm,
    marginTop: spacing.sm,
  },
  noSubjects: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  subjectRow: {
    gap: spacing.sm,
    paddingRight: spacing.md,
    paddingBottom: spacing.xs,
  },
  subjectChipWrap: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  subjectChip: {
    backgroundColor: colors.surface,
  },
  subjectChipActive: {
    backgroundColor: colors.primaryLight,
  },
  subjectChipText: {
    color: colors.text,
  },
  subjectChipTextActive: {
    color: colors.primary,
    fontWeight: '700',
  },
  chipDelete: {
    marginLeft: -6,
    marginRight: spacing.xs,
  },
  selectedSubjectBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    backgroundColor: colors.primaryLight,
    borderRadius: radius.md,
    padding: spacing.sm,
    marginTop: spacing.sm,
    marginBottom: spacing.sm,
  },
  selectedSubjectInfo: {
    flex: 1,
    minWidth: 0,
  },
  selectedSubjectName: {
    ...typography.label,
    color: colors.primary,
    fontWeight: '700',
  },
  selectedSubjectMeta: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
  },
  pickHint: {
    ...typography.caption,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  segment: {
    marginBottom: spacing.sm,
  },
  countRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  countChip: {
    flex: 1,
  },
  generateBtn: {
    marginTop: spacing.xs,
  },
  quickRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  quickBtn: {
    flex: 1,
  },
  recentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    marginBottom: spacing.xs,
  },
  sectionLabel: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  clearAllBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: spacing.xs,
  },
  clearAllText: {
    ...typography.caption,
    color: colors.error,
    fontWeight: '700',
  },
  quizDelete: {
    padding: spacing.xs,
  },
  list: {
    padding: spacing.md,
    paddingTop: 0,
    flexGrow: 1,
    paddingBottom: spacing.lg,
  },
  quizCard: {
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  quizRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  quizIcon: {
    width: 40,
    height: 40,
    borderRadius: radius.md,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.md,
  },
  quizInfo: {
    flex: 1,
    minWidth: 0,
  },
  quizSubject: {
    ...typography.caption,
    color: colors.primary,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  quizTitle: {
    ...typography.label,
    color: colors.text,
    marginTop: 2,
  },
  quizMeta: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
  },
});
