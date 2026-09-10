import { useCallback, useEffect, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { ActivityIndicator, Text } from 'react-native-paper';
import { useNavigation, useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, spacing, typography } from '@/core/theme';
import { getErrorMessage } from '@/data/api/client';
import { subjectsApi } from '@/data/api/endpoints';
import type { SubjectModule, SubjectOverview } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import EmptyState from '@/presentation/components/EmptyState';
import ModuleMultiSelect from '@/presentation/components/ModuleMultiSelect';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import { useUIStore } from '@/store/uiStore';

type Route = RouteProp<RootStackParamList, 'SubjectNotes'>;
type Nav = NativeStackNavigationProp<RootStackParamList>;

const CATEGORY_META: Record<string, { label: string; icon: keyof typeof Ionicons.glyphMap }> = {
  pyq: { label: 'PYQ paper', icon: 'document-text-outline' },
  notes: { label: 'Notes PDF', icon: 'reader-outline' },
  syllabus: { label: 'Syllabus', icon: 'book-outline' },
  study_material: { label: 'Study material', icon: 'library-outline' },
  other: { label: 'Document', icon: 'document-outline' },
};

function sourceSummary(o: SubjectOverview): string {
  const parts: string[] = [];
  const papers = o.analyzed_paper_count || o.pyq_count;
  if (papers) parts.push(`${papers} analyzed paper${papers > 1 ? 's' : ''}`);
  if (o.module_count) parts.push(`${o.module_count} module${o.module_count > 1 ? 's' : ''}`);
  if (o.topics?.length) parts.push(`${o.topics.length} topic${o.topics.length > 1 ? 's' : ''}`);
  if (o.syllabus_count) parts.push(`${o.syllabus_count} syllabus`);
  return parts.length ? parts.join(' · ') : 'No uploaded sources yet';
}

export default function SubjectNotesScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { subjectId, subjectName } = route.params;
  const showSnackbar = useUIStore((s) => s.showSnackbar);

  const [overview, setOverview] = useState<SubjectOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [includeUnmapped, setIncludeUnmapped] = useState(true);
  const [filterError, setFilterError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const { data } = await subjectsApi.getOverview(subjectId);
      setOverview(data.data);
      navigation.setOptions({ title: data.data.subject || subjectName || 'Subject Notes' });
      const mods = data.data.modules ?? [];
      if (mods.length) {
        setSelectedIds(mods.map((m) => m.module_id));
        setIncludeUnmapped(mods.some((m) => m.is_unmapped));
      }
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [subjectId, subjectName, navigation, showSnackbar]);

  useEffect(() => {
    load();
  }, [load]);

  const openModule = (mod: SubjectModule) => {
    if (!overview) return;
    navigation.navigate('ModuleTopics', {
      subjectId: overview.subject_id,
      subjectName: overview.subject,
      moduleId: mod.module_id,
      moduleIds: [mod.module_id],
      moduleName: mod.display_name || mod.module_name,
      moduleNumber: mod.module_number,
      analysisIds: overview.analysis_ids,
    });
  };

  const applyModuleFilter = () => {
    if (!overview) return;
    const ids = selectedIds.filter((id) => {
      if (id === 'm_unmapped') return includeUnmapped;
      return true;
    });
    if (!ids.length && !includeUnmapped) {
      setFilterError('Select at least one module, or choose All Modules.');
      return;
    }
    setFilterError(null);
    const first = overview.modules?.find((m) => ids.includes(m.module_id));
    navigation.navigate('ModuleTopics', {
      subjectId: overview.subject_id,
      subjectName: overview.subject,
      moduleId: first?.module_id,
      moduleIds: ids,
      moduleName: first?.display_name || first?.module_name,
      moduleNumber: first?.module_number,
      analysisIds: overview.analysis_ids,
    });
  };

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

  const modules = overview.modules?.length
    ? overview.modules
    : [
        {
          module_id: 'm_general',
          module_name: 'General Topics',
          display_name: 'General Topics',
          topic_count: overview.topics?.length || 0,
          topics: overview.topics || [],
          asked_topic_count: overview.topics?.filter((t) => (t.occurrence_count ?? t.frequency) > 0)
            .length,
          high_priority_count: overview.topics?.filter((t) => t.priority === 'High').length,
        } as SubjectModule,
      ];

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
        <Text style={styles.breadcrumb}>Select a module to view syllabus topics</Text>
      </View>

      <AppCard style={styles.infoCard}>
        <View style={styles.infoRow}>
          <Ionicons name="information-circle-outline" size={18} color={colors.primary} />
          <Text style={styles.infoText}>
            Modules and topic names come from your uploaded syllabus. PYQ analysis adds occurrence
            and exam priority so you know what has been asked before.
          </Text>
        </View>
      </AppCard>

      {overview.source_documents?.length ? (
        <AppCard style={styles.sourcesCard}>
          <Text style={styles.sectionLabel}>Sources</Text>
          {overview.source_documents.slice(0, 5).map((src) => {
            const meta = CATEGORY_META[src.category] ?? CATEGORY_META.other;
            return (
              <View key={src.id} style={styles.sourceItem}>
                <Ionicons name={meta.icon} size={16} color={colors.textSecondary} />
                <Text style={styles.sourceText} numberOfLines={1}>
                  {src.title}
                </Text>
                <Text style={styles.sourceCat}>{meta.label}</Text>
              </View>
            );
          })}
        </AppCard>
      ) : null}

      <Text style={styles.sectionTitle}>Modules</Text>
      <Text style={styles.sectionHint}>
        Tap one module for a single-module view, or select several and apply the filter.
      </Text>

      {modules.length > 1 ? (
        <ModuleMultiSelect
          modules={modules}
          selectedIds={selectedIds}
          onChange={(ids) => {
            setSelectedIds(ids);
            setFilterError(null);
          }}
          includeUnmapped={includeUnmapped}
          onIncludeUnmappedChange={setIncludeUnmapped}
          onApply={applyModuleFilter}
          error={filterError}
        />
      ) : null}

      {modules.length === 0 ? (
        <View>
          <EmptyState
            icon="documents-outline"
            title="No modules yet"
            subtitle="Upload a syllabus PDF, then analyze PYQs for this subject."
          />
          <AppButton
            label="Upload Syllabus"
            onPress={() => navigation.navigate('UploadPYQ', { initialCategory: 'syllabus' })}
            icon="book-outline"
            style={styles.uploadSyllabusBtn}
          />
        </View>
      ) : (
        modules.map((mod) => (
          <Pressable key={mod.module_id} onPress={() => openModule(mod)}>
            <AppCard style={styles.moduleCard}>
              <View style={styles.moduleIcon}>
                <Ionicons
                  name={mod.is_unmapped ? 'help-circle-outline' : 'book-outline'}
                  size={20}
                  color={colors.primary}
                />
              </View>
              <View style={styles.moduleMeta}>
                <Text style={styles.moduleName} numberOfLines={2}>
                  {mod.display_name || mod.module_name}
                </Text>
                <Text style={styles.moduleStats}>
                  {mod.topic_count} topic{mod.topic_count === 1 ? '' : 's'}
                  {mod.asked_topic_count
                    ? ` · ${mod.asked_topic_count} asked in PYQs`
                    : ''}
                  {mod.high_priority_count
                    ? ` · ${mod.high_priority_count} high priority`
                    : ''}
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
            </AppCard>
          </Pressable>
        ))
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
  breadcrumb: { ...typography.caption, color: colors.primary, marginTop: spacing.xs },
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
  infoRow: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-start' },
  infoText: { ...typography.caption, color: colors.text, flex: 1 },
  sourcesCard: {
    padding: spacing.md,
    marginBottom: spacing.md,
    backgroundColor: colors.surface,
  },
  sectionLabel: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '700',
    textTransform: 'uppercase',
    marginBottom: spacing.xs,
  },
  sourceItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    marginBottom: spacing.xs,
  },
  sourceText: { ...typography.bodySmall, color: colors.text, flex: 1, minWidth: 0 },
  sourceCat: { ...typography.caption, color: colors.textMuted },
  sectionTitle: { ...typography.h3, color: colors.text, marginBottom: spacing.sm },
  moduleCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    marginBottom: spacing.sm,
    gap: spacing.sm,
  },
  moduleIcon: {
    width: 36,
    height: 36,
    borderRadius: radius.md,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  moduleMeta: { flex: 1, minWidth: 0 },
  moduleName: { ...typography.label, color: colors.text },
  moduleStats: { ...typography.caption, color: colors.textSecondary, marginTop: 2 },
  uploadSyllabusBtn: { marginTop: spacing.md, marginBottom: spacing.lg },
});
