import React from 'react';
import { StyleSheet, View, ViewStyle } from 'react-native';
import { Card } from 'react-native-paper';

import { colors, radius, shadows, spacing } from '@/core/theme';

interface AppCardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  onPress?: () => void;
}

export default function AppCard({ children, style, onPress }: AppCardProps) {
  if (onPress) {
    return (
      <Card style={[styles.card, style]} onPress={onPress} mode="elevated">
        <Card.Content style={styles.content}>{children}</Card.Content>
      </Card>
    );
  }

  return (
    <View style={[styles.card, styles.wrapper, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    ...shadows.card,
  },
  wrapper: {
    padding: spacing.md,
  },
  content: {
    paddingVertical: spacing.sm,
  },
});
