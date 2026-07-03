import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { Text, TextInput, HelperText } from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { ENV } from '@/core/config/apiConfig';
import { colors, spacing, typography } from '@/core/theme';
import type { AuthStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppLogo from '@/presentation/components/AppLogo';
import ScreenWrapper, { HEADERLESS_SCREEN_EDGES } from '@/presentation/components/ScreenWrapper';
import { getErrorMessage } from '@/data/api/client';
import { useAuthStore } from '@/store/authStore';
import { useNetworkStore } from '@/store/networkStore';
import { useUIStore } from '@/store/uiStore';

type Nav = NativeStackNavigationProp<AuthStackParamList, 'Login'>;

export default function LoginScreen() {
  const navigation = useNavigation<Nav>();
  const { login, isLoading, error, clearError } = useAuthStore();
  const {
    healthStatus,
    healthMessage,
    healthDetail,
    isChecking,
    runHealthCheck,
  } = useNetworkStore();
  const showSnackbar = useUIStore((s) => s.showSnackbar);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const backendOk = healthStatus === 'connected';

  useEffect(() => {
    if (healthStatus === 'checking') {
      runHealthCheck();
    }
  }, [healthStatus, runHealthCheck]);

  const handleLogin = async () => {
    clearError();
    if (!backendOk) {
      showSnackbar(healthDetail ?? healthMessage ?? 'Backend is not reachable', 'error');
      return;
    }
    if (!email || !password) {
      showSnackbar('Please fill in all fields', 'error');
      return;
    }
    try {
      await login(email.trim(), password);
      navigation.getParent()?.reset({
        index: 0,
        routes: [{ name: 'Main', params: { screen: 'Dashboard' } }],
      });
    } catch (err) {
      showSnackbar(getErrorMessage(err), 'error');
    }
  };

  return (
    <ScreenWrapper edges={HEADERLESS_SCREEN_EDGES}>
      <View style={styles.logoRow}>
        <AppLogo size="small" showWordmark />
      </View>
      <View style={styles.header}>
        <Text style={styles.title}>Welcome back</Text>
        <Text style={styles.subtitle}>Sign in to continue your study journey</Text>
      </View>

      <Pressable
        style={[styles.backendBanner, backendOk ? styles.backendOk : styles.backendBad]}
        onPress={() => runHealthCheck()}
        disabled={isChecking}
      >
        <Ionicons
          name={backendOk ? 'checkmark-circle' : 'alert-circle'}
          size={18}
          color={backendOk ? colors.success : colors.error}
        />
        <View style={styles.backendTextWrap}>
          <Text style={styles.backendTitle}>
            {isChecking ? 'Checking backend…' : healthMessage}
          </Text>
          {!backendOk && healthDetail ? (
            <Text style={styles.backendDetail} numberOfLines={3}>
              {healthDetail}
            </Text>
          ) : null}
          {__DEV__ ? (
            <Text style={styles.backendUrl} numberOfLines={1}>
              {ENV.API_URL}
            </Text>
          ) : null}
        </View>
        <Text style={styles.retryText}>{isChecking ? '…' : 'Retry'}</Text>
      </Pressable>

      <View style={styles.form}>
        <TextInput
          label="Email"
          value={email}
          onChangeText={setEmail}
          mode="outlined"
          keyboardType="email-address"
          autoCapitalize="none"
          style={styles.input}
          outlineColor={colors.border}
          activeOutlineColor={colors.primary}
        />
        <TextInput
          label="Password"
          value={password}
          onChangeText={setPassword}
          mode="outlined"
          secureTextEntry={!showPassword}
          right={
            <TextInput.Icon
              icon={showPassword ? 'eye-off' : 'eye'}
              onPress={() => setShowPassword(!showPassword)}
            />
          }
          style={styles.input}
          outlineColor={colors.border}
          activeOutlineColor={colors.primary}
        />
        {error ? <HelperText type="error">{error}</HelperText> : null}

        <AppButton
          label="Sign In"
          onPress={handleLogin}
          loading={isLoading}
          style={styles.button}
        />
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>Don't have an account?</Text>
        <Text
          style={styles.link}
          onPress={() => navigation.navigate('Signup')}
        >
          Create account
        </Text>
      </View>
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  logoRow: {
    alignItems: 'center',
    marginTop: spacing.lg,
    marginBottom: spacing.md,
  },
  header: {
    marginTop: spacing.sm,
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
  backendBanner: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    padding: spacing.md,
    borderRadius: 12,
    marginBottom: spacing.md,
    borderWidth: 1,
  },
  backendOk: {
    backgroundColor: colors.successLight,
    borderColor: colors.successLight,
  },
  backendBad: {
    backgroundColor: colors.errorLight,
    borderColor: colors.errorLight,
  },
  backendTextWrap: {
    flex: 1,
    minWidth: 0,
  },
  backendTitle: {
    ...typography.caption,
    fontWeight: '700',
    color: colors.text,
  },
  backendDetail: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
    lineHeight: 18,
  },
  backendUrl: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 4,
  },
  retryText: {
    ...typography.caption,
    color: colors.primary,
    fontWeight: '700',
  },
  form: {
    gap: spacing.sm,
  },
  input: {
    backgroundColor: colors.background,
    marginBottom: spacing.sm,
  },
  button: {
    marginTop: spacing.md,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: spacing.xl,
    gap: spacing.xs,
  },
  footerText: {
    color: colors.textSecondary,
  },
  link: {
    color: colors.primary,
    fontWeight: '600',
  },
});
