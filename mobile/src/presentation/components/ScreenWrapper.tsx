import React from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { SafeAreaView, type Edge } from 'react-native-safe-area-context';

import { colors, spacing } from '@/core/theme';

/** Tab screens: top inset only — bottom tab bar handles home indicator. */
export const TAB_SCREEN_EDGES: Edge[] = ['top'];

/** Auth and other headerless full-screen layouts. */
export const HEADERLESS_SCREEN_EDGES: Edge[] = ['top', 'bottom'];

/** Stack screens with a native header only need bottom inset. */
export const STACK_SCREEN_EDGES: Edge[] = ['bottom'];

interface ScreenWrapperProps {
  children: React.ReactNode;
  scrollable?: boolean;
  padded?: boolean;
  refreshing?: boolean;
  onRefresh?: () => void;
  edges?: Edge[];
}

export default function ScreenWrapper({
  children,
  scrollable = true,
  padded = true,
  refreshing,
  onRefresh,
  edges = STACK_SCREEN_EDGES,
}: ScreenWrapperProps) {
  const content = (
    <View style={[scrollable ? styles.scrollInner : styles.flexInner, padded && styles.padded]}>
      {children}
    </View>
  );

  return (
    <SafeAreaView style={styles.safe} edges={edges}>
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
  scrollInner: {
    flexGrow: 1,
  },
  flexInner: {
    flex: 1,
  },
  padded: {
    padding: spacing.md,
  },
});
