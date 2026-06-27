import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, spacing, typography } from '@/core/theme';

export interface TopicRowData {
  topic: string;
  unit: string;
  frequency: number;
  hasNotes?: boolean;
}

interface TopicListItemProps {
  row: TopicRowData;
  onPress: (row: TopicRowData) => void;
}

export default function TopicListItem({ row, onPress }: TopicListItemProps) {
  return (
    <Pressable
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
      onPress={() => onPress(row)}
    >
      <View style={styles.left}>
        <Text style={styles.topic} numberOfLines={2}>
          {row.topic}
        </Text>
        <Text style={styles.meta}>
          {row.unit} · Asked {row.frequency}x
        </Text>
      </View>
      <View style={styles.right}>
        {row.hasNotes ? (
          <View style={styles.badgeReady}>
            <Ionicons name="document-text" size={14} color={colors.success} />
            <Text style={styles.badgeReadyText}>Ready</Text>
          </View>
        ) : (
          <View style={styles.badgeGenerate}>
            <Ionicons name="sparkles" size={14} color={colors.primary} />
            <Text style={styles.badgeGenerateText}>Generate</Text>
          </View>
        )}
        <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  pressed: {
    backgroundColor: colors.surface,
  },
  left: {
    flex: 1,
    paddingRight: spacing.sm,
  },
  topic: {
    ...typography.label,
    color: colors.text,
    marginBottom: 4,
  },
  meta: {
    ...typography.caption,
    color: colors.textSecondary,
  },
  right: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  badgeReady: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: colors.successLight,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.full,
  },
  badgeReadyText: {
    ...typography.caption,
    color: colors.success,
    fontWeight: '600',
  },
  badgeGenerate: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: colors.primaryLight,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.full,
  },
  badgeGenerateText: {
    ...typography.caption,
    color: colors.primary,
    fontWeight: '600',
  },
});
