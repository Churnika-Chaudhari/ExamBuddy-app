import { useCallback, useState } from 'react';
import { Alert, FlatList, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, spacing, typography } from '@/core/theme';
import { notesApi, subjectsApi } from '@/data/api/endpoints';
import type { GeneratedTopicNote, Note, QuizSubject } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppCard from '@/presentation/components/AppCard';
import EmptyState from '@/presentation/components/EmptyState';
import NoteTypeBadge from '@/presentation/components/NoteTypeBadge';
import TopicTags from '@/presentation/components/TopicTags';
import { useNotesStore } from '@/store/notesStore';

type Nav = NativeStackNavigationProp<RootStackParamList>;

type NotesListItem =
  | { kind: 'batch'; note: Note }
  | { kind: 'topic'; note: GeneratedTopicNote };

export default function NotesScreen() {
  const navigation = useNavigation<Nav>();
  const { notes, isLoading, fetchNotes, clearNotes } = useNotesStore();
  const [generatedNotes, setGeneratedNotes] = useState<GeneratedTopicNote[]>([]);
  const [subjects, setSubjects] = useState<QuizSubject[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [clearing, setClearing] = useState(false);

  const loadAll = useCallback(async () => {
    setRefreshing(true);
    await fetchNotes();
    try {
      const { data } = await notesApi.listGenerated(1);
      setGeneratedNotes(data.data);
    } catch {
      setGeneratedNotes([]);
    }
    try {
      const { data } = await subjectsApi.list();
      setSubjects(data.data);
    } catch {
      setSubjects([]);
    }
    setRefreshing(false);
  }, [fetchNotes]);

  useFocusEffect(
    useCallback(() => {
      loadAll();
    }, [loadAll])
  );

  const listData: NotesListItem[] = [
    ...generatedNotes.map((note) => ({ kind: 'topic' as const, note })),
    ...notes.map((note) => ({ kind: 'batch' as const, note })),
  ];

  const confirmClearAll = () => {
    if (!listData.length || clearing) return;
    Alert.alert(
      'Clear all notes?',
      'This permanently deletes all your generated and topic notes. This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear All',
          style: 'destructive',
          onPress: async () => {
            setClearing(true);
            try {
              await clearNotes();
              setGeneratedNotes([]);
            } catch {
              Alert.alert('Could not clear notes', 'Please try again.');
            } finally {
              setClearing(false);
            }
          },
        },
      ]
    );
  };

  const renderItem = ({ item }: { item: NotesListItem }) => {
    if (item.kind === 'topic') {
      const note = item.note;
      return (
        <AppCard
          style={styles.noteCard}
          onPress={() =>
            navigation.navigate('TopicStudyNotes', {
              topic: note.topic,
              analysisId: note.analysis_id ?? undefined,
              subject: note.subject ?? undefined,
              unit: note.unit ?? undefined,
              frequency: note.frequency ?? undefined,
            })
          }
        >
          <View style={styles.noteHeader}>
            <View style={styles.noteIcon}>
              <Ionicons name="sparkles" size={20} color={colors.primary} />
            </View>
            <View style={styles.noteMeta}>
              <Text style={styles.noteTitle} numberOfLines={2}>
                {note.topic}
              </Text>
              <Text style={styles.topicBadge}>Topic Notes</Text>
            </View>
            {note.is_saved ? (
              <Ionicons name="heart" size={18} color={colors.error} style={styles.favoriteIcon} />
            ) : null}
          </View>
          <Text style={styles.noteSummary} numberOfLines={3}>
            {note.summary || note.notes}
          </Text>
        </AppCard>
      );
    }

    const note = item.note;
    return (
      <AppCard
        style={styles.noteCard}
        onPress={() => navigation.navigate('NoteDetail', { noteId: note.id })}
      >
        <View style={styles.noteHeader}>
          <View style={styles.noteIcon}>
            <Ionicons name="document-text-outline" size={20} color={colors.primary} />
          </View>
          <View style={styles.noteMeta}>
            <Text style={styles.noteTitle} numberOfLines={2}>
              {note.title}
            </Text>
            <NoteTypeBadge type={note.type} />
          </View>
          {note.is_favorite ? (
            <Ionicons name="heart" size={18} color={colors.error} style={styles.favoriteIcon} />
          ) : null}
        </View>
        <Text style={styles.noteSummary} numberOfLines={3}>
          {note.summary || note.content}
        </Text>
        <TopicTags topics={note.topics ?? []} maxVisible={4} />
      </AppCard>
    );
  };

  const renderSubjectsHeader = () => {
    if (!subjects.length) return null;
    return (
      <View style={styles.subjectsSection}>
        <Text style={styles.subjectsTitle}>Study by Subject</Text>
        <Text style={styles.subjectsHint}>
          Notes built from all uploaded PYQs and study materials of a subject
        </Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.subjectsRow}
        >
          {subjects.map((subject) => (
            <Pressable
              key={subject.id}
              onPress={() =>
                navigation.navigate('SubjectNotes', {
                  subjectId: subject.id,
                  subjectName: subject.name,
                })
              }
            >
              <AppCard style={styles.subjectCard}>
                <View style={styles.subjectIcon}>
                  <Ionicons name="library" size={18} color={colors.primary} />
                </View>
                <Text style={styles.subjectName} numberOfLines={2}>
                  {subject.name}
                </Text>
                <Text style={styles.subjectMeta}>
                  {subject.pyq_count} PYQ{subject.pyq_count === 1 ? '' : 's'} ·{' '}
                  {subject.topic_count} topic{subject.topic_count === 1 ? '' : 's'}
                </Text>
              </AppCard>
            </Pressable>
          ))}
        </ScrollView>
        <Text style={styles.recentLabel}>Recent Notes</Text>
      </View>
    );
  };

  if (isLoading && !listData.length && !refreshing) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerText}>
          <Text style={styles.title}>My Notes</Text>
          <Text style={styles.subtitle}>AI topic notes and batch study guides</Text>
        </View>
        {listData.length > 0 ? (
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

      <FlatList
        data={listData}
        keyExtractor={(item) =>
          item.kind === 'topic' ? `topic-${item.note.id}` : `batch-${item.note.id}`
        }
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
        onRefresh={loadAll}
        refreshing={refreshing}
        ListHeaderComponent={renderSubjectsHeader}
        ListEmptyComponent={
          <EmptyState
            icon="book-outline"
            title="No notes yet"
            subtitle="Pick a subject above to generate notes from all your uploaded PDFs"
          />
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
  },
  header: {
    padding: spacing.md,
    paddingTop: spacing.lg,
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
    paddingTop: 0,
    flexGrow: 1,
  },
  noteCard: {
    padding: spacing.md,
    marginBottom: spacing.sm,
    overflow: 'visible',
  },
  noteHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: spacing.sm,
  },
  noteIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.sm,
    flexShrink: 0,
  },
  noteMeta: {
    flex: 1,
    minWidth: 0,
    paddingRight: spacing.xs,
  },
  noteTitle: {
    ...typography.label,
    color: colors.text,
  },
  topicBadge: {
    ...typography.caption,
    color: colors.primary,
    fontWeight: '600',
    marginTop: 2,
  },
  favoriteIcon: {
    marginTop: 2,
    flexShrink: 0,
  },
  noteSummary: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    lineHeight: 20,
    marginBottom: spacing.sm,
  },
  subjectsSection: {
    marginBottom: spacing.sm,
  },
  subjectsTitle: {
    ...typography.label,
    color: colors.text,
    fontWeight: '700',
  },
  subjectsHint: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
    marginBottom: spacing.sm,
  },
  subjectsRow: {
    gap: spacing.sm,
    paddingRight: spacing.md,
  },
  subjectCard: {
    width: 150,
    padding: spacing.md,
  },
  subjectIcon: {
    width: 32,
    height: 32,
    borderRadius: 9,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  subjectName: {
    ...typography.label,
    color: colors.text,
  },
  subjectMeta: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 4,
  },
  recentLabel: {
    ...typography.label,
    color: colors.text,
    fontWeight: '700',
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
});
