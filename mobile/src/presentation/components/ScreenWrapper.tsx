import React from 'react';
import { KeyboardAvoidingView, Platform, RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, spacing } from '@/core/theme';

interface ScreenWrapperProps {
  children: React.ReactNode;
  scrollable?: boolean;
  padded?: boolean;
  refreshing?: boolean;
  onRefresh?: () => void;
}

export default function ScreenWrapper({
  children,
  scrollable = true,
  padded = true,
  refreshing,
  onRefresh,
}: ScreenWrapperProps) {
  const content = (
    <View style={[styles.inner, padded && styles.padded]}>{children}</View>
  );

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        {scrollable ? (
          <ScrollView
            contentContainerStyle={styles.scroll}
            showsVerticalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
            refreshControl={
              onRefresh ? (
                <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} />
              ) : undefined
            }
          >
            {content}
          </ScrollView>
        ) : (
          content
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background,
  },
  flex: {
    flex: 1,
  },
  scroll: {
    flexGrow: 1,
  },
  inner: {
    flex: 1,
  },
  padded: {
    padding: spacing.md,
  },
});
