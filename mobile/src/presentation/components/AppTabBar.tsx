import { BottomTabBar, type BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { Platform, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, shadows } from '@/core/theme';

export default function AppTabBar(props: BottomTabBarProps) {
  return (
    <SafeAreaView edges={['bottom']} style={styles.safe}>
      <View style={styles.shell}>
        <BottomTabBar {...props} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    backgroundColor: colors.white,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    ...Platform.select({
      android: { elevation: 16 },
      ios: shadows.card,
      default: {},
    }),
  },
  shell: {
    backgroundColor: colors.white,
  },
});
