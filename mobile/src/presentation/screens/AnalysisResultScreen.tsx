import { useEffect, useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator, ProgressBar } from 'react-native-paper';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, spacing, typography } from '@/core/theme';
import type { PYQAnalysis } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppCard from '@/presentation/components/AppCard';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import TopicListItem, { type TopicRowData } from '@/presentation/components/TopicListItem';
import { useAnalysisStore } from '@/store/analysisStore';
import { useNotesStore } from '@/store/notesStore';

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

export default function AnalysisResultScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { analysisId } = route.params;

  const { currentAnalysis, isLoading, fetchAnalysis, pollAnalysis } = useAnalysisStore();
  const { fetchCachedTopics, cachedTopicKeys } = useNotesStore();

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

  return (
    <ScreenWrapper>
      <Text style={styles.heading}>Syllabus Topics</Text>
      <Text style={styles.desc}>
        Tap any topic to generate AI study notes — NotebookLM style exam preparation.
      </Text>

      {analysis.summary ? (
        <AppCard style={styles.summaryCard}>
          <Text style={styles.summaryText}>{analysis.summary}</Text>
        </AppCard>
      ) : null}

      {topicRows.length > 0 ? (
        <>
          <Text style={styles.sectionTitle}>All Topics ({topicRows.length})</Text>
          <Text style={styles.sectionHint}>
            Generate · Save · Regenerate · Share · Export PDF per topic
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
});
