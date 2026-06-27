import { useCallback, useEffect, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { ActivityIndicator, Text } from 'react-native-paper';
import { useNavigation, useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, spacing, typography } from '@/core/theme';
import { getErrorMessage } from '@/data/api/client';
import { subjectsApi } from '@/data/api/endpoints';
import type { SubjectOverview } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppCard from '@/presentation/components/AppCard';
import EmptyState from '@/presentation/components/EmptyState';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import { useUIStore } from '@/store/uiStore';

type Route = RouteProp<RootStackParamList, 'SubjectNotes'>;
type Nav = NativeStackNavigationProp<RootStackParamList>;

const CATEGORY_META: Record<string, { label: string; icon: keyof typeof Ionicons.glyphMap }> = {
  pyq: { label: 'PYQ paper', icon: 'document-text-outline' },
  notes: { label: 'Notes PDF', icon: 'reader-outline' },
  study_material: { label: 'Study material', icon: 'library-outline' },
  other: { label: 'Document', icon: 'document-outline' },
};

function sourceSummary(o: SubjectOverview): string {
  const parts: string[] = [];
  if (o.pyq_count) parts.push(`${o.pyq_count} PYQ paper${o.pyq_count > 1 ? 's' : ''}`);
  if (o.notes_count) parts.push(`${o.notes_count} notes PDF${o.notes_count > 1 ? 's' : ''}`);
  if (o.study_material_count)
    parts.push(`${o.study_material_count} study material${o.study_material_count > 1 ? 's' : ''}`);
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

  const load = useCallback(async () => {
    try {
      const { data } = await subjectsApi.getOverview(subjectId);
      setOverview(data.data);
      navigation.setOptions({ title: data.data.subject || subjectName || 'Subject Notes' });
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

  const onRefresh = () => {
    setRefreshing(true);
    load();
  };

  const openTopic = (topic: string, frequency?: number) => {
    if (!overview) return;
    navigation.navigate('TopicStudyNotes', {
      topic,
      subject: overview.subject,
      analysisId: overview.analysis_ids[0],
      frequency: frequency ?? undefined,
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

  const topics = overview.topics ?? [];

  return (
    <ScreenWrapper refreshing={refreshing} onRefresh={onRefresh}>
      <View style={styles.header}>
        <View style={styles.titleRow}>
          <Ionicons name="library" size={22} color={colors.primary} />
          <Text style={styles.title}>{overview.subject} Notes</Text>
        </View>
        <Text style={styles.subtitle}>
          Generated from all your uploaded {overview.subject} resources
        </Text>
      </View>

      <AppCard style={styles.sourcesCard}>
        <Text style={styles.sectionLabel}>Generated from</Text>
        <Text style={styles.sourceSummary}>{sourceSummary(overview)}</Text>
        {overview.source_documents.length > 0 ? (
          <View style={styles.sourceList}>
            {overview.source_documents.map((src) => {
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
          </View>
        ) : null}
      </AppCard>

      <View style={styles.topicsHeader}>
        <Text style={styles.sectionTitle}>Topics Covered</Text>
        <Text style={styles.topicsCount}>{topics.length}</Text>
      </View>
      <Text style={styles.topicsHint}>
        Tap a topic to generate full notes from every uploaded {overview.subject} document.
      </Text>

      {topics.length === 0 ? (
        <EmptyState
          icon="documents-outline"
          title="No topics yet"
          subtitle="Upload and analyze PYQs for this subject to extract topics."
        />
      ) : (
        topics.map((t, idx) => (
          <Pressable key={`${t.topic}-${idx}`} onPress={() => openTopic(t.topic, t.frequency)}>
            <AppCard style={styles.topicCard}>
              <View style={styles.topicCheck}>
                <Ionicons name="checkmark-circle" size={20} color={colors.primary} />
              </View>
              <View style={styles.topicMeta}>
                <Text style={styles.topicName} numberOfLines={2}>
                  {t.topic}
                </Text>
                {t.frequency ? (
                  <Text style={styles.topicFreq}>Appeared {t.frequency}x in PYQs</Text>
                ) : null}
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
  header: {
    marginBottom: spacing.md,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  title: {
    ...typography.h2,
    color: colors.text,
    flex: 1,
  },
  subtitle: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },
  sourcesCard: {
    padding: spacing.md,
    marginBottom: spacing.lg,
    backgroundColor: colors.surface,
  },
  sectionLabel: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '700',
    textTransform: 'uppercase',
    marginBottom: spacing.xs,
  },
  sourceSummary: {
    ...typography.label,
    color: colors.primary,
    marginBottom: spacing.sm,
  },
  sourceList: {
    gap: spacing.xs,
  },
  sourceItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  sourceText: {
    ...typography.bodySmall,
    color: colors.text,
    flex: 1,
    minWidth: 0,
  },
  sourceCat: {
    ...typography.caption,
    color: colors.textMuted,
    flexShrink: 0,
  },
  topicsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: 2,
  },
  sectionTitle: {
    ...typography.h3,
    color: colors.text,
  },
  topicsCount: {
    ...typography.caption,
    color: colors.primary,
    fontWeight: '700',
    backgroundColor: colors.primaryLight,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: 10,
    overflow: 'hidden',
  },
  topicsHint: {
    ...typography.caption,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  topicCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    marginBottom: spacing.sm,
    gap: spacing.sm,
  },
  topicCheck: {
    flexShrink: 0,
  },
  topicMeta: {
    flex: 1,
    minWidth: 0,
  },
  topicName: {
    ...typography.label,
    color: colors.text,
  },
  topicFreq: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
  },
});
