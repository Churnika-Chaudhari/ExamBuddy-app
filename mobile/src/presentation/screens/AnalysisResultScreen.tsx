import { useCallback, useEffect, useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator, ProgressBar } from 'react-native-paper';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, spacing, typography } from '@/core/theme';
import { getErrorMessage } from '@/data/api/client';
import { subjectsApi } from '@/data/api/endpoints';
import type { PYQAnalysis, SubjectModule, SubjectPyqFilter } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import ModuleMultiSelect from '@/presentation/components/ModuleMultiSelect';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import TopicListItem, { type TopicRowData } from '@/presentation/components/TopicListItem';
import { useAnalysisStore } from '@/store/analysisStore';
import { useNotesStore } from '@/store/notesStore';
import { useUIStore } from '@/store/uiStore';

type Route = RouteProp<RootStackParamList, 'AnalysisResult'>;
type Nav = NativeStackNavigationProp<RootStackParamList, 'AnalysisResult'>;

function buildFrequencyTable(analysis: PYQAnalysis) {
  if (analysis.topic_frequency_table?.length) {
    return analysis.topic_frequency_table;
  }
  if (analysis.academic_topic_table?.length) {
    return analysis.academic_topic_table.map((r) => ({
      topic: r.topic,
      unit: r.unit ?? 'General',
      frequency: r.frequency,
    }));
  }
  if (analysis.topic_table?.length) {
    return analysis.topic_table.map((r) => ({
      topic: r.topic,
      unit: 'General',
      frequency: r.frequency,
    }));
  }
  return Object.entries(analysis.topic_frequency ?? {})
    .sort(([, a], [, b]) => b - a)
    .map(([topic, frequency]) => ({ topic, unit: 'General', frequency }));
}

function topicHasNotes(topic: string, cachedKeys: string[]) {
  const key = topic.toLowerCase().trim();
  return cachedKeys.some((k) => k === key || k.includes(key) || key.includes(k));
}

function askedTopics(mod: SubjectModule) {
  if (mod.pyq_topics?.length) return mod.pyq_topics;
  return (mod.topics || []).filter((t) => (t.asked ?? (t.occurrence_count ?? t.frequency ?? 0) > 0));
}

export default function AnalysisResultScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { analysisId } = route.params;
  const showSnackbar = useUIStore((s) => s.showSnackbar);

  const { currentAnalysis, isLoading, fetchAnalysis, pollAnalysis } = useAnalysisStore();
  const { fetchCachedTopics, cachedTopicKeys } = useNotesStore();

  const [subjectId, setSubjectId] = useState<string | null>(null);
  const [modules, setModules] = useState<SubjectModule[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [includeUnmapped, setIncludeUnmapped] = useState(true);
  const [filtered, setFiltered] = useState<SubjectPyqFilter | null>(null);
  const [filterError, setFilterError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    const load = async () => {
      const analysis = await fetchAnalysis(analysisId);
      if (analysis.status === 'processing' || analysis.status === 'pending') {
        await pollAnalysis(analysisId);
      }
      await fetchCachedTopics(analysisId);
    };
    load();
  }, [analysisId, fetchAnalysis, pollAnalysis, fetchCachedTopics]);

  const analysis = currentAnalysis;
  const isProcessing = analysis?.status === 'processing' || analysis?.status === 'pending';

  const loadModuleFilter = useCallback(async (subjectName: string) => {
    try {
      const { data } = await subjectsApi.list();
      const match = data.data.find(
        (s) => s.name.trim().toLowerCase() === subjectName.trim().toLowerCase()
      );
      if (!match) return;
      setSubjectId(match.id);
      const pyq = await subjectsApi.filterPyq(match.id);
      const payload = pyq.data.data;
      setModules(payload.modules);
      setSelectedIds(payload.modules.map((m) => m.module_id));
      setIncludeUnmapped(payload.modules.some((m) => m.is_unmapped));
      setFiltered(payload);
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    }
  }, [showSnackbar]);

  useEffect(() => {
    if (analysis?.status === 'completed' && analysis.subject) {
      loadModuleFilter(analysis.subject);
    }
  }, [analysis?.status, analysis?.subject, loadModuleFilter]);

  const frequencyTable = useMemo(
    () => (analysis ? buildFrequencyTable(analysis) : []),
    [analysis]
  );

  const topicRows: TopicRowData[] = useMemo(
    () =>
      frequencyTable.map((row) => ({
        ...row,
        hasNotes: topicHasNotes(row.topic, cachedTopicKeys),
      })),
    [frequencyTable, cachedTopicKeys]
  );

  const handleTopicPress = (row: TopicRowData) => {
    navigation.navigate('TopicStudyNotes', {
      topic: row.topic,
      analysisId,
      subject: analysis?.subject ?? undefined,
      unit: row.unit,
      frequency: row.frequency,
    });
  };

  const applyFilter = async () => {
    if (!subjectId) return;
    const ids = selectedIds.filter((id) => (id === 'm_unmapped' ? includeUnmapped : true));
    if (!ids.length) {
      setFilterError('Select at least one module, or choose All Modules.');
      return;
    }
    setFilterError(null);
    setApplying(true);
    try {
      const { data } = await subjectsApi.filterPyq(subjectId, ids, includeUnmapped);
      setFiltered(data.data);
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    } finally {
      setApplying(false);
    }
  };

  if (isLoading && !analysis) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (isProcessing) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.processingText}>Extracting syllabus topics...</Text>
        <ProgressBar indeterminate color={colors.primary} style={styles.progress} />
      </View>
    );
  }

  if (!analysis || analysis.status === 'failed') {
    return (
      <View style={styles.centered}>
        <Ionicons name="alert-circle-outline" size={48} color={colors.error} />
        <Text style={styles.errorText}>{analysis?.error_message ?? 'Analysis failed'}</Text>
      </View>
    );
  }

  const grouped = filtered?.modules ?? [];

  return (
    <ScreenWrapper>
      <Text style={styles.heading}>PYQ Results</Text>
      <Text style={styles.desc}>
        Filter by one or more syllabus modules, then tap a topic to generate exam notes.
      </Text>

      {analysis.summary ? (
        <AppCard style={styles.summaryCard}>
          <Text style={styles.summaryText}>{analysis.summary}</Text>
        </AppCard>
      ) : null}

      {modules.length > 0 ? (
        <>
          <ModuleMultiSelect
            modules={modules}
            selectedIds={selectedIds}
            onChange={(ids) => {
              setSelectedIds(ids);
              setFilterError(null);
            }}
            includeUnmapped={includeUnmapped}
            onIncludeUnmappedChange={setIncludeUnmapped}
            onApply={applyFilter}
            applying={applying}
            error={filterError}
          />

          {filtered?.empty_modules?.length ? (
            <Text style={styles.emptyBanner}>
              No PYQs in: {filtered.empty_modules.join(', ')}
            </Text>
          ) : null}

          {grouped.map((mod) => {
            const pyqs = askedTopics(mod);
            const label = mod.display_name || mod.module_name;
            return (
              <View key={mod.module_id} style={styles.groupBlock}>
                <Text style={styles.groupTitle}>{label.toUpperCase()}</Text>
                {pyqs.length === 0 ? (
                  <Text style={styles.emptyModule}>No PYQs found for {label}.</Text>
                ) : (
                  pyqs.map((t, index) => (
                    <TopicListItem
                      key={`${mod.module_id}-${t.topic}-${index}`}
                      row={{
                        topic: t.topic_name || t.topic,
                        unit: t.unit || label,
                        frequency: t.occurrence_count ?? t.frequency ?? 0,
                        hasNotes: topicHasNotes(t.topic_name || t.topic, cachedTopicKeys),
                      }}
                      onPress={handleTopicPress}
                    />
                  ))
                )}
              </View>
            );
          })}

          {subjectId ? (
            <AppButton
              label="Open subject modules"
              mode="outlined"
              icon="library-outline"
              onPress={() =>
                navigation.navigate('SubjectNotes', {
                  subjectId,
                  subjectName: analysis.subject ?? undefined,
                })
              }
              style={styles.subjectBtn}
            />
          ) : null}
        </>
      ) : topicRows.length > 0 ? (
        <>
          <Text style={styles.sectionTitle}>All Topics ({topicRows.length})</Text>
          <Text style={styles.sectionHint}>
            Upload a syllabus to filter these PYQ topics by module.
          </Text>
          {topicRows.map((row, index) => (
            <TopicListItem key={`${row.topic}-${index}`} row={row} onPress={handleTopicPress} />
          ))}
        </>
      ) : (
        <Text style={styles.emptyText}>No syllabus topics could be extracted.</Text>
      )}
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
    backgroundColor: colors.background,
  },
  processingText: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.md,
  },
  progress: {
    width: '80%',
    marginTop: spacing.lg,
    height: 4,
    borderRadius: 2,
  },
  errorText: {
    ...typography.body,
    color: colors.error,
    marginTop: spacing.md,
    textAlign: 'center',
  },
  heading: {
    ...typography.h2,
    color: colors.text,
    marginBottom: spacing.xs,
  },
  desc: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  summaryCard: {
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  summaryText: {
    ...typography.bodySmall,
    color: colors.text,
    lineHeight: 22,
  },
  sectionTitle: {
    ...typography.h3,
    color: colors.text,
    marginTop: spacing.md,
    marginBottom: spacing.xs,
  },
  sectionHint: {
    ...typography.caption,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  emptyText: {
    ...typography.bodySmall,
    color: colors.textMuted,
    marginVertical: spacing.lg,
  },
  emptyBanner: {
    ...typography.caption,
    color: colors.warning,
    marginBottom: spacing.sm,
  },
  groupBlock: {
    marginBottom: spacing.md,
  },
  groupTitle: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '700',
    letterSpacing: 0.4,
    marginBottom: spacing.sm,
  },
  emptyModule: {
    ...typography.bodySmall,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  subjectBtn: {
    marginTop: spacing.sm,
    marginBottom: spacing.lg,
  },
});
