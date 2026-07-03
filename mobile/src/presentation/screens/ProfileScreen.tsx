import { useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { Text, TextInput, Avatar } from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, spacing, typography } from '@/core/theme';
import { fontScale } from '@/core/theme/responsive';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import ScreenWrapper, { TAB_SCREEN_EDGES } from '@/presentation/components/ScreenWrapper';
import { profileApi } from '@/data/api/endpoints';
import { useAuthStore } from '@/store/authStore';
import { useUIStore } from '@/store/uiStore';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export default function ProfileScreen() {
  const navigation = useNavigation<Nav>();
  const { user, logout } = useAuthStore();
  const showSnackbar = useUIStore((s) => s.showSnackbar);

  const [fullName, setFullName] = useState(user?.full_name ?? '');
  const [institution, setInstitution] = useState(user?.institution ?? '');
  const [course, setCourse] = useState(user?.course ?? '');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await profileApi.update({
        full_name: fullName,
        institution: institution || undefined,
        course: course || undefined,
      });
      showSnackbar('Profile updated', 'success');
    } catch {
      showSnackbar('Failed to update profile', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign Out',
        style: 'destructive',
        onPress: async () => {
          await logout();
          navigation.reset({
            index: 0,
            routes: [{ name: 'Auth', params: { screen: 'Login' } }],
          });
        },
      },
    ]);
  };

  const initials = user?.full_name
    ?.split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) ?? 'SS';

  return (
    <ScreenWrapper edges={TAB_SCREEN_EDGES}>
      <View style={styles.profileHeader}>
        <Avatar.Text
          size={72}
          label={initials}
          style={styles.avatar}
          labelStyle={styles.avatarLabel}
        />
        <Text style={styles.name}>{user?.full_name}</Text>
        <Text style={styles.email}>{user?.email}</Text>
      </View>

      <AppCard style={styles.formCard}>
        <Text style={styles.sectionTitle}>Personal Info</Text>
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
          label="Institution"
          value={institution}
          onChangeText={setInstitution}
          mode="outlined"
          placeholder="College / University"
          style={styles.input}
          outlineColor={colors.border}
          activeOutlineColor={colors.primary}
        />
        <TextInput
          label="Course"
          value={course}
          onChangeText={setCourse}
          mode="outlined"
          placeholder="e.g. B.Tech Computer Science"
          style={styles.input}
          outlineColor={colors.border}
          activeOutlineColor={colors.primary}
        />
        <AppButton label="Save Changes" onPress={handleSave} loading={isSaving} />
      </AppCard>

      <AppCard style={styles.menuCard}>
        <MenuItem icon="cloud-upload-outline" label="Upload PYQ" onPress={() => navigation.navigate('UploadPYQ')} />
        <MenuItem icon="documents-outline" label="Uploaded Documents" onPress={() => navigation.navigate('UploadedDocuments')} />
        <MenuItem icon="book-outline" label="My Notes" onPress={() => navigation.navigate('Main', { screen: 'Notes' })} />
      </AppCard>

      <AppButton
        label="Sign Out"
        mode="outlined"
        onPress={handleLogout}
        icon="exit-to-app"
        style={styles.logoutBtn}
      />
    </ScreenWrapper>
  );
}

function MenuItem({
  icon,
  label,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}) {
  return (
    <AppCard style={styles.menuItem} onPress={onPress}>
      <View style={styles.menuRow}>
        <Ionicons name={icon} size={22} color={colors.primary} />
        <Text style={styles.menuLabel}>{label}</Text>
        <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
      </View>
    </AppCard>
  );
}

const styles = StyleSheet.create({
  profileHeader: {
    alignItems: 'center',
    paddingVertical: spacing.lg,
  },
  avatar: {
    backgroundColor: colors.primary,
    marginBottom: spacing.md,
  },
  avatarLabel: {
    fontSize: fontScale(28),
    fontWeight: '600',
  },
  name: {
    ...typography.h2,
    color: colors.text,
  },
  email: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: 4,
  },
  formCard: {
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  sectionTitle: {
    ...typography.h3,
    color: colors.text,
    marginBottom: spacing.md,
  },
  input: {
    backgroundColor: colors.background,
    marginBottom: spacing.md,
  },
  menuCard: {
    marginBottom: spacing.lg,
  },
  menuItem: {
    padding: spacing.md,
    marginBottom: spacing.xs,
  },
  menuRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  menuLabel: {
    ...typography.body,
    color: colors.text,
    flex: 1,
  },
  logoutBtn: {
    marginBottom: spacing.xl,
    borderColor: colors.error,
  },
});
