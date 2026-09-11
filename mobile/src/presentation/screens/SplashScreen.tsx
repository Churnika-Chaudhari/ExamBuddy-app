import { useEffect } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';

import { colors } from '@/core/theme';
import type { RootStackParamList } from '@/navigation/types';
import { useAuthStore } from '@/store/authStore';

type Nav = NativeStackNavigationProp<RootStackParamList, 'Splash'>;

/** Kept for compatibility. Startup no longer waits here — token routing is in App.tsx. */
export default function SplashScreen() {
  const navigation = useNavigation<Nav>();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (isAuthenticated) {
      navigation.replace('Main', { screen: 'Dashboard' });
    } else {
      navigation.replace('Auth', { screen: 'Login' });
    }
  }, [isAuthenticated, navigation]);

  return (
    <View style={styles.container}>
      <ActivityIndicator color={colors.primary} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
