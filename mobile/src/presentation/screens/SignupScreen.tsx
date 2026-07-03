import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text, TextInput, HelperText } from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';

import { colors, spacing, typography } from '@/core/theme';
import type { AuthStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import ScreenWrapper, { HEADERLESS_SCREEN_EDGES } from '@/presentation/components/ScreenWrapper';
import { getErrorMessage } from '@/data/api/client';
import { useAuthStore } from '@/store/authStore';
import { useUIStore } from '@/store/uiStore';

type Nav = NativeStackNavigationProp<AuthStackParamList, 'Signup'>;

export default function SignupScreen() {
  const navigation = useNavigation<Nav>();
  const { register, isLoading, error, clearError } = useAuthStore();
  const showSnackbar = useUIStore((s) => s.showSnackbar);

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleSignup = async () => {
    clearError();
    if (!fullName || !email || !password) {
      showSnackbar('Please fill in all fields', 'error');
      return;
    }
    if (password !== confirmPassword) {
      showSnackbar('Passwords do not match', 'error');
      return;
    }
    if (password.length < 8) {
      showSnackbar('Password must be at least 8 characters', 'error');
      return;
    }
    try {
      await register(email.trim(), password, fullName.trim());
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
      <View style={styles.header}>
        <Text style={styles.title}>Create account</Text>
        <Text style={styles.subtitle}>Start analyzing PYQs with AI</Text>
      </View>

      <View style={styles.form}>
        <TextInput
          label="Full Name"
          value={fullName}
          onChangeText={setFullName}
          mode="outlined"
          style={styles.input}
          outlineColor={colors.border}
          activeOutlineColor={colors.primary}
        />
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
        <TextInput
          label="Confirm Password"
          value={confirmPassword}
          onChangeText={setConfirmPassword}
          mode="outlined"
          secureTextEntry={!showPassword}
          style={styles.input}
          outlineColor={colors.border}
          activeOutlineColor={colors.primary}
        />
        {error ? <HelperText type="error">{error}</HelperText> : null}

        <AppButton
          label="Create Account"
          onPress={handleSignup}
          loading={isLoading}
          style={styles.button}
        />
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>Already have an account?</Text>
        <Text style={styles.link} onPress={() => navigation.navigate('Login')}>
          Sign in
        </Text>
      </View>
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  header: {
    marginTop: spacing.xl,
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
