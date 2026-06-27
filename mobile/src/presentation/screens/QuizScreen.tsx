import { useCallback, useState } from 'react';
import { Alert, FlatList, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator, Menu, Chip, SegmentedButtons } from 'react-native-paper';
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
import { useQuizStore } from '@/store/quizStore';
import { useUIStore } from '@/store/uiStore';

type Nav = NativeStackNavigationProp<RootStackParamList>;

const DIFFICULTIES: { value: QuizDifficulty; label: string }[] = [
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
];

const QUESTION_COUNTS = [10, 20, 30];

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

  const [menuOpen, setMenuOpen] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState<QuizSubject | null>(null);
  const [difficulty, setDifficulty] = useState<QuizDifficulty>('medium');
  const [numQuestions, setNumQuestions] = useState(10);

  useFocusEffect(
    useCallback(() => {
      fetchQuizzes();
      fetchSubjects().catch(() => undefined);
    }, [fetchQuizzes, fetchSubjects])
  );

  const handleGenerate = async () => {
    if (!selectedSubject) return;
    try {
      const topics = await fetchSubjectTopics(selectedSubject.id);
      const topicNames = topics.map((t) => t.topic);
      const quiz = await generateQuiz({
        subject: selectedSubject.name,
        topics: topicNames,
        difficulty,
        num_questions: numQuestions,
        quiz_type: 'mixed',
        title: `${selectedSubject.name} Quiz`,
      });
      showSnackbar('Quiz generated!', 'success');
      navigation.navigate('QuizPlay', { quizId: quiz.id });
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
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
          <Text style={styles.quizTitle} numberOfLines={1}>
            {item.title}
          </Text>
          <Text style={styles.quizMeta}>
            {item.subject ? `${item.subject} · ` : ''}
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

  const canGenerate = Boolean(selectedSubject) && !isGenerating;

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.title}>Quiz Generator</Text>
          <Text style={styles.subtitle}>
            Subjects are loaded automatically from your uploaded PYQ papers
          </Text>
        </View>

        <AppCard style={styles.configCard}>
          <Text style={styles.fieldLabel}>Subject</Text>
          <Menu
            visible={menuOpen}
            onDismiss={() => setMenuOpen(false)}
            anchor={
              <AppButton
                label={selectedSubject?.name ?? 'Select Subject'}
                mode="outlined"
                onPress={() => setMenuOpen(true)}
                icon="chevron-down"
                style={styles.dropdownBtn}
              />
            }
          >
            {subjects.length === 0 ? (
              <Menu.Item title="No subjects — upload PYQs first" disabled />
            ) : (
              subjects.map((s) => (
                <View key={s.id} style={styles.menuRow}>
                  <Pressable
                    style={styles.menuSelect}
                    onPress={() => {
                      setSelectedSubject(s);
                      setMenuOpen(false);
                    }}
                  >
                    <Text style={styles.menuName} numberOfLines={1}>
                      {s.name}
                    </Text>
                    <Text style={styles.menuMeta}>
                      {s.topic_count} topics · {s.pyq_count} PYQs
                    </Text>
                  </Pressable>
                  <Pressable
                    hitSlop={8}
                    onPress={() => confirmDeleteSubject(s)}
                    style={styles.menuDelete}
                  >
                    <Ionicons name="trash-outline" size={16} color={colors.error} />
                  </Pressable>
                </View>
              ))
            )}
          </Menu>

          {selectedSubject ? (
            <Text style={styles.subjectMeta}>
              {selectedSubject.pyq_count} PYQ papers · {selectedSubject.topic_count} topics
            </Text>
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
            label="Generate Quiz"
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
              if (!selectedSubject) {
                showSnackbar('Select a subject first for subject-wise analysis', 'error');
                return;
              }
              navigation.navigate('QuizAnalysis', { subject: selectedSubject.name });
            }}
            icon="analytics-outline"
            style={styles.quickBtn}
            disabled={!selectedSubject}
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
      </ScrollView>

      {isLoading && !quizzes.length ? (
        <View style={styles.centeredInline}>
          <ActivityIndicator size="small" color={colors.primary} />
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
          ListEmptyComponent={
            <EmptyState
              icon="help-circle-outline"
              title="No quizzes yet"
              subtitle="Select a subject and tap Generate Quiz"
            />
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    paddingBottom: spacing.sm,
  },
  header: {
    padding: spacing.md,
    paddingTop: spacing.lg,
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
  dropdownBtn: {
    justifyContent: 'flex-start',
  },
  menuRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    minWidth: 240,
  },
  menuSelect: {
    flex: 1,
    paddingVertical: spacing.xs,
  },
  menuName: {
    ...typography.bodySmall,
    color: colors.text,
    fontWeight: '600',
  },
  menuMeta: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 1,
  },
  menuDelete: {
    padding: spacing.sm,
  },
  subjectMeta: {
    ...typography.caption,
    color: colors.primary,
    marginTop: spacing.xs,
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
    minWidth: 52,
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
  },
  quizTitle: {
    ...typography.label,
    color: colors.text,
  },
  quizMeta: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
  },
  centeredInline: {
    padding: spacing.lg,
    alignItems: 'center',
  },
});
