import { useCallback, useEffect, useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { ActivityIndicator, Text } from 'react-native-paper';
import { useNavigation, useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, spacing, typography } from '@/core/theme';
import { getErrorMessage } from '@/data/api/client';
import { notesApi, subjectsApi } from '@/data/api/endpoints';
import type { SubjectModule, SubjectOverview, SubjectTopic } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import EmptyState from '@/presentation/components/EmptyState';
import ModuleMultiSelect from '@/presentation/components/ModuleMultiSelect';
import NotesTopicCard from '@/presentation/components/NotesTopicCard';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import { useUIStore } from '@/store/uiStore';
import {
  isRealSyllabusModule,
  normalizeTopicKey,
  occurrenceOf,
  partitionTopics,
  topicHasCachedNotes,
  topicLabel,
} from '@/utils/notesTopics';

type Route = RouteProp<RootStackParamList, 'SubjectNotes'>;
type Nav = NativeStackNavigationProp<RootStackParamList>;

function sourceSummary(o: SubjectOverview): string {
  const parts: string[] = [];
  const papers = o.analyzed_paper_count || o.pyq_count;
  if (papers) parts.push(`${papers} analyzed paper${papers > 1 ? 's' : ''}`);
  if (o.module_count) parts.push(`${o.module_count} module${o.module_count > 1 ? 's' : ''}`);
  if (o.topics?.length) parts.push(`${o.topics.length} topic${o.topics.length > 1 ? 's' : ''}`);
  if (o.syllabus_count) parts.push(`${o.syllabus_count} syllabus`);
  return parts.length ? parts.join(' · ') : 'No uploaded sources yet';
}

function allSelectableIds(modules: SubjectModule[], includeUnmapped: boolean): string[] {
  const ids = modules.filter(isRealSyllabusModule).map((m) => m.module_id);
  const unmapped = modules.find((m) => m.is_unmapped);
  if (includeUnmapped && unmapped) ids.push(unmapped.module_id);
  return ids;
}

export default function SubjectNotesScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { subjectId, subjectName } = route.params;
  const showSnackbar = useUIStore((s) => s.showSnackbar);

  const [overview, setOverview] = useState<SubjectOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [applying, setApplying] = useState(false);

  const [draftIds, setDraftIds] = useState<string[]>([]);
  const [draftUnmapped, setDraftUnmapped] = useState(true);
  const [displayedModules, setDisplayedModules] = useState<SubjectModule[]>([]);
  const [filterError, setFilterError] = useState<string | null>(null);
  const [cachedKeys, setCachedKeys] = useState<Set<string>>(new Set());

  const loadCachedKeys = useCallback(
    async (subject: string, moduleIds?: string[]) => {
      try {
        const keys = await notesApi.listCachedTopicKeysForSubject(subject, moduleIds);
        setCachedKeys(new Set(keys.map((k) => normalizeTopicKey(k))));
      } catch {
        setCachedKeys(new Set());
      }
    },
    []
  );

  const load = useCallback(async () => {
    try {
      const { data } = await subjectsApi.getOverview(subjectId);
      const ov = data.data;
      setOverview(ov);
      navigation.setOptions({ title: ov.subject || subjectName || 'Subject Notes' });

      const syllabusMods = (ov.modules || []).filter(isRealSyllabusModule);
      const unmapped = (ov.modules || []).find((m) => m.is_unmapped);
      const includeUnmapped = Boolean(unmapped);
      const initialIds = allSelectableIds(ov.modules || [], includeUnmapped);
      setDraftIds(initialIds);
      setDraftUnmapped(includeUnmapped);

      if (ov.has_syllabus_modules && syllabusMods.length) {
        setDisplayedModules(
          (ov.modules || []).filter(
            (m) => isRealSyllabusModule(m) || (includeUnmapped && m.is_unmapped)
          )
        );
      } else {
        setDisplayedModules([]);
      }

      await loadCachedKeys(ov.subject);
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [subjectId, subjectName, navigation, showSnackbar, loadCachedKeys]);

  useEffect(() => {
    load();
  }, [load]);

  const applyModuleFilter = async () => {
    if (!overview) return;
    const ids = draftIds.filter((id) => (id === 'm_unmapped' ? draftUnmapped : true));
    if (!ids.length) {
      setFilterError('Select at least one module, or choose All Modules.');
      return;
    }
    setFilterError(null);
    setApplying(true);
    try {
      const { data } = await subjectsApi.filterPyq(overview.subject_id, ids, draftUnmapped);
      const payload = data.data;
      setDisplayedModules(payload.modules);
      await loadCachedKeys(overview.subject, payload.selected_module_ids);
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    } finally {
      setApplying(false);
    }
  };

  const openTopic = (t: SubjectTopic, fromModule?: SubjectModule | null) => {
    if (!overview) return;
    const occ = occurrenceOf(t);
    const moduleName = fromModule?.display_name || fromModule?.module_name || t.module_name || undefined;
    navigation.navigate('TopicStudyNotes', {
      topic: topicLabel(t),
      subject: overview.subject || subjectName,
      subjectId: overview.subject_id,
      analysisId: t.analysis_ids?.[0] || overview.analysis_ids[0],
      unit: t.unit || moduleName,
      moduleId: t.module_id || fromModule?.module_id,
      moduleName,
      moduleNumber: t.module_number ?? fromModule?.module_number,
      topicId: t.topic_id || undefined,
      frequency: occ || undefined,
      occurrenceCount: occ,
      paperCount: t.paper_count ?? undefined,
      totalMarks: t.total_marks ?? undefined,
      priority: t.priority || undefined,
    });
  };

  const hasSyllabus = Boolean(
    overview?.has_syllabus_modules && (overview.modules || []).some(isRealSyllabusModule)
  );
  const syllabusModules = useMemo(
    () => (overview?.modules || []).filter((m) => isRealSyllabusModule(m) || m.is_unmapped),
    [overview]
  );
  const hasPyqs = Boolean(
    (overview?.analyzed_paper_count || 0) > 0 ||
      (overview?.topics || []).some((t) => occurrenceOf(t) > 0)
  );

  const uncategorizedTopics = useMemo(() => {
    if (hasSyllabus) return [];
    return overview?.topics || [];
  }, [hasSyllabus, overview]);

  const displayedTopics = useMemo(() => {
    if (!hasSyllabus) return uncategorizedTopics;
    return displayedModules.flatMap((m) => m.topics || []);
  }, [hasSyllabus, uncategorizedTopics, displayedModules]);

  const groups = useMemo(() => partitionTopics(displayedTopics), [displayedTopics]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (!overview) {
    return (
      <View style={styles.centered}>
        <EmptyState
          icon="alert-circle-outline"
          title="Could not load subject"
          subtitle="Pull to refresh or try again later."
        />
      </View>
    );
  }

  const renderTopicList = (topics: SubjectTopic[], module?: SubjectModule | null) =>
    topics.map((t, idx) => (
      <NotesTopicCard
        key={`${module?.module_id || 'u'}-${topicLabel(t)}-${idx}`}
        topic={t}
        moduleLabel={module?.display_name || module?.module_name || t.module_name}
        hasNotes={topicHasCachedNotes(t, cachedKeys)}
        onPress={() => openTopic(t, module)}
      />
    ));

  const renderModuleGroups = (modules: SubjectModule[]) => {
    if (!modules.length) {
      return (
        <EmptyState
          icon="filter-outline"
          title="No topics available in the selected module(s)."
          subtitle="Try another module selection, or upload a syllabus / PYQ."
        />
      );
    }
    return modules.map((mod) => {
      const parts = partitionTopics(mod.topics || []);
      const label = mod.display_name || mod.module_name;
      const empty = !(mod.topics || []).length;
      return (
        <View key={mod.module_id} style={styles.moduleBlock}>
          <Text style={styles.moduleHeading}>{label.toUpperCase()}</Text>
          {empty ? (
            <Text style={styles.emptyModule}>No topics available in this module.</Text>
          ) : !groups.hasRepeated ? (
            <>
              {parts.analyzed.length ? (
                <>
                  <Text style={styles.categoryTitle}>📚 Analyzed Topics</Text>
                  {renderTopicList(parts.analyzed, mod)}
                </>
              ) : null}
              {parts.syllabus.length ? (
                <>
                  <Text style={styles.categoryTitle}>Syllabus Topics</Text>
                  {renderTopicList(parts.syllabus, mod)}
                </>
              ) : null}
            </>
          ) : (
            <>
              {parts.frequent.length ? (
                <>
                  <Text style={styles.categoryTitle}>🔥 Frequently Asked Topics</Text>
                  {renderTopicList(parts.frequent, mod)}
                </>
              ) : null}
              {parts.repeated.length ? (
                <>
                  <Text style={styles.categoryTitle}>⭐ Other Repeated Topics</Text>
                  {renderTopicList(parts.repeated, mod)}
                </>
              ) : null}
              {parts.once.length ? (
                <>
                  <Text style={styles.categoryTitle}>📚 Topics Asked Once</Text>
                  {renderTopicList(parts.once, mod)}
                </>
              ) : null}
              {parts.syllabus.length ? (
                <>
                  <Text style={styles.categoryTitle}>Syllabus Topics</Text>
                  {renderTopicList(parts.syllabus, mod)}
                </>
              ) : null}
            </>
          )}
        </View>
      );
    });
  };

  return (
    <ScreenWrapper
      refreshing={refreshing}
      onRefresh={() => {
        setRefreshing(true);
        load();
      }}
    >
      <View style={styles.header}>
        <View style={styles.titleRow}>
          <Ionicons name="library" size={22} color={colors.primary} />
          <Text style={styles.title}>{overview.subject}</Text>
        </View>
        <Text style={styles.subtitle}>{sourceSummary(overview)}</Text>
      </View>

      {!hasPyqs ? (
        <AppCard style={styles.infoCard}>
          <Text style={styles.infoText}>
            No PYQs have been analyzed for this subject yet.
            {hasSyllabus ? ' Syllabus topics are still available below.' : ''}
          </Text>
        </AppCard>
      ) : null}

      {hasPyqs && !groups.hasRepeated && displayedTopics.length > 0 ? (
        <AppCard style={styles.infoCard}>
          <Text style={styles.infoTitle}>No Repeated Topics Found</Text>
          <Text style={styles.infoText}>
            None of the analyzed PYQs for this subject currently contain repeated topics. You can
            still view all analyzed topics below.
          </Text>
        </AppCard>
      ) : null}

      {hasSyllabus ? (
        <>
          <Text style={styles.sectionTitle}>Module Filter</Text>
          <Text style={styles.sectionHint}>
            Select one or more modules, then tap Apply Filter. Topics do not change until you apply.
          </Text>
          <ModuleMultiSelect
            modules={syllabusModules}
            selectedIds={draftIds}
            onChange={(ids) => {
              setDraftIds(ids);
              setFilterError(null);
            }}
            includeUnmapped={draftUnmapped}
            onIncludeUnmappedChange={setDraftUnmapped}
            onApply={applyModuleFilter}
            applying={applying}
            error={filterError}
          />
        </>
      ) : (
        <AppCard style={styles.infoCard}>
          <Text style={styles.infoTitle}>No syllabus available for module-wise organization.</Text>
          <Text style={styles.infoText}>
            Topics can still be displayed as Uncategorized Topics. Upload a syllabus to organize
            them module-wise.
          </Text>
          <AppButton
            label="Upload Syllabus"
            onPress={() => navigation.navigate('UploadPYQ', { initialCategory: 'syllabus' })}
            icon="book-outline"
            style={styles.uploadBtn}
          />
        </AppCard>
      )}

      {hasSyllabus ? (
        displayedTopics.length === 0 ? (
          <EmptyState
            icon="filter-outline"
            title="No topics available in the selected module(s)."
            subtitle="Select different modules and apply the filter again."
          />
        ) : (
          renderModuleGroups(displayedModules)
        )
      ) : uncategorizedTopics.length === 0 ? (
        <EmptyState
          icon="documents-outline"
          title="No topics yet"
          subtitle="Upload a syllabus or analyze a PYQ for this subject."
        />
      ) : (
        <View style={styles.moduleBlock}>
          <Text style={styles.moduleHeading}>UNCATEGORIZED TOPICS</Text>
          {!groups.hasRepeated && groups.hasAnalyzed ? (
            <>
              <Text style={styles.categoryTitle}>📚 Analyzed Topics</Text>
              {renderTopicList(groups.analyzed)}
              {groups.syllabus.length ? (
                <>
                  <Text style={styles.categoryTitle}>Syllabus Topics</Text>
                  {renderTopicList(groups.syllabus)}
                </>
              ) : null}
            </>
          ) : (
            <>
              {groups.frequent.length ? (
                <>
                  <Text style={styles.categoryTitle}>🔥 Frequently Asked Topics</Text>
                  {renderTopicList(groups.frequent)}
                </>
              ) : null}
              {groups.repeated.length ? (
                <>
                  <Text style={styles.categoryTitle}>⭐ Other Repeated Topics</Text>
                  {renderTopicList(groups.repeated)}
                </>
              ) : null}
              {groups.once.length ? (
                <>
                  <Text style={styles.categoryTitle}>📚 Topics Asked Once</Text>
                  {renderTopicList(groups.once)}
                </>
              ) : null}
              {groups.syllabus.length ? (
                <>
                  <Text style={styles.categoryTitle}>Syllabus Topics</Text>
                  {renderTopicList(groups.syllabus)}
                </>
              ) : null}
            </>
          )}
        </View>
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
  header: { marginBottom: spacing.md },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  title: { ...typography.h2, color: colors.text, flex: 1 },
  subtitle: { ...typography.bodySmall, color: colors.textSecondary },
  sectionTitle: { ...typography.h3, color: colors.text, marginBottom: spacing.xs },
  sectionHint: {
    ...typography.caption,
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  infoCard: {
    padding: spacing.md,
    marginBottom: spacing.md,
    backgroundColor: colors.primaryLight,
  },
  infoTitle: {
    ...typography.label,
    color: colors.text,
    marginBottom: 4,
  },
  infoText: { ...typography.caption, color: colors.text, lineHeight: 18 },
  uploadBtn: { marginTop: spacing.sm },
  moduleBlock: { marginBottom: spacing.md },
  moduleHeading: {
    ...typography.caption,
    color: colors.primary,
    fontWeight: '800',
    letterSpacing: 0.6,
    marginBottom: spacing.xs,
  },
  categoryTitle: {
    ...typography.label,
    color: colors.text,
    marginTop: spacing.sm,
    marginBottom: spacing.xs,
  },
  emptyModule: {
    ...typography.caption,
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
});
