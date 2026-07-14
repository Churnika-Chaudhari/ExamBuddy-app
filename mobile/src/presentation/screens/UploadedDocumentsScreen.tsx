import { useCallback, useState } from 'react';
import { Alert, FlatList, Pressable, StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, spacing, typography } from '@/core/theme';
import type { Document } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import EmptyState from '@/presentation/components/EmptyState';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import { useDocumentStore } from '@/store/documentStore';
import { canOpenDocument, openDocumentPdf } from '@/utils/openDocument';

type Nav = NativeStackNavigationProp<RootStackParamList>;

const STATUS_META: Record<
  Document['status'],
  { label: string; color: string; bg: string }
> = {
  ready: { label: 'Ready', color: colors.success, bg: colors.successLight },
  processing: { label: 'Processing', color: colors.warning, bg: colors.warningLight },
  uploading: { label: 'Uploading', color: colors.warning, bg: colors.warningLight },
  failed: { label: 'Failed', color: colors.error, bg: colors.errorLight },
};

const CATEGORY_LABEL: Record<Document['category'], string> = {
  pyq: 'PYQ',
  notes: 'Notes',
  study_material: 'Study Material',
  other: 'Document',
};

function formatSize(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return '';
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value?: string): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function UploadedDocumentsScreen() {
  const navigation = useNavigation<Nav>();
  const { documents, isLoading, fetchDocuments, clearDocuments } = useDocumentStore();
  const [clearing, setClearing] = useState(false);

  useFocusEffect(
    useCallback(() => {
      fetchDocuments();
    }, [fetchDocuments])
  );

  const confirmClearAll = () => {
    if (!documents.length || clearing) return;
    Alert.alert(
      'Clear all documents?',
      'This permanently deletes all your uploaded documents (PYQs and notes). This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear All',
          style: 'destructive',
          onPress: async () => {
            setClearing(true);
            try {
              await clearDocuments();
            } catch {
              Alert.alert('Could not clear documents', 'Please try again.');
            } finally {
              setClearing(false);
            }
          },
        },
      ]
    );
  };

  const openDocument = (item: Document) => {
    if (canOpenDocument(item)) {
      navigation.navigate('DocumentViewer', {
        documentId: item.id,
        title: item.title,
        fileUrl: item.file_url,
      });
      return;
    }
    void openDocumentPdf(item);
  };

  const renderItem = ({ item }: { item: Document }) => {
    const status = STATUS_META[item.status] ?? STATUS_META.ready;
    const meta = [
      item.file_type?.toUpperCase(),
      item.page_count ? `${item.page_count} page${item.page_count > 1 ? 's' : ''}` : null,
      formatSize(item.file_size_bytes),
      formatDate(item.created_at),
    ]
      .filter(Boolean)
      .join('  ·  ');

    return (
      <AppCard style={styles.docCard} onPress={() => openDocument(item)}>
        <View style={styles.docHeader}>
          <View style={styles.docIcon}>
            <Ionicons name="document-text-outline" size={20} color={colors.primary} />
          </View>
          <View style={styles.docInfo}>
            <Text style={styles.docTitle} numberOfLines={2}>
              {item.title}
            </Text>
            <View style={styles.docTags}>
              <View style={styles.categoryBadge}>
                <Text style={styles.categoryText}>{CATEGORY_LABEL[item.category]}</Text>
              </View>
              {item.subject ? <Text style={styles.docSubject}>{item.subject}</Text> : null}
            </View>
          </View>
          <View style={[styles.statusBadge, { backgroundColor: status.bg }]}>
            <Text style={[styles.statusText, { color: status.color }]}>{status.label}</Text>
          </View>
        </View>
        {meta ? <Text style={styles.docMeta}>{meta}</Text> : null}
        {canOpenDocument(item) ? (
          <Text style={styles.tapHint}>Tap to open PDF</Text>
        ) : null}
        {item.status === 'failed' && item.error_message ? (
          <Text style={styles.docError}>{item.error_message}</Text>
        ) : null}
      </AppCard>
    );
  };

  if (isLoading && !documents.length) {
    return (
      <ScreenWrapper scrollable={false}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      </ScreenWrapper>
    );
  }

  return (
    <ScreenWrapper scrollable={false} padded={false}>
      <View style={styles.container}>
      <FlatList
        data={documents}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
        onRefresh={fetchDocuments}
        refreshing={isLoading}
        ListHeaderComponent={
          <View style={styles.header}>
            <View style={styles.headerText}>
              <Text style={styles.title}>Uploaded Documents</Text>
              <Text style={styles.subtitle}>
                {documents.length} document{documents.length === 1 ? '' : 's'} uploaded
              </Text>
            </View>
            {documents.length > 0 ? (
              <Pressable
                onPress={confirmClearAll}
                hitSlop={8}
                disabled={clearing}
                style={[styles.clearAllBtn, clearing && styles.clearAllBtnDisabled]}
              >
                <Ionicons name="trash-outline" size={14} color={colors.error} />
                <Text style={styles.clearAllText}>{clearing ? 'Clearing…' : 'Clear All'}</Text>
              </Pressable>
            ) : null}
          </View>
        }
        ListEmptyComponent={
          <EmptyState
            icon="document-outline"
            title="No documents yet"
            subtitle="Upload PYQs or notes to power your AI study notes"
          />
        }
      />

      <View style={styles.footer}>
        <AppButton
          label="Upload Documents"
          onPress={() => navigation.navigate('UploadPYQ')}
          icon="cloud-upload-outline"
        />
      </View>
      </View>
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  header: {
    paddingBottom: spacing.sm,
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
  },
  headerText: {
    flex: 1,
    minWidth: 0,
    paddingRight: spacing.sm,
  },
  clearAllBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: spacing.xs,
    marginTop: 4,
  },
  clearAllBtnDisabled: {
    opacity: 0.5,
  },
  clearAllText: {
    ...typography.caption,
    color: colors.error,
    fontWeight: '600',
  },
  title: {
    ...typography.h2,
    color: colors.text,
  },
  subtitle: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: 4,
  },
  list: {
    padding: spacing.md,
    paddingBottom: spacing.xl,
    flexGrow: 1,
  },
  docCard: {
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  docHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
  },
  docIcon: {
    width: 36,
    height: 36,
    borderRadius: radius.md,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  docInfo: {
    flex: 1,
    minWidth: 0,
  },
  docTitle: {
    ...typography.label,
    color: colors.text,
  },
  docTags: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: spacing.xs,
    marginTop: 4,
  },
  categoryBadge: {
    backgroundColor: colors.primaryLight,
    paddingHorizontal: spacing.sm,
    paddingVertical: 1,
    borderRadius: radius.sm,
  },
  categoryText: {
    ...typography.caption,
    color: colors.primary,
    fontWeight: '700',
  },
  docSubject: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '600',
  },
  statusBadge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radius.sm,
    flexShrink: 0,
  },
  statusText: {
    ...typography.caption,
    fontWeight: '700',
  },
  docMeta: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  docError: {
    ...typography.caption,
    color: colors.error,
    marginTop: spacing.xs,
  },
  tapHint: {
    ...typography.caption,
    color: colors.primary,
    fontWeight: '600',
    marginTop: spacing.xs,
  },
  footer: {
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.background,
  },
});
