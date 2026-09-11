import { StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';

import { colors, radius, spacing, typography } from '@/core/theme';
import type { SubjectTopic } from '@/domain/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import {
  occurrenceOf,
  topicLabel,
  topicPriority,
  topicStatus,
} from '@/utils/notesTopics';

type Props = {
  topic: SubjectTopic;
  moduleLabel?: string | null;
  hasNotes?: boolean;
  onPress: () => void;
};

export default function NotesTopicCard({ topic, moduleLabel, hasNotes, onPress }: Props) {
  const occ = occurrenceOf(topic);
  const priority = topicPriority(topic);
  const status = topicStatus(topic);

  return (
    <AppCard style={styles.card}>
      <Text style={styles.name}>{topicLabel(topic)}</Text>
      {moduleLabel ? (
        <Text style={styles.meta}>
          Module:{' '}
          <Text style={styles.metaValue}>{moduleLabel}</Text>
        </Text>
      ) : null}
      <Text style={styles.meta}>
        PYQ Occurrence: <Text style={styles.metaValue}>{occ}</Text>
      </Text>
      <Text style={styles.meta}>
        Priority:{' '}
        <Text style={styles.metaValue}>{priority ?? 'No PYQ Data'}</Text>
      </Text>
      <View style={styles.statusRow}>
        <Text style={styles.meta}>Status:</Text>
        <View style={[styles.badge, badgeStyle(status.kind)]}>
          <Text style={[styles.badgeText, badgeTextStyle(status.kind)]}>{status.label}</Text>
        </View>
      </View>
      <AppButton
        label={hasNotes ? 'View Notes' : 'Generate Notes'}
        onPress={onPress}
        icon={hasNotes ? 'book-outline' : 'sparkles-outline'}
        mode={hasNotes ? 'outlined' : 'contained'}
        style={styles.btn}
      />
    </AppCard>
  );
}

function badgeStyle(kind: ReturnType<typeof topicStatus>['kind']) {
  if (kind === 'frequent') return { backgroundColor: colors.errorLight };
  if (kind === 'repeated') return { backgroundColor: colors.warningLight };
  if (kind === 'once') return { backgroundColor: colors.primaryLight };
  return { backgroundColor: colors.surfaceAlt };
}

function badgeTextStyle(kind: ReturnType<typeof topicStatus>['kind']) {
  if (kind === 'frequent') return { color: colors.error };
  if (kind === 'repeated') return { color: colors.warning };
  if (kind === 'once') return { color: colors.primary };
  return { color: colors.textSecondary };
}

const styles = StyleSheet.create({
  card: {
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  name: {
    ...typography.label,
    color: colors.text,
    marginBottom: spacing.xs,
  },
  meta: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
  },
  metaValue: {
    color: colors.text,
    fontWeight: '600',
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    marginTop: spacing.xs,
    marginBottom: spacing.sm,
  },
  badge: {
    borderRadius: radius.full,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
  },
  badgeText: {
    ...typography.caption,
    fontWeight: '700',
  },
  btn: {
    marginTop: spacing.xs,
  },
});
