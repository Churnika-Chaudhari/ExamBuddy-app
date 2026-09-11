import { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, spacing, typography } from '@/core/theme';
import { documentsApi, subjectsApi } from '@/data/api/endpoints';
import type { Document, QuizSubject } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import EmptyState from '@/presentation/components/EmptyState';
import ScreenWrapper, { TAB_SCREEN_EDGES } from '@/presentation/components/ScreenWrapper';
import { canOpenDocument, openDocumentPdf } from '@/utils/openDocument';

type Nav = NativeStackNavigationProp<RootStackParamList>;

function formatDate(value?: string): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function NotesScreen() {
  const navigation = useNavigation<Nav>();
  const [subjects, setSubjects] = useState<QuizSubject[]>([]);
  const [uploadedNotes, setUploadedNotes] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      const [{ data: subjectRes }, notesRes] = await Promise.all([
        subjectsApi.list(),
        documentsApi.list({ category: 'notes' }).catch(() => null),
      ]);
      setSubjects(subjectRes.data || []);
      setUploadedNotes(notesRes?.data.data || []);
    } catch {
      setSubjects([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadAll();
    }, [loadAll])
  );

  const openUploadedNote = (doc: Document) => {
    if (canOpenDocument(doc)) {
      navigation.navigate('DocumentViewer', {
        documentId: doc.id,
        title: doc.title,
        fileUrl: doc.file_url,
      });
      return;
    }
    void openDocumentPdf(doc);
  };

  if (loading && !refreshing) {
    return (
      <ScreenWrapper scrollable={false} padded={false} edges={TAB_SCREEN_EDGES}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      </ScreenWrapper>
    );
  }

  return (
    <ScreenWrapper
      edges={TAB_SCREEN_EDGES}
      refreshing={refreshing}
      onRefresh={() => {
        setRefreshing(true);
        loadAll();
      }}
    >
      <View style={styles.header}>
        <Text style={styles.title}>Notes Generation</Text>
        <Text style={styles.subtitle}>Select Subject</Text>
      </View>

      {subjects.length === 0 ? (
        <EmptyState
          icon="library-outline"
          title="No subjects available yet"
          subtitle="Upload a syllabus or analyze a PYQ to get started."
        />
      ) : (
        subjects.map((subject) => {
          const papers = subject.analyzed_paper_count || subject.pyq_count || 0;
          return (
            <AppCard key={subject.id} style={styles.subjectCard}>
              <View style={styles.subjectHeader}>
                <View style={styles.subjectIcon}>
                  <Ionicons name="library" size={20} color={colors.primary} />
                </View>
                <View style={styles.subjectMeta}>
                  <Text style={styles.subjectName}>{subject.name}</Text>
                  <Text style={styles.subjectStat}>PYQs Analyzed: {papers}</Text>
                  <Text style={styles.subjectStat}>Topics Found: {subject.topic_count}</Text>
                </View>
              </View>
              <AppButton
                label="View Notes"
                onPress={() =>
                  navigation.navigate('SubjectNotes', {
                    subjectId: subject.id,
                    subjectName: subject.name,
                  })
                }
                icon="document-text-outline"
                style={styles.viewBtn}
              />
            </AppCard>
          );
        })
      )}

      {uploadedNotes.length > 0 ? (
        <View style={styles.uploadedSection}>
          <Text style={styles.sectionTitle}>Uploaded PDF Notes</Text>
          <Text style={styles.sectionHint}>Your own notes — tap to open and read</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.uploadedRow}
          >
            {uploadedNotes.map((doc) => (
              <Pressable key={doc.id} onPress={() => openUploadedNote(doc)}>
                <AppCard style={styles.uploadedCard}>
                  <View style={styles.uploadedIcon}>
                    <Ionicons name="document-text" size={20} color={colors.primary} />
                  </View>
                  <Text style={styles.uploadedTitle} numberOfLines={2}>
                    {doc.title}
                  </Text>
                  {doc.subject ? (
                    <Text style={styles.uploadedSubject} numberOfLines={1}>
                      {doc.subject}
                    </Text>
                  ) : null}
                  <Text style={styles.uploadedMeta}>
                    {doc.page_count ? `${doc.page_count} pg · ` : ''}
                    {formatDate(doc.created_at)}
                  </Text>
                </AppCard>
              </Pressable>
            ))}
          </ScrollView>
        </View>
      ) : null}
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  header: {
    marginBottom: spacing.md,
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
  subjectCard: {
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  subjectHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  subjectIcon: {
    width: 40,
    height: 40,
    borderRadius: radius.md,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  subjectMeta: {
    flex: 1,
    minWidth: 0,
  },
  subjectName: {
    ...typography.h3,
    color: colors.text,
    marginBottom: 4,
  },
  subjectStat: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 1,
  },
  viewBtn: {
    marginTop: spacing.xs,
  },
  uploadedSection: {
    marginTop: spacing.md,
    marginBottom: spacing.lg,
  },
  sectionTitle: {
    ...typography.label,
    color: colors.text,
    fontWeight: '700',
  },
  sectionHint: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
    marginBottom: spacing.sm,
  },
  uploadedRow: {
    gap: spacing.sm,
    paddingRight: spacing.md,
  },
  uploadedCard: {
    width: 160,
    minHeight: 120,
    padding: spacing.md,
  },
  uploadedIcon: {
    width: 32,
    height: 32,
    borderRadius: 9,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  uploadedTitle: {
    ...typography.label,
    color: colors.text,
  },
  uploadedSubject: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
  },
  uploadedMeta: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 4,
  },
});
