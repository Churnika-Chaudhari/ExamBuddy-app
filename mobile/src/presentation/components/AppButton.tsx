import React from 'react';
import { StyleSheet } from 'react-native';
import { Button } from 'react-native-paper';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';

import { colors, radius } from '@/core/theme';

interface AppButtonProps {
  label: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  mode?: 'contained' | 'outlined' | 'text';
  icon?: string;
  style?: object;
}

function renderButtonIcon(icon: string) {
  return ({ size, color }: { size: number; color: string }) => {
    if (icon in Ionicons.glyphMap) {
      return <Ionicons name={icon as keyof typeof Ionicons.glyphMap} size={size} color={color} />;
    }
    return (
      <MaterialCommunityIcons
        name={icon as keyof typeof MaterialCommunityIcons.glyphMap}
        size={size}
        color={color}
      />
    );
  };
}

export default function AppButton({
  label,
  onPress,
  loading = false,
  disabled = false,
  mode = 'contained',
  icon,
  style,
}: AppButtonProps) {
  return (
    <Button
      mode={mode}
      onPress={onPress}
      loading={loading}
      disabled={disabled || loading}
      icon={icon ? renderButtonIcon(icon) : undefined}
      style={[styles.button, style]}
      contentStyle={styles.content}
      labelStyle={styles.label}
      buttonColor={mode === 'contained' ? colors.primary : undefined}
      textColor={mode === 'contained' ? colors.white : colors.primary}
    >
      {label}
    </Button>
  );
}

const styles = StyleSheet.create({
  button: {
    borderRadius: radius.md,
  },
  content: {
    paddingVertical: 6,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
  },
});
