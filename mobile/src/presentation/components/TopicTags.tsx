import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/core/theme';
import { filterTopics } from '@/utils/topicFilter';

interface TopicTagsProps {
  topics: string[];
  maxVisible?: number;
  showLabel?: boolean;
}

export default function TopicTags({
  topics,
  maxVisible,
  showLabel = false,
}: TopicTagsProps) {
  const filtered = filterTopics(topics);
  if (!filtered.length) return null;

  const visible = maxVisible ? filtered.slice(0, maxVisible) : filtered;
  const remaining = maxVisible ? Math.max(filtered.length - maxVisible, 0) : 0;

  return (
    <View style={styles.wrapper}>
      {showLabel ? <Text style={styles.label}>Topics</Text> : null}
      <View style={styles.row}>
        {visible.map((topic, index) => (
          <View key={`${topic}-${index}`} style={styles.tag}>
            <Text style={styles.tagText} numberOfLines={2}>
              {topic}
            </Text>
          </View>
        ))}
        {remaining > 0 ? (
          <View style={[styles.tag, styles.moreTag]}>
            <Text style={styles.moreText}>+{remaining} more</Text>
          </View>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    width: '100%',
    marginBottom: spacing.sm,
  },
  label: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '600',
    marginBottom: spacing.xs,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    width: '100%',
  },
  tag: {
    maxWidth: '100%',
    backgroundColor: colors.primaryLight,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.primary + '33',
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
    marginRight: spacing.xs,
    marginBottom: spacing.xs,
  },
  tagText: {
    ...typography.caption,
    color: colors.primaryDark,
    fontWeight: '500',
    flexShrink: 1,
  },
  moreTag: {
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
  },
  moreText: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '600',
  },
});
