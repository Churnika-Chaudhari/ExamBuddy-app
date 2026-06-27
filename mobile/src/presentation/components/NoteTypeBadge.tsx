import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/core/theme';
import type { Note } from '@/domain/types';

const TYPE_LABELS: Record<Note['type'], string> = {
  generated: 'AI Generated',
  simplified: 'Simplified',
  manual: 'Manual',
};

const TYPE_COLORS: Record<Note['type'], { bg: string; text: string; border: string }> = {
  generated: {
    bg: colors.primaryLight,
    text: colors.primaryDark,
    border: colors.primary + '33',
  },
  simplified: {
    bg: colors.successLight,
    text: '#166534',
    border: colors.success + '33',
  },
  manual: {
    bg: colors.surfaceAlt,
    text: colors.textSecondary,
    border: colors.border,
  },
};

interface NoteTypeBadgeProps {
  type: Note['type'];
}

export default function NoteTypeBadge({ type }: NoteTypeBadgeProps) {
  const palette = TYPE_COLORS[type] ?? TYPE_COLORS.manual;
  const label = TYPE_LABELS[type] ?? type;

  return (
    <View
      style={[
        styles.badge,
        { backgroundColor: palette.bg, borderColor: palette.border },
      ]}
    >
      <Text style={[styles.text, { color: palette.text }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    borderRadius: radius.sm,
    borderWidth: 1,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    marginTop: 4,
  },
  text: {
    fontSize: 11,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
});
