import { StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';

import { colors, radius, spacing, typography } from '@/core/theme';
import { moderateScale } from '@/core/theme/responsive';

export interface BarChartItem {
  label: string;
  value: number;
  color?: string;
}

interface SimpleBarChartProps {
  data: BarChartItem[];
  maxValue?: number;
  unit?: string;
  height?: number;
}

export default function SimpleBarChart({
  data,
  maxValue,
  unit = '%',
  height = 160,
}: SimpleBarChartProps) {
  if (!data.length) {
    return <Text style={styles.empty}>No data yet</Text>;
  }

  const max = maxValue ?? Math.max(...data.map((d) => d.value), 1);

  return (
    <View style={[styles.container, { height }]}>
      {data.map((item) => {
        const pct = Math.max(4, (item.value / max) * 100);
        return (
          <View key={item.label} style={styles.row}>
            <Text style={styles.label} numberOfLines={1}>
              {item.label}
            </Text>
            <View style={styles.barTrack}>
              <View
                style={[
                  styles.barFill,
                  {
                    width: `${pct}%`,
                    backgroundColor: item.color ?? colors.primary,
                  },
                ]}
              />
            </View>
            <Text style={styles.value}>
              {item.value}
              {unit}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.sm,
    justifyContent: 'center',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  label: {
    ...typography.caption,
    color: colors.textSecondary,
    width: moderateScale(72),
    flexShrink: 0,
  },
  barTrack: {
    flex: 1,
    height: 10,
    backgroundColor: colors.surfaceAlt,
    borderRadius: radius.full,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: radius.full,
  },
  value: {
    ...typography.caption,
    color: colors.text,
    width: moderateScale(42),
    textAlign: 'right',
    fontWeight: '600',
  },
  empty: {
    ...typography.caption,
    color: colors.textMuted,
    textAlign: 'center',
    padding: spacing.md,
  },
});
