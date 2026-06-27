import { useCallback, useEffect, useState } from 'react';
import { Share, StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import * as Clipboard from 'expo-clipboard';
import { useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';

import { colors, spacing, typography } from '@/core/theme';
import { getErrorMessage } from '@/data/api/client';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import MarkdownRenderer from '@/presentation/components/MarkdownRenderer';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import { useNotesStore } from '@/store/notesStore';
import { useUIStore } from '@/store/uiStore';

type Route = RouteProp<RootStackParamList, 'TopicStudyNotes'>;

function providerLabel(note: {
  ai_metadata?: {
    provider?: string | null;
    model?: string | null;
    generation_error?: string | null;
    ai_error?: string | null;
  } | null;
} | null) {
  const meta = note?.ai_metadata;
  const p = meta?.provider;
  if (meta?.generation_error || meta?.ai_error) {
    if (p && p !== 'local') {
      return `${meta.generation_error || meta.ai_error}`;
    }
    return meta.generation_error || meta.ai_error || 'Local template — AI unavailable';
  }
  if (!p || p === 'local') return 'Local template — configure GEMINI_API_KEY in backend .env';
  if (p === 'openai') return `ChatGPT · ${meta?.model ?? 'OpenAI'}`;
  if (p === 'gemini') return `Google Gemini · ${meta?.model ?? 'Gemini'}`;
  return p;
}

export default function TopicStudyNotesScreen() {
  const route = useRoute<Route>();
  const { topic, analysisId, subject, unit, frequency } = route.params;

  const {
    topicNote,
    isGenerating,
    isExporting,
    error,
    generateTopicNotes,
    regenerateTopicNotes,
    saveTopicNotes,
    exportTopicNotePdf,
    clearTopicNote,
  } = useNotesStore();
  const showSnackbar = useUIStore((s) => s.showSnackbar);
  const [initialized, setInitialized] = useState(false);

  const loadNotes = useCallback(async () => {
    try {
      await generateTopicNotes({
        topic,
        analysisId,
        subject,
        unit,
        frequency,
        regenerate: false,
      });
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    } finally {
      setInitialized(true);
    }
  }, [topic, analysisId, subject, unit, frequency, generateTopicNotes, showSnackbar]);

  useEffect(() => {
    clearTopicNote();
    loadNotes();
    return () => clearTopicNote();
  }, [loadNotes, clearTopicNote]);

  const handleRegenerate = async () => {
    try {
      await regenerateTopicNotes({
        topic,
        analysisId,
        subject,
        unit,
        frequency,
      });
      showSnackbar('Notes regenerated', 'success');
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    }
  };

  const handleSave = async () => {
    if (!topicNote) return;
    try {
      await saveTopicNotes(topicNote.id, !topicNote.is_saved);
      showSnackbar(topicNote.is_saved ? 'Removed from saved' : 'Notes saved', 'success');
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    }
  };

  const handleCopy = async () => {
    if (!topicNote?.notes) return;
    await Clipboard.setStringAsync(topicNote.notes);
    showSnackbar('Notes copied to clipboard', 'success');
  };

  const handleShare = async () => {
    if (!topicNote?.notes) return;
    try {
      await Share.share({
        title: `${topic} — Study Notes`,
        message: topicNote.notes,
      });
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    }
  };

  const handleExportPdf = async () => {
    if (!topicNote?.id) return;
    try {
      await exportTopicNotePdf(topicNote.id);
      showSnackbar('PDF ready to share or save', 'success');
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    }
  };

  if (!initialized || (isGenerating && !topicNote)) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>
          {isGenerating ? 'Generating AI study notes from your PDFs...' : 'Loading notes...'}
        </Text>
      </View>
    );
  }

  if (!topicNote) {
    return (
      <View style={styles.centered}>
        <Ionicons name="alert-circle-outline" size={48} color={colors.error} />
        <Text style={styles.errorTitle}>Notes generation failed</Text>
        <Text style={styles.errorText}>
          {error ?? 'Could not generate notes. Check backend is running and API key is configured.'}
        </Text>
        <AppButton label="Retry" onPress={loadNotes} loading={isGenerating} style={styles.retryBtn} />
      </View>
    );
  }

  const note = topicNote;
  const hasNotes = Boolean(note.notes?.trim());

  return (
    <ScreenWrapper>
      <View style={styles.header}>
        <View style={styles.titleRow}>
          <Ionicons name="book" size={22} color={colors.primary} />
          <Text style={styles.title}>{topic}</Text>
        </View>
        {unit ? <Text style={styles.unit}>{unit}</Text> : null}
        {frequency ? (
          <Text style={styles.freq}>Appeared {frequency} times in PYQs</Text>
        ) : null}
        <Text style={styles.provider}>
          {providerLabel(note)}
          {note.cached ? ' · Cached' : ''}
          {note.ai_metadata?.generation_mode === 'rag' ? ' · RAG' : ''}
          {(note.rag_sources?.length ?? 0) > 0 ? ` · ${note.rag_sources?.length} sources` : ''}
        </Text>

        {note.rag_sources && note.rag_sources.length > 0 ? (
          <AppCard style={styles.sourcesCard}>
            <Text style={styles.sourcesLabel}>Generated from</Text>
            {note.rag_sources.slice(0, 6).map((src, idx) => (
              <Text key={idx} style={styles.sourceItem}>
                • {src.title} ({src.category})
              </Text>
            ))}
          </AppCard>
        ) : null}
      </View>

      {error ? (
        <AppCard style={styles.errorCard}>
          <Text style={styles.errorCardText}>{error}</Text>
        </AppCard>
      ) : null}

      {note.summary ? (
        <AppCard style={styles.summaryCard}>
          <Text style={styles.summaryLabel}>Overview</Text>
          <Text style={styles.summaryText}>{note.summary}</Text>
        </AppCard>
      ) : null}

      <AppCard style={styles.notesCard}>
        {hasNotes ? (
          <MarkdownRenderer content={note.notes} />
        ) : (
          <View>
            <Text style={styles.empty}>No notes content returned.</Text>
            <AppButton
              label="Regenerate Notes"
              onPress={handleRegenerate}
              loading={isGenerating}
              style={styles.regenInline}
            />
          </View>
        )}
      </AppCard>

      <View style={styles.actions}>
        <AppButton
          label={note.is_saved ? 'Saved' : 'Save Notes'}
          onPress={handleSave}
          icon={note.is_saved ? 'heart' : 'heart-outline'}
          mode={note.is_saved ? 'outlined' : 'contained'}
          style={styles.actionBtn}
          disabled={!hasNotes}
        />
        <AppButton
          label="Regenerate"
          onPress={handleRegenerate}
          loading={isGenerating}
          icon="refresh"
          mode="outlined"
          style={styles.actionBtn}
        />
      </View>

      <View style={styles.actions}>
        <AppButton
          label="Copy"
          onPress={handleCopy}
          icon="content-copy"
          mode="outlined"
          style={styles.actionBtn}
          disabled={!hasNotes}
        />
        <AppButton
          label="Share"
          onPress={handleShare}
          icon="share-variant"
          mode="outlined"
          style={styles.actionBtn}
          disabled={!hasNotes}
        />
      </View>

      <AppButton
        label="Export PDF"
        onPress={handleExportPdf}
        loading={isExporting}
        icon="download"
        style={styles.exportBtn}
        disabled={!hasNotes || !note.id}
      />
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
    padding: spacing.xl,
  },
  loadingText: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.md,
    textAlign: 'center',
  },
  errorTitle: {
    ...typography.h3,
    color: colors.error,
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },
  errorText: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: spacing.lg,
  },
  retryBtn: {
    minWidth: 160,
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
  unit: {
    ...typography.caption,
    color: colors.primary,
    fontWeight: '600',
    marginBottom: 2,
  },
  freq: {
    ...typography.caption,
    color: colors.textSecondary,
    marginBottom: spacing.xs,
  },
  provider: {
    ...typography.caption,
    color: colors.textMuted,
  },
  sourcesCard: {
    padding: spacing.md,
    marginTop: spacing.sm,
    backgroundColor: colors.surface,
  },
  sourcesLabel: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '700',
    marginBottom: spacing.xs,
    textTransform: 'uppercase',
  },
  sourceItem: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 20,
  },
  errorCard: {
    padding: spacing.md,
    marginBottom: spacing.md,
    backgroundColor: colors.errorLight,
    borderColor: colors.errorLight,
  },
  errorCardText: {
    ...typography.bodySmall,
    color: colors.error,
  },
  summaryCard: {
    padding: spacing.md,
    backgroundColor: colors.primaryLight,
    borderColor: colors.primaryLight,
    marginBottom: spacing.md,
  },
  summaryLabel: {
    ...typography.caption,
    color: colors.primaryDark,
    fontWeight: '700',
    marginBottom: spacing.xs,
    textTransform: 'uppercase',
  },
  summaryText: {
    ...typography.bodySmall,
    color: colors.text,
    lineHeight: 22,
  },
  notesCard: {
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  empty: {
    ...typography.bodySmall,
    color: colors.textMuted,
    marginBottom: spacing.md,
  },
  regenInline: {
    marginTop: spacing.sm,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  actionBtn: {
    flex: 1,
  },
  exportBtn: {
    marginBottom: spacing.xl,
  },
});
