import { useCallback, useState } from 'react';
import { FlatList, StyleSheet, TouchableOpacity, View } from 'react-native';
import { Text, ActivityIndicator, RadioButton } from 'react-native-paper';
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
  const [selected, setSelected] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      fetchSubjects().catch((err) => showSnackbar(getErrorMessage(err), 'error'));
    }, [fetchSubjects, showSnackbar])
  );

  const handleContinue = () => {
    if (!selected) return;
    const subject = subjects.find((s) => s.name === selected);
    if (!subject) return;
    setSelectedSubject(selected);
    navigation.navigate('QuizConfig', { subject: subject.name, subjectId: subject.id });
  };

  const renderSubject = ({ item }: { item: QuizSubject }) => {
    const isSelected = selected === item.name;
    return (
      <TouchableOpacity onPress={() => setSelected(item.name)} activeOpacity={0.7}>
        <AppCard
          style={{
            ...styles.card,
            ...(isSelected ? styles.cardSelected : {}),
          }}
        >
          <View style={styles.row}>
            <RadioButton
              value={item.name}
              status={isSelected ? 'checked' : 'unchecked'}
              onPress={() => setSelected(item.name)}
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

      <FlatList
        data={subjects}
        keyExtractor={(item) => item.name}
        renderItem={renderSubject}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <EmptyState
            icon="school-outline"
            title="No subjects found"
            subtitle="Upload and analyze PYQ papers first to detect subjects"
          />
        }
      />

      <View style={styles.footer}>
        <AppButton
          label="Continue"
          onPress={handleContinue}
          disabled={!selected}
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
