import { useCallback, useMemo, useState } from 'react';
import { Alert, FlatList, Pressable, StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator, RadioButton, Searchbar } from 'react-native-paper';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, spacing, typography } from '@/core/theme';
import { fontScale, moderateScale } from '@/core/theme/responsive';
import { getErrorMessage } from '@/data/api/client';
import type { QuizAttempt } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import EmptyState from '@/presentation/components/EmptyState';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import { useQuizStore } from '@/store/quizStore';
import { useUIStore } from '@/store/uiStore';

type Nav = NativeStackNavigationProp<RootStackParamList, 'QuizHistory'>;

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

function formatTime(seconds?: number | null) {
  if (!seconds) return '';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function scoreColor(score: number) {
  if (score >= 75) return colors.success;
  if (score >= 50) return colors.warning;
  return colors.error;
}

function scoreTint(score: number) {
  if (score >= 75) return colors.successLight;
  if (score >= 50) return colors.warningLight;
  return colors.errorLight;
}

export default function QuizHistoryScreen() {
  const navigation = useNavigation<Nav>();
  const {
    history,
    historySubjects,
    isLoading,
    error,
    fetchHistory,
    fetchHistorySubjects,
    clearHistory,
    deleteAttempt,
  } = useQuizStore();
  const showSnackbar = useUIStore((s) => s.showSnackbar);
  const [search, setSearch] = useState('');
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(true);

  const selectedSubject = historySubjects.find((s) => s.id === selectedSubjectId) ?? null;

  const loadSubjects = useCallback(async () => {
    try {
      await fetchHistorySubjects();
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    }
  }, [fetchHistorySubjects, showSnackbar]);

  useFocusEffect(
    useCallback(() => {
      void loadSubjects();
      if (selectedSubjectId && !pickerOpen) {
        void fetchHistory(selectedSubjectId, search || undefined);
      }
    }, [loadSubjects, fetchHistory, selectedSubjectId, pickerOpen])
  );

  const handleSelectSubject = (subjectId: string) => {
    if (subjectId !== selectedSubjectId) {
      clearHistory();
    }
    setSelectedSubjectId(subjectId);
    setSearch('');
    setPickerOpen(false);
  };

  const handleChangeSubject = () => {
    setPickerOpen(true);
  };

  const summary = useMemo(() => {
    if (!history.length) return { count: 0, avg: 0, best: 0 };
    const scores = history.map((h) => h.score);
    const avg = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    const best = Math.round(Math.max(...scores));
    return { count: history.length, avg, best };
  }, [history]);

  const handleDelete = (item: QuizAttempt) => {
    Alert.alert('Delete attempt?', `Remove ${item.quiz_title ?? 'quiz'} from history?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await deleteAttempt(item.id);
            showSnackbar('Attempt deleted', 'success');
          } catch (err) {
            showSnackbar(getErrorMessage(err), 'error');
          }
        },
      },
    ]);
  };

  const renderItem = ({ item }: { item: QuizAttempt }) => {
    const score = Math.round(item.score);
    const color = scoreColor(score);
    return (
      <AppCard
        style={styles.card}
        onPress={() => navigation.navigate('QuizAttemptReview', { attemptId: item.id })}
      >
        <View style={[styles.accent, { backgroundColor: color }]} />
        <View style={styles.row}>
          <View style={[styles.scoreBadge, { backgroundColor: scoreTint(score) }]}>
            <Text style={[styles.scoreText, { color }]}>{score}%</Text>
          </View>

          <View style={styles.info}>
            <Text style={styles.title} numberOfLines={1}>
              {item.quiz_title ?? 'Quiz'}
            </Text>

            <View style={styles.tagRow}>
              <View style={styles.subjectPill}>
                <Ionicons name="folder-outline" size={11} color={colors.primaryDark} />
                <Text style={styles.subjectPillText} numberOfLines={1}>
                  {item.subject ?? 'General'}
                </Text>
              </View>
              {item.difficulty ? (
                <View style={styles.diffPill}>
                  <Text style={styles.diffPillText}>{item.difficulty}</Text>
                </View>
              ) : null}
            </View>

            <View style={styles.metaRow}>
              <View style={styles.metaItem}>
                <Ionicons name="checkmark-circle-outline" size={13} color={colors.textMuted} />
                <Text style={styles.metaText}>
                  {item.correct_count}/{item.total_count}
                </Text>
              </View>
              <View style={styles.metaItem}>
                <Ionicons name="calendar-outline" size={13} color={colors.textMuted} />
                <Text style={styles.metaText}>{formatDate(item.completed_at)}</Text>
              </View>
              {item.time_taken_seconds ? (
                <View style={styles.metaItem}>
                  <Ionicons name="time-outline" size={13} color={colors.textMuted} />
                  <Text style={styles.metaText}>{formatTime(item.time_taken_seconds)}</Text>
                </View>
              ) : null}
            </View>
          </View>

          <Pressable onPress={() => handleDelete(item)} hitSlop={8} style={styles.deleteBtn}>
            <Ionicons name="trash-outline" size={18} color={colors.textMuted} />
          </Pressable>
        </View>
      </AppCard>
    );
  };

  const renderHeader = () => {
    if (!history.length) return null;
    return (
      <View style={styles.summaryRow}>
        <View style={styles.summaryItem}>
          <Text style={styles.summaryValue}>{summary.count}</Text>
          <Text style={styles.summaryLabel}>Attempts</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryItem}>
          <Text style={[styles.summaryValue, { color: scoreColor(summary.avg) }]}>
            {summary.avg}%
          </Text>
          <Text style={styles.summaryLabel}>Average</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryItem}>
          <Text style={[styles.summaryValue, { color: colors.success }]}>{summary.best}%</Text>
          <Text style={styles.summaryLabel}>Best</Text>
        </View>
      </View>
    );
  };

  const renderSubject = ({ item }: { item: { id: string; name: string } }) => {
    const active = selectedSubjectId === item.id;
    return (
      <Pressable
        onPress={() => handleSelectSubject(item.id)}
        accessibilityRole="radio"
        accessibilityState={{ selected: active }}
        style={[styles.subjectRow, active && styles.subjectRowActive]}
      >
        <RadioButton
          value={item.id}
          status={active ? 'checked' : 'unchecked'}
          onPress={() => handleSelectSubject(item.id)}
          color={colors.primary}
        />
        <Text style={[styles.subjectName, active && styles.subjectNameActive]}>{item.name}</Text>
      </Pressable>
    );
  };

  if (error && !historySubjects.length && pickerOpen) {
    return (
      <ScreenWrapper scrollable={false} padded={false}>
        <View style={styles.centered}>
          <EmptyState
            icon="alert-circle-outline"
            title="Unable to load history. Please try again."
            subtitle=""
          />
          <AppButton label="Try again" onPress={loadSubjects} style={styles.retryBtn} />
        </View>
      </ScreenWrapper>
    );
  }

  return (
    <ScreenWrapper scrollable={false} padded={false}>
      <View style={styles.header}>
        <Text style={styles.pageTitle}>History</Text>
        {selectedSubject && !pickerOpen ? (
          <View style={styles.selectedBox}>
            <Text style={styles.selectedCaption}>Selected Subject</Text>
            <Text style={styles.selectedName}>{selectedSubject.name}</Text>
            <AppButton
              label="Change Subject"
              mode="outlined"
              onPress={handleChangeSubject}
              style={styles.changeBtn}
            />
          </View>
        ) : (
          <Text style={styles.selectLabel}>Select Subject</Text>
        )}
      </View>

      {pickerOpen ? (
        isLoading && !historySubjects.length ? (
          <View style={styles.centered}>
            <ActivityIndicator size="large" color={colors.primary} />
            <Text style={styles.loadingText}>Loading history...</Text>
          </View>
        ) : historySubjects.length === 0 ? (
          <EmptyState
            icon="time-outline"
            title="No history available yet."
            subtitle="Complete a quiz to see your attempts here"
          />
        ) : (
          <FlatList
            data={historySubjects}
            keyExtractor={(item) => item.id}
            renderItem={renderSubject}
            contentContainerStyle={styles.subjectList}
            showsVerticalScrollIndicator={false}
          />
        )
      ) : error && !history.length ? (
        <View style={styles.centered}>
          <EmptyState
            icon="alert-circle-outline"
            title="Unable to load history. Please try again."
            subtitle=""
          />
          <AppButton
            label="Try again"
            onPress={() => selectedSubjectId && fetchHistory(selectedSubjectId, search || undefined)}
            style={styles.retryBtn}
          />
        </View>
      ) : (
        <>
          <View style={styles.filters}>
            <Text style={styles.sectionTitle}>
              {selectedSubject ? `${selectedSubject.name} History` : 'History'}
            </Text>
            <Searchbar
              placeholder="Search quizzes..."
              value={search}
              onChangeText={setSearch}
              onSubmitEditing={() =>
                selectedSubjectId && fetchHistory(selectedSubjectId, search || undefined)
              }
              style={styles.search}
              inputStyle={styles.searchInput}
              icon={() => <Ionicons name="search-outline" size={18} color={colors.textMuted} />}
              clearIcon={() => <Ionicons name="close-outline" size={18} color={colors.textMuted} />}
            />
          </View>

          {isLoading && !history.length ? (
            <View style={styles.centered}>
              <ActivityIndicator size="large" color={colors.primary} />
              <Text style={styles.loadingText}>Loading history...</Text>
            </View>
          ) : (
            <FlatList
              data={history}
              keyExtractor={(item) => item.id}
              renderItem={renderItem}
              ListHeaderComponent={renderHeader}
              contentContainerStyle={styles.list}
              onRefresh={() =>
                selectedSubjectId && fetchHistory(selectedSubjectId, search || undefined)
              }
              refreshing={isLoading}
              showsVerticalScrollIndicator={false}
              ListEmptyComponent={
                <EmptyState
                  icon="time-outline"
                  title="No history available for this subject."
                  subtitle="Complete a quiz in this subject to see attempts here"
                />
              }
            />
          )}
        </>
      )}
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
    paddingBottom: spacing.xs,
    backgroundColor: colors.background,
  },
  pageTitle: {
    ...typography.h2,
    color: colors.text,
  },
  selectLabel: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '700',
    textTransform: 'uppercase',
    marginTop: spacing.md,
    marginBottom: spacing.xs,
  },
  selectedBox: {
    backgroundColor: colors.primaryLight,
    borderRadius: radius.md,
    padding: spacing.sm,
    marginTop: spacing.sm,
  },
  selectedCaption: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  selectedName: {
    ...typography.label,
    color: colors.primary,
    fontWeight: '700',
    marginTop: 2,
  },
  changeBtn: {
    marginTop: spacing.sm,
    alignSelf: 'flex-start',
  },
  subjectList: {
    padding: spacing.md,
    paddingTop: spacing.xs,
  },
  subjectRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingVertical: spacing.xs,
    paddingRight: spacing.sm,
    marginBottom: spacing.sm,
  },
  subjectRowActive: {
    borderColor: colors.primary,
    backgroundColor: colors.primaryLight,
  },
  subjectName: {
    ...typography.label,
    color: colors.text,
    flex: 1,
  },
  subjectNameActive: {
    color: colors.primary,
    fontWeight: '700',
  },
  sectionTitle: {
    ...typography.label,
    color: colors.text,
    fontWeight: '700',
    marginBottom: spacing.sm,
  },
  loadingText: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  retryBtn: {
    alignSelf: 'center',
    marginTop: spacing.md,
  },
  filters: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: spacing.xs,
    backgroundColor: colors.background,
  },
  search: {
    marginBottom: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    elevation: 0,
  },
  searchInput: {
    fontSize: 14,
    minHeight: 0,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  list: {
    padding: spacing.md,
    paddingTop: spacing.sm,
    flexGrow: 1,
  },
  summaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.primaryLight,
    borderRadius: radius.lg,
    paddingVertical: spacing.md,
    marginBottom: spacing.md,
  },
  summaryItem: {
    flex: 1,
    alignItems: 'center',
  },
  summaryDivider: {
    width: 1,
    height: 28,
    backgroundColor: colors.primary,
    opacity: 0.2,
  },
  summaryValue: {
    ...typography.h3,
    color: colors.primaryDark,
  },
  summaryLabel: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
  },
  card: {
    padding: spacing.md,
    paddingLeft: spacing.md + 4,
    marginBottom: spacing.sm,
    overflow: 'hidden',
  },
  accent: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    width: 4,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  scoreBadge: {
    width: moderateScale(54),
    height: moderateScale(54),
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scoreText: {
    fontSize: fontScale(16),
    fontWeight: '800',
  },
  info: {
    flex: 1,
  },
  title: {
    ...typography.label,
    color: colors.text,
  },
  tagRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    marginTop: 4,
  },
  subjectPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    backgroundColor: colors.primaryLight,
    paddingVertical: 2,
    paddingHorizontal: 8,
    borderRadius: radius.full,
    flexShrink: 1,
    maxWidth: '60%',
  },
  subjectPillText: {
    ...typography.caption,
    fontSize: 11,
    color: colors.primaryDark,
    fontWeight: '600',
  },
  diffPill: {
    backgroundColor: colors.surfaceAlt,
    paddingVertical: 2,
    paddingHorizontal: 8,
    borderRadius: radius.full,
  },
  diffPillText: {
    ...typography.caption,
    fontSize: 11,
    color: colors.textSecondary,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginTop: 6,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  metaText: {
    ...typography.caption,
    color: colors.textMuted,
  },
  deleteBtn: {
    padding: spacing.xs,
    alignSelf: 'flex-start',
  },
});
