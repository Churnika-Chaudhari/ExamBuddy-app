import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { ActivityIndicator } from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, spacing } from '@/core/theme';
import type { RootStackParamList } from '@/navigation/types';
import AppLogo from '@/presentation/components/AppLogo';
import { useAuthStore } from '@/store/authStore';
import { useNetworkStore } from '@/store/networkStore';

type Nav = NativeStackNavigationProp<RootStackParamList, 'Splash'>;

export default function SplashScreen() {
  const navigation = useNavigation<Nav>();
  const { initialize, isAuthenticated, isInitialized } = useAuthStore();
  const { runHealthCheck } = useNetworkStore();
  const [backendChecked, setBackendChecked] = useState(false);

  useEffect(() => {
    initialize();
    runHealthCheck().finally(() => setBackendChecked(true));
  }, [initialize, runHealthCheck]);

  useEffect(() => {
    if (!isInitialized || !backendChecked) return;

    const timer = setTimeout(() => {
      if (isAuthenticated) {
        navigation.replace('Main', { screen: 'Dashboard' });
      } else {
        navigation.replace('Auth', { screen: 'Login' });
      }
    }, 1600);

    return () => clearTimeout(timer);
  }, [isInitialized, isAuthenticated, backendChecked, navigation]);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.hero}>
        <AppLogo size="splash" />
      </View>

      <View style={styles.footer}>
        <ActivityIndicator size="small" color={colors.primary} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.lg,
  },
  hero: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  footer: {
    alignItems: 'center',
    paddingBottom: spacing.md,
  },
});
