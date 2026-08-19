import { useCallback, useEffect, useMemo, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { ActivityIndicator, Chip, Searchbar, SegmentedButtons, Text } from 'react-native-paper';
import { useNavigation, useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, spacing, typography } from '@/core/theme';
import { getErrorMessage } from '@/data/api/client';
import { subjectsApi } from '@/data/api/endpoints';
import type { SubjectModule, SubjectOverview, SubjectTopic } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppCard from '@/presentation/components/AppCard';
import EmptyState from '@/presentation/components/EmptyState';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import { useUIStore } from '@/store/uiStore';

type Route = RouteProp<RootStackParamList, 'ModuleTopics'>;
type Nav = NativeStackNavigationProp<RootStackParamList>;

type PriorityFilter = 'High' | 'Medium' | 'Low' | 'All';
type SortMode = 'priority' | 'occurred' | 'az';

const PRIORITY_META: Record<
  'High' | 'Medium' | 'Low',
  { label: string; color: string; bg: string; icon: keyof typeof Ionicons.glyphMap }
> = {
  High: { label: 'HIGH PRIORITY', color: colors.error, bg: colors.errorLight, icon: 'flame' },
  Medium: {
    label: 'MEDIUM PRIORITY',
    color: colors.warning,
    bg: colors.warningLight,
    icon: 'alert-circle',
  },
  Low: { label: 'LOW PRIORITY', color: colors.success, bg: colors.successLight, icon: 'leaf' },
};

function topicPriority(t: SubjectTopic): 'High' | 'Medium' | 'Low' {
  const raw = (t.priority || t.importance || 'Low').toString();
  if (/high/i.test(raw)) return 'High';
  if (/medium/i.test(raw)) return 'Medium';
  return 'Low';
}

function occurrenceOf(t: SubjectTopic): number {
  return t.occurrence_count ?? t.frequency ?? 0;
}

function paperCountOf(t: SubjectTopic): number {
  return t.paper_count ?? 0;
}

function topicLabel(t: SubjectTopic): string {
  return t.topic_name || t.topic;
}

function sortTopics(topics: SubjectTopic[], mode: SortMode): SubjectTopic[] {
  const rank = { High: 0, Medium: 1, Low: 2 };
  const copy = [...topics];
  copy.sort((a, b) => {
    if (mode === 'az') return topicLabel(a).localeCompare(topicLabel(b));
    if (mode === 'occurred') return occurrenceOf(b) - occurrenceOf(a);
    const askedDiff = Number(Boolean(b.asked ?? occurrenceOf(b) > 0)) - Number(Boolean(a.asked ?? occurrenceOf(a) > 0));
    if (askedDiff !== 0) return askedDiff;
    const pr = rank[topicPriority(a)] - rank[topicPriority(b)];
    if (pr !== 0) return pr;
    return occurrenceOf(b) - occurrenceOf(a);
  });
  return copy;
}

export default function ModuleTopicsScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { subjectId, subjectName, moduleId, moduleName, moduleNumber, analysisIds } = route.params;
  const showSnackbar = useUIStore((s) => s.showSnackbar);

  const [overview, setOverview] = useState<SubjectOverview | null>(null);
  const [module, setModule] = useState<SubjectModule | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<PriorityFilter>('All');
  const [sortMode, setSortMode] = useState<SortMode>('priority');
  const [search, setSearch] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await subjectsApi.getOverview(subjectId);
      const ov = data.data;
      setOverview(ov);
      const found =
        ov.modules?.find((m) => m.module_id === moduleId) ||
        ({
          module_id: moduleId,
          module_name: moduleName,
          display_name: moduleName,
          module_number: moduleNumber,
          topics: (ov.topics || []).filter(
            (t) => t.module_id === moduleId || (t.unit || '').includes(moduleName)
          ),
          topic_count: 0,
        } as SubjectModule);
      if (!found.topic_count) found.topic_count = found.topics?.length || 0;
      setModule(found);
      navigation.setOptions({ title: found.display_name || moduleName || 'Module Topics' });
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [subjectId, moduleId, moduleName, moduleNumber, navigation, showSnackbar]);

  useEffect(() => {
    load();
  }, [load]);

  const openTopic = (t: SubjectTopic) => {
    if (!overview) return;
    const occ = occurrenceOf(t);
    navigation.navigate('TopicStudyNotes', {
      topic: topicLabel(t),
      subject: overview.subject || subjectName,
      analysisId: t.analysis_ids?.[0] || analysisIds?.[0] || overview.analysis_ids[0],
      unit: t.unit || module?.display_name || moduleName,
      moduleName: module?.display_name || moduleName,
      moduleNumber: module?.module_number ?? moduleNumber,
      frequency: occ || undefined,
      occurrenceCount: occ || undefined,
      paperCount: paperCountOf(t) || undefined,
      totalMarks: t.total_marks ?? undefined,
      priority: topicPriority(t),
    });
  };

  const filteredTopics = useMemo(() => {
    if (!module) return [];
    const q = search.trim().toLowerCase();
    let list = module.topics ?? [];
    if (q) {
      list = list.filter((t) => topicLabel(t).toLowerCase().includes(q));
    }
    if (!q && filter !== 'All') {
      if (filter === 'Low') {
        list = list.filter(
          (t) => topicPriority(t) === 'Low' || !(t.asked || occurrenceOf(t) > 0)
        );
      } else {
        list = list.filter(
          (t) => topicPriority(t) === filter && (t.asked || occurrenceOf(t) > 0)
        );
      }
    }
    return sortTopics(list, sortMode);
  }, [module, filter, search, sortMode]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (!module || !overview) {
    return (
      <View style={styles.centered}>
        <EmptyState icon="alert-circle-outline" title="Module not found" subtitle="Go back and try again." />
      </View>
    );
  }

  const summary = {
    High: (module.topics || []).filter((t) => topicPriority(t) === 'High' && occurrenceOf(t) > 0).length,
    Medium: (module.topics || []).filter((t) => topicPriority(t) === 'Medium' && occurrenceOf(t) > 0)
      .length,
    Low: (module.topics || []).filter((t) => topicPriority(t) === 'Low' || occurrenceOf(t) === 0).length,
  };

  return (
    <ScreenWrapper
      refreshing={refreshing}
      onRefresh={() => {
        setRefreshing(true);
        load();
      }}
    >
      <Text style={styles.breadcrumb}>
        {overview.subject} › {module.display_name || module.module_name}
      </Text>
      <Text style={styles.subtitle}>
        {module.topic_count} topics · syllabus structure with PYQ priority
      </Text>

      <AppCard style={styles.infoCard}>
        <Text style={styles.infoText}>
          Priority is based on previous analyzed PYQs. Topics not yet asked still appear so you can
          cover the complete syllabus.
        </Text>
      </AppCard>

      <Searchbar
        placeholder="Search topics in this module"
        value={search}
        onChangeText={setSearch}
        style={styles.search}
        inputStyle={styles.searchInput}
      />

      <SegmentedButtons
        value={filter}
        onValueChange={(v) => setFilter(v as PriorityFilter)}
        density="small"
        style={styles.segmented}
        buttons={[
          { value: 'All', label: 'All' },
          { value: 'High', label: `High (${summary.High})` },
          { value: 'Medium', label: `Med (${summary.Medium})` },
          { value: 'Low', label: `Low` },
        ]}
      />

      <View style={styles.sortRow}>
        <Text style={styles.sortLabel}>Sort</Text>
        {(
          [
            ['priority', 'Priority'],
            ['occurred', 'Most asked'],
            ['az', 'A–Z'],
          ] as const
        ).map(([value, label]) => (
          <Chip
            key={value}
            compact
            selected={sortMode === value}
            onPress={() => setSortMode(value)}
            style={styles.sortChip}
          >
            {label}
          </Chip>
        ))}
      </View>

      {filteredTopics.length === 0 ? (
        <EmptyState
          icon="search-outline"
          title="No topics here"
          subtitle="Try another filter or upload a syllabus / PYQs."
        />
      ) : (
        filteredTopics.map((t, idx) => {
          const priority = topicPriority(t);
          const meta = PRIORITY_META[priority];
          const occ = occurrenceOf(t);
          const papers = paperCountOf(t);
          const asked = t.asked ?? occ > 0;
          return (
            <Pressable key={`${topicLabel(t)}-${idx}`} onPress={() => openTopic(t)}>
              <AppCard style={styles.topicCard}>
                <View style={[styles.priorityBadge, { backgroundColor: meta.bg }]}>
                  <Ionicons name={meta.icon} size={14} color={meta.color} />
                  <Text style={[styles.priorityBadgeText, { color: meta.color }]}>
                    {asked ? meta.label : 'NOT ASKED YET'}
                  </Text>
                </View>
                <View style={styles.topicRow}>
                  <View style={styles.topicMeta}>
                    <Text style={styles.topicName} numberOfLines={2}>
                      {topicLabel(t)}
                    </Text>
                    <Text style={styles.topicFreq}>
                      {asked
                        ? `Asked ${occ} time${occ === 1 ? '' : 's'}${
                            papers > 0
                              ? ` · Appeared in ${papers} paper${papers === 1 ? '' : 's'}`
                              : ''
                          }`
                        : 'In syllabus · not found in analyzed PYQs yet'}
                    </Text>
                    {t.total_marks != null && t.total_marks > 0 ? (
                      <Text style={styles.topicMarks}>Total marks: {t.total_marks}</Text>
                    ) : null}
                    {t.needs_review ? (
                      <Text style={styles.needsReview}>Needs review — low-confidence match</Text>
                    ) : null}
                  </View>
                  <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
                </View>
              </AppCard>
            </Pressable>
          );
        })
      )}
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
  breadcrumb: { ...typography.label, color: colors.primary, marginBottom: spacing.xs },
  subtitle: { ...typography.bodySmall, color: colors.textSecondary, marginBottom: spacing.md },
  infoCard: {
    padding: spacing.md,
    marginBottom: spacing.md,
    backgroundColor: colors.primaryLight,
  },
  infoText: { ...typography.caption, color: colors.text },
  search: {
    marginBottom: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
  },
  searchInput: { ...typography.bodySmall },
  segmented: { marginBottom: spacing.sm },
  sortRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: spacing.xs,
    marginBottom: spacing.md,
  },
  sortLabel: { ...typography.caption, color: colors.textSecondary, marginRight: spacing.xs },
  sortChip: { backgroundColor: colors.surface },
  topicCard: { padding: spacing.md, marginBottom: spacing.sm, gap: spacing.sm },
  priorityBadge: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radius.sm,
  },
  priorityBadgeText: { ...typography.caption, fontWeight: '700', fontSize: 10 },
  topicRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  topicMeta: { flex: 1, minWidth: 0 },
  topicName: { ...typography.label, color: colors.text },
  topicFreq: { ...typography.caption, color: colors.textSecondary, marginTop: 2 },
  topicMarks: { ...typography.caption, color: colors.primary, marginTop: 2 },
  needsReview: { ...typography.caption, color: colors.warning, marginTop: 2 },
});
