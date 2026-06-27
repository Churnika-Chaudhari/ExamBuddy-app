import { useCallback, useMemo, useState } from 'react';
import { Alert, FlatList, Pressable, StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator, Searchbar } from 'react-native-paper';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, spacing, typography } from '@/core/theme';
import { fontScale, moderateScale } from '@/core/theme/responsive';
import { getErrorMessage } from '@/data/api/client';
import type { QuizAttempt } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
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
  const { history, subjects, isLoading, fetchHistory, fetchSubjects, deleteAttempt } =
    useQuizStore();
  const showSnackbar = useUIStore((s) => s.showSnackbar);
  const [search, setSearch] = useState('');
  const [subjectFilter, setSubjectFilter] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      fetchSubjects();
      fetchHistory(subjectFilter ?? undefined, search || undefined);
    }, [fetchHistory, fetchSubjects, subjectFilter, search])
  );

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

  return (
    <ScreenWrapper scrollable={false} padded={false}>
      <View style={styles.filters}>
        <Searchbar
          placeholder="Search quizzes..."
          value={search}
          onChangeText={setSearch}
          onSubmitEditing={() => fetchHistory(subjectFilter ?? undefined, search)}
          style={styles.search}
          inputStyle={styles.searchInput}
          icon={() => <Ionicons name="search-outline" size={18} color={colors.textMuted} />}
          clearIcon={() => <Ionicons name="close-outline" size={18} color={colors.textMuted} />}
        />
        <FlatList
          horizontal
          data={[{ id: 'all', name: 'All' }, ...subjects]}
          keyExtractor={(item) => item.id}
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chipRow}
          renderItem={({ item }) => {
            const isAll = item.id === 'all';
            const active = isAll ? !subjectFilter : subjectFilter === item.name;
            return (
              <Pressable
                onPress={() => {
                  setSubjectFilter(isAll ? null : item.name);
                  fetchHistory(isAll ? undefined : item.name, search || undefined);
                }}
                style={[styles.filterChip, active && styles.filterChipActive]}
              >
                <Text style={[styles.filterChipText, active && styles.filterChipTextActive]}>
                  {item.name}
                </Text>
              </Pressable>
            );
          }}
        />
      </View>

      {isLoading && !history.length ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : (
        <FlatList
          data={history}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          ListHeaderComponent={renderHeader}
          contentContainerStyle={styles.list}
          onRefresh={() => fetchHistory(subjectFilter ?? undefined, search || undefined)}
          refreshing={isLoading}
          showsVerticalScrollIndicator={false}
          ListEmptyComponent={
            <EmptyState
              icon="time-outline"
              title="No quiz history"
              subtitle="Complete a quiz to see your attempts and track your progress here"
            />
          }
        />
      )}
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  filters: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
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
  chipRow: {
    gap: spacing.xs,
    paddingBottom: spacing.xs,
  },
  filterChip: {
    paddingVertical: 6,
    paddingHorizontal: spacing.md,
    borderRadius: radius.full,
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.border,
    marginRight: spacing.xs,
  },
  filterChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  filterChipText: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '600',
  },
  filterChipTextActive: {
    color: colors.white,
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
