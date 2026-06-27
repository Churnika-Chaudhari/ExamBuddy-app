import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { ENV } from '@/core/config/apiConfig';
import { colors, spacing, typography } from '@/core/theme';
import type { RootStackParamList } from '@/navigation/types';
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
    }, 1200);

    return () => clearTimeout(timer);
  }, [isInitialized, isAuthenticated, backendChecked, navigation]);

  const backendOk = healthStatus === 'connected';

  return (
    <View style={styles.container}>
      <View style={styles.logoWrap}>
        <Ionicons name="school" size={48} color={colors.primary} />
      </View>
      <Text style={styles.title}>SmartStudy</Text>
      <Text style={styles.subtitle}>Study smarter, score higher</Text>

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
            <Text style={styles.statusText}>Checking backend…</Text>
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
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
  },
  logoWrap: {
    width: 96,
    height: 96,
    borderRadius: 28,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  title: {
    ...typography.h1,
    color: colors.text,
  },
  subtitle: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    marginTop: spacing.lg,
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
    marginTop: spacing.lg,
  },
});
