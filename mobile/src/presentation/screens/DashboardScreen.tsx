import { useCallback, useState } from 'react';
import { Alert, Pressable, StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, spacing, typography } from '@/core/theme';
import { getErrorMessage } from '@/data/api/client';
import type { RecentActivity } from '@/domain/types';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';
import EmptyState from '@/presentation/components/EmptyState';
import ScreenWrapper, { TAB_SCREEN_EDGES } from '@/presentation/components/ScreenWrapper';
import StatCard from '@/presentation/components/StatCard';
import { useAuthStore } from '@/store/authStore';
import { useDashboardStore } from '@/store/dashboardStore';
import { useUIStore } from '@/store/uiStore';
import { formatRelativeTime } from '@/utils/formatRelativeTime';

type Nav = NativeStackNavigationProp<RootStackParamList>;

const QUICK_ACTIONS = [
  {
    key: 'upload',
    title: 'Upload PYQs',
    desc: 'Upload question papers',
    icon: 'cloud-upload-outline' as const,
    color: colors.primary,
    bg: colors.primaryLight,
    onPress: (nav: Nav) => nav.navigate('UploadPYQ'),
  },
  {
    key: 'notes',
    title: 'Generate Notes',
    desc: 'AI study notes',
    icon: 'book-outline' as const,
    color: colors.warning,
    bg: colors.warningLight,
    onPress: (nav: Nav) => nav.navigate('Main', { screen: 'Notes' }),
  },
  {
    key: 'quiz',
    title: 'Generate Quiz',
    desc: 'Subject-based quiz',
    icon: 'help-circle-outline' as const,
    color: colors.success,
    bg: colors.successLight,
    onPress: (nav: Nav) => nav.navigate('Main', { screen: 'Quiz' }),
  },
  {
    key: 'analytics',
    title: 'View Analytics',
    desc: 'Quiz performance',
    icon: 'analytics-outline' as const,
    color: colors.primaryDark,
    bg: colors.primaryLight,
    onPress: (nav: Nav) => nav.navigate('QuizHistory'),
  },
];

function activityIcon(type: string): keyof typeof Ionicons.glyphMap {
  if (type.includes('quiz')) return 'help-circle-outline';
  if (type.includes('note')) return 'book-outline';
  if (type.includes('analysis') || type.includes('pyq')) return 'analytics-outline';
  return 'document-text-outline';
}

export default function DashboardScreen() {
  const navigation = useNavigation<Nav>();
  const user = useAuthStore((s) => s.user);
  const { data, isLoading, fetchDashboard, clearActivities, deleteActivity } = useDashboardStore();
  const showSnackbar = useUIStore((s) => s.showSnackbar);
  const [clearing, setClearing] = useState(false);

  useFocusEffect(
    useCallback(() => {
      fetchDashboard();
    }, [fetchDashboard])
  );

  const confirmClearAll = () => {
    Alert.alert(
      'Clear Recent Activity?',
      'This will remove all recent activity records.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            setClearing(true);
            try {
              await clearActivities();
              showSnackbar('Recent activity cleared', 'success');
            } catch (err) {
              showSnackbar(getErrorMessage(err), 'error');
            } finally {
              setClearing(false);
            }
          },
        },
      ]
    );
  };

  const confirmDeleteItem = (item: RecentActivity) => {
    Alert.alert('Delete Activity?', `Remove "${item.title}" from recent activity?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await deleteActivity(item.ref_id, item.type);
            showSnackbar('Activity removed', 'success');
          } catch (err) {
            showSnackbar(getErrorMessage(err), 'error');
          }
        },
      },
    ]);
  };

  const stats = data?.stats;
  const activities = data?.recent_activity ?? [];

  return (
    <ScreenWrapper edges={TAB_SCREEN_EDGES} refreshing={isLoading} onRefresh={fetchDashboard}>
      <View style={styles.header}>
        <Text style={styles.greeting}>
          Hello, {user?.full_name?.split(' ')[0] ?? 'Student'}
        </Text>
        <Text style={styles.subtitle}>Ready to ace your exams?</Text>
      </View>

      {isLoading && !data ? (
        <ActivityIndicator color={colors.primary} style={styles.loader} />
      ) : (
        <View style={styles.content}>
          <View style={styles.statsGrid}>
            <StatCard icon="document-text-outline" label="Documents" value={stats?.documents_count ?? 0} />
            <StatCard icon="analytics-outline" label="Analyses" value={stats?.analyses_count ?? 0} />
            <StatCard icon="book-outline" label="Notes" value={stats?.notes_count ?? 0} />
            <StatCard
              icon="trophy-outline"
              label="Avg Score"
              value={`${stats?.avg_quiz_score ?? 0}%`}
              color={colors.success}
            />
          </View>

          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <View style={styles.actionsGrid}>
            {QUICK_ACTIONS.map((action) => (
              <AppCard
                key={action.key}
                style={styles.actionCard}
                onPress={() => action.onPress(navigation)}
              >
                <View style={[styles.actionIcon, { backgroundColor: action.bg }]}>
                  <Ionicons name={action.icon} size={22} color={action.color} />
                </View>
                <Text style={styles.actionTitle}>{action.title}</Text>
                <Text style={styles.actionDesc}>{action.desc}</Text>
              </AppCard>
            ))}
          </View>

          <View style={styles.activityHeader}>
            <Text style={styles.sectionTitleInline}>Recent Activity</Text>
            {activities.length > 0 ? (
              <Pressable
                onPress={confirmClearAll}
                disabled={clearing}
                style={styles.clearAllBtn}
                hitSlop={8}
              >
                <Ionicons name="trash-outline" size={16} color={colors.error} />
                <Text style={styles.clearAllText}>Clear All</Text>
              </Pressable>
            ) : null}
          </View>

          {activities.length > 0 ? (
            activities.slice(0, 8).map((item, index) => (
              <AppCard key={`${item.ref_id}-${item.type}-${index}`} style={styles.activityCard}>
                <View style={styles.activityRow}>
                  <View style={styles.activityIconWrap}>
                    <Ionicons
                      name={activityIcon(item.type)}
                      size={18}
                      color={colors.primary}
                    />
                  </View>
                  <View style={styles.activityContent}>
                    <Text style={styles.activityTitle}>{item.title}</Text>
                    <Text style={styles.activityMeta}>
                      {item.type.replace(/_/g, ' ')} · {formatRelativeTime(item.timestamp)}
                    </Text>
                  </View>
                  <Pressable
                    onPress={() => confirmDeleteItem(item)}
                    hitSlop={8}
                    style={styles.deleteBtn}
                  >
                    <Ionicons name="close-circle-outline" size={22} color={colors.textMuted} />
                  </Pressable>
                </View>
              </AppCard>
            ))
          ) : (
            <View style={styles.emptyWrap}>
              <EmptyState
                icon="document-text-outline"
                title="No recent activity"
                subtitle="Start by uploading question papers using the Quick Actions section."
              />
              <AppButton
                label="Upload PYQs"
                onPress={() => navigation.navigate('UploadPYQ')}
                icon="cloud-upload-outline"
                style={styles.emptyCta}
              />
            </View>
          )}
        </View>
      )}
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  header: {
    marginBottom: spacing.lg,
    marginTop: spacing.sm,
  },
  greeting: {
    ...typography.h2,
    color: colors.text,
  },
  subtitle: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: 4,
  },
  loader: {
    marginTop: spacing.xl,
  },
  content: {
    flex: 1,
    paddingBottom: spacing.xl,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  sectionTitle: {
    ...typography.h3,
    color: colors.text,
    marginBottom: spacing.md,
  },
  sectionTitleInline: {
    ...typography.h3,
    color: colors.text,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  actionCard: {
    flexGrow: 1,
    flexBasis: '46%',
    minWidth: '46%',
    maxWidth: '100%',
    padding: spacing.md,
  },
  actionIcon: {
    width: 40,
    height: 40,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  actionTitle: {
    ...typography.label,
    color: colors.text,
  },
  actionDesc: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
  },
  activityHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.md,
  },
  clearAllBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
  },
  clearAllText: {
    ...typography.caption,
    color: colors.error,
    fontWeight: '600',
  },
  activityCard: {
    marginBottom: spacing.sm,
    padding: spacing.md,
  },
  activityRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  activityIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.md,
  },
  activityContent: {
    flex: 1,
  },
  activityTitle: {
    ...typography.bodySmall,
    color: colors.text,
    fontWeight: '600',
  },
  activityMeta: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 2,
    textTransform: 'capitalize',
  },
  deleteBtn: {
    padding: spacing.xs,
  },
  emptyWrap: {
    marginBottom: spacing.lg,
  },
  emptyCta: {
    marginTop: spacing.md,
    marginHorizontal: spacing.xl,
  },
});
