import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { ActivityIndicator, Text } from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ENV } from '@/core/config/apiConfig';
import { colors, spacing, typography } from '@/core/theme';
import type { RootStackParamList } from '@/navigation/types';
import AppLogo from '@/presentation/components/AppLogo';
import { useAuthStore } from '@/store/authStore';
import { useNetworkStore } from '@/store/networkStore';

type Nav = NativeStackNavigationProp<RootStackParamList, 'Splash'>;

export default function SplashScreen() {
  const navigation = useNavigation<Nav>();
  const { initialize, isAuthenticated, isInitialized } = useAuthStore();
  const { runHealthCheck, healthStatus, healthMessage } = useNetworkStore();
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

  const backendOk = healthStatus === 'connected';

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.hero}>
        <AppLogo size="splash" />
      </View>

      <View style={styles.footer}>
        <View style={styles.statusRow}>
          {backendChecked ? (
            <>
              <Ionicons
                name={backendOk ? 'cloud-done-outline' : 'cloud-offline-outline'}
                size={16}
                color={backendOk ? colors.success : colors.error}
              />
              <Text style={[styles.statusText, backendOk ? styles.statusOk : styles.statusBad]}>
                {healthMessage}
              </Text>
            </>
          ) : (
            <>
              <ActivityIndicator size={14} color={colors.primary} />
              <Text style={styles.statusText}>Connecting to server…</Text>
            </>
          )}
        </View>

        {__DEV__ && backendChecked ? (
          <Text style={styles.devHint} numberOfLines={2}>
            {ENV.RUNTIME_PLATFORM} · {ENV.API_URL}
          </Text>
        ) : null}

        <ActivityIndicator size="small" color={colors.primary} style={styles.loader} />
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
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
  },
  statusText: {
    ...typography.caption,
    color: colors.textSecondary,
    flexShrink: 1,
  },
  statusOk: {
    color: colors.success,
    fontWeight: '600',
  },
  statusBad: {
    color: colors.error,
    fontWeight: '600',
  },
  devHint: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: spacing.xs,
    textAlign: 'center',
  },
  loader: {
    marginTop: spacing.md,
  },
});
