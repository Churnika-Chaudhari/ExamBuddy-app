import { useCallback, useMemo, useState } from 'react';
import { FlatList, StyleSheet, TouchableOpacity, View } from 'react-native';
import { Text, ActivityIndicator, RadioButton, Searchbar } from 'react-native-paper';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, spacing, typography } from '@/core/theme';
import { getErrorMessage } from '@/data/api/client';
import type { QuizSubject } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import EmptyState from '@/presentation/components/EmptyState';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import { useQuizStore } from '@/store/quizStore';
import { useUIStore } from '@/store/uiStore';

type Nav = NativeStackNavigationProp<RootStackParamList, 'QuizSubjectSelect'>;

export default function QuizSubjectSelectScreen() {
  const navigation = useNavigation<Nav>();
  const { subjects, isLoading, fetchSubjects, setSelectedSubject } = useQuizStore();
  const showSnackbar = useUIStore((s) => s.showSnackbar);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(true);
  const [query, setQuery] = useState('');

  const visibleSubjects = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return subjects;
    return subjects.filter((s) => s.name.toLowerCase().includes(q));
  }, [subjects, query]);

  useFocusEffect(
    useCallback(() => {
      fetchSubjects().catch((err) => showSnackbar(getErrorMessage(err), 'error'));
    }, [fetchSubjects, showSnackbar])
  );

  const selectedSubject = subjects.find((s) => s.id === selectedId) ?? null;

  const handleSelectSubject = (id: string) => {
    setSelectedId(id);
    setQuery('');
    setPickerOpen(false);
  };

  const handleChangeSubject = () => {
    setQuery('');
    setPickerOpen(true);
  };

  const handleContinue = () => {
    if (!selectedId) return;
    const subject = subjects.find((s) => s.id === selectedId);
    if (!subject) return;
    setSelectedSubject(subject.name);
    navigation.navigate('QuizConfig', { subject: subject.name, subjectId: subject.id });
  };

  const renderSubject = ({ item }: { item: QuizSubject }) => {
    const isSelected = selectedId === item.id;
    return (
      <TouchableOpacity onPress={() => handleSelectSubject(item.id)} activeOpacity={0.7}>
        <AppCard
          style={{
            ...styles.card,
            ...(isSelected ? styles.cardSelected : {}),
          }}
        >
          <View style={styles.row}>
            <RadioButton
              value={item.id}
              status={isSelected ? 'checked' : 'unchecked'}
              onPress={() => handleSelectSubject(item.id)}
              color={colors.primary}
            />
            <View style={styles.info}>
              <Text style={styles.name}>{item.name}</Text>
              <Text style={styles.meta}>
                {item.pyq_count} PYQs · {item.topic_count} topics
              </Text>
            </View>
            <Ionicons
              name="book-outline"
              size={22}
              color={isSelected ? colors.primary : colors.textMuted}
            />
          </View>
        </AppCard>
      </TouchableOpacity>
    );
  };

  if (isLoading && !subjects.length) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading subjects...</Text>
      </View>
    );
  }

  return (
    <ScreenWrapper scrollable={false} padded={false}>
      <View style={styles.header}>
        <Text style={styles.title}>Select Subject</Text>
        <Text style={styles.subtitle}>
          Choose one subject. Quiz questions will use only topics from that subject.
        </Text>
      </View>

      {selectedSubject && !pickerOpen ? (
        <View style={styles.selectedWrap}>
          <AppCard style={styles.selectedCard}>
            <Text style={styles.selectedCaption}>Selected Subject</Text>
            <Text style={styles.selectedName}>{selectedSubject.name}</Text>
            <Text style={styles.selectedMeta}>
              {selectedSubject.pyq_count} PYQs · {selectedSubject.topic_count} topics
            </Text>
            <AppButton
              label="Change Subject"
              mode="outlined"
              onPress={handleChangeSubject}
              style={styles.changeBtn}
            />
          </AppCard>
        </View>
      ) : (
        <View style={styles.pickerWrap}>
          <Searchbar
            placeholder="Search subject..."
            value={query}
            onChangeText={setQuery}
            style={styles.search}
          />

          <FlatList
            data={visibleSubjects}
            keyExtractor={(item) => item.id}
            renderItem={renderSubject}
            contentContainerStyle={styles.list}
            ListEmptyComponent={
              <EmptyState
                icon="school-outline"
                title="No subjects found"
                subtitle={
                  query.trim()
                    ? 'Try a different search.'
                    : 'Upload and analyze PYQ papers first to detect subjects'
                }
              />
            }
          />
        </View>
      )}

      <View style={styles.footer}>
        <AppButton
          label="Continue"
          onPress={handleContinue}
          disabled={!selectedId}
          icon="arrow-right"
        />
      </View>
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
  loadingText: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: spacing.md,
  },
  header: {
    padding: spacing.md,
    paddingTop: spacing.lg,
  },
  title: {
    ...typography.h2,
    color: colors.text,
  },
  subtitle: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: spacing.xs,
    lineHeight: 20,
  },
  pickerWrap: {
    flex: 1,
  },
  search: {
    marginHorizontal: spacing.md,
    marginBottom: spacing.sm,
    backgroundColor: colors.surface,
  },
  selectedWrap: {
    flex: 1,
    padding: spacing.md,
  },
  selectedCard: {
    padding: spacing.md,
  },
  selectedCaption: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  selectedName: {
    ...typography.label,
    color: colors.primary,
    fontWeight: '700',
    marginTop: 2,
  },
  selectedMeta: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
  },
  changeBtn: {
    marginTop: spacing.sm,
    alignSelf: 'flex-start',
  },
  list: {
    padding: spacing.md,
    paddingTop: 0,
    flexGrow: 1,
  },
  card: {
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  cardSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.primaryLight,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  info: {
    flex: 1,
    marginLeft: spacing.xs,
  },
  name: {
    ...typography.label,
    color: colors.text,
  },
  meta: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
  },
  footer: {
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
});
