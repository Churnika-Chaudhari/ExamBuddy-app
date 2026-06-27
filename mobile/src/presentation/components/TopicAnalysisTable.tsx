import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/core/theme';

export interface TopicFrequencyRow {
  topic: string;
  unit: string;
  frequency: number;
}

/** @deprecated Use TopicFrequencyRow */
export interface AcademicTopicRow {
  topic: string;
  frequency: number;
  unit?: string;
}

interface TopicAnalysisTableProps {
  rows: TopicFrequencyRow[];
}

export default function TopicAnalysisTable({ rows }: TopicAnalysisTableProps) {
  if (!rows.length) return null;

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
      <View style={styles.table}>
        <View style={styles.headerRow}>
          <Text style={[styles.headerCell, styles.topicCol]}>Standardized Topic</Text>
          <Text style={[styles.headerCell, styles.unitCol]}>Unit</Text>
          <Text style={[styles.headerCell, styles.freqCol]}>Frequency</Text>
        </View>
        {rows.map((row, index) => (
          <View
            key={`${row.topic}-${index}`}
            style={[styles.dataRow, index % 2 === 1 && styles.altRow]}
          >
            <Text style={[styles.dataCell, styles.topicCol]} numberOfLines={3}>
              {row.topic}
            </Text>
            <Text style={[styles.dataCell, styles.unitCol]} numberOfLines={2}>
              {row.unit}
            </Text>
            <Text style={[styles.dataCell, styles.freqCol, styles.freqText]}>
              {row.frequency}
            </Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  table: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    overflow: 'hidden',
    minWidth: '100%',
  },
  headerRow: {
    flexDirection: 'row',
    backgroundColor: colors.primaryLight,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
  },
  headerCell: {
    ...typography.caption,
    fontWeight: '700',
    color: colors.primaryDark,
  },
  dataRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  altRow: {
    backgroundColor: colors.surface,
  },
  dataCell: {
    ...typography.caption,
    color: colors.text,
  },
  topicCol: {
    flex: 1,
    minWidth: 160,
    paddingRight: spacing.sm,
  },
  unitCol: {
    width: 120,
    paddingRight: spacing.sm,
    color: colors.textSecondary,
  },
  freqCol: {
    width: 72,
    textAlign: 'center',
  },
  freqText: {
    fontWeight: '700',
    color: colors.primary,
  },
});
