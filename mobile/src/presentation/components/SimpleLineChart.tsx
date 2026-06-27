import { StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';

import { colors, radius, spacing, typography } from '@/core/theme';

export interface LineChartPoint {
  label: string;
  value: number;
}

interface SimpleLineChartProps {
  data: LineChartPoint[];
  height?: number;
  color?: string;
}

export default function SimpleLineChart({
  data,
  height = 140,
  color = colors.primary,
}: SimpleLineChartProps) {
  if (!data.length) {
    return <Text style={styles.empty}>No trend data yet</Text>;
  }

  const max = Math.max(...data.map((d) => d.value), 1);
  const min = Math.min(...data.map((d) => d.value), 0);
  const range = max - min || 1;
  const chartHeight = height - 40;

  return (
    <View style={[styles.container, { height }]}>
      <View style={[styles.chartArea, { height: chartHeight }]}>
        {data.map((point, index) => {
          const barH = ((point.value - min) / range) * (chartHeight - 8) + 8;
          return (
            <View key={`${point.label}-${index}`} style={styles.column}>
              <Text style={styles.pointValue}>{Math.round(point.value)}</Text>
              <View style={styles.track}>
                <View style={[styles.bar, { height: barH, backgroundColor: color }]} />
              </View>
            </View>
          );
        })}
      </View>
      <View style={styles.labels}>
        {data.map((point, index) => (
          <Text
            key={`lbl-${point.label}-${index}`}
            style={styles.xLabel}
            numberOfLines={1}
          >
            {point.label}
          </Text>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingTop: spacing.sm,
  },
  chartArea: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    gap: 6,
    paddingHorizontal: spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  column: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'flex-end',
    height: '100%',
  },
  pointValue: {
    ...typography.caption,
    color: colors.textSecondary,
    fontSize: 10,
    fontWeight: '700',
    marginBottom: 2,
  },
  track: {
    width: '60%',
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: colors.surfaceAlt,
    borderTopLeftRadius: radius.sm,
    borderTopRightRadius: radius.sm,
    overflow: 'hidden',
  },
  bar: {
    width: '100%',
    borderTopLeftRadius: radius.sm,
    borderTopRightRadius: radius.sm,
    minHeight: 4,
  },
  labels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.xs,
    paddingHorizontal: spacing.xs,
  },
  xLabel: {
    ...typography.caption,
    color: colors.textMuted,
    fontSize: 9,
    flex: 1,
    textAlign: 'center',
  },
  empty: {
    ...typography.caption,
    color: colors.textMuted,
    textAlign: 'center',
    padding: spacing.md,
  },
});
