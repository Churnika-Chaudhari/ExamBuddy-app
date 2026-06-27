import { useCallback } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { useFocusEffect, useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, spacing, typography } from '@/core/theme';
import { fontScale, moderateScale } from '@/core/theme/responsive';
import AppCard from '@/presentation/components/AppCard';
import EmptyState from '@/presentation/components/EmptyState';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import SimpleBarChart from '@/presentation/components/SimpleBarChart';
import SimpleLineChart from '@/presentation/components/SimpleLineChart';
import type { RootStackParamList } from '@/navigation/types';
import { useQuizStore } from '@/store/quizStore';

type Route = RouteProp<RootStackParamList, 'QuizAnalysis'>;

function scoreColor(score: number) {
  if (score >= 75) return colors.success;
  if (score >= 50) return colors.warning;
  return colors.error;
}

function performanceLabel(score: number) {
  if (score >= 85) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 50) return 'Average';
  return 'Needs Work';
}

function StatTile({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: string;
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
}) {
  return (
    <AppCard style={styles.statTile}>
      <View style={[styles.statIcon, { backgroundColor: `${color}1A` }]}>
        <Ionicons name={icon} size={18} color={color} />
      </View>
      <View style={styles.statTextWrap}>
        <Text style={styles.statValue}>{value}</Text>
        <Text style={styles.statLabel}>{label}</Text>
      </View>
    </AppCard>
  );
}

function SectionHeader({
  icon,
  color,
  title,
  subtitle,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <View style={styles.sectionHeader}>
      <View style={[styles.sectionIcon, { backgroundColor: `${color}1A` }]}>
        <Ionicons name={icon} size={16} color={color} />
      </View>
      <View style={styles.flex}>
        <Text style={styles.sectionTitle}>{title}</Text>
        {subtitle ? <Text style={styles.sectionSubtitle}>{subtitle}</Text> : null}
      </View>
    </View>
  );
}

export default function QuizAnalysisScreen() {
  const route = useRoute<Route>();
  const { subject } = route.params;
  const { analysis, isLoading, fetchAnalysis } = useQuizStore();

  useFocusEffect(
    useCallback(() => {
      fetchAnalysis(subject);
    }, [fetchAnalysis, subject])
  );

  if (isLoading && !analysis) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (!analysis || analysis.total_quizzes_attempted === 0) {
    return (
      <ScreenWrapper>
        <EmptyState
          icon="analytics-outline"
          title={`No ${subject} quiz data yet`}
          subtitle={`Complete a ${subject} quiz to see performance insights`}
        />
      </ScreenWrapper>
    );
  }

  const avg = Math.round(analysis.average_score);
  const heroColor = scoreColor(avg);

  const weeklyChart = analysis.weekly_progress.map((w) => ({
    label: w.week.replace('W', 'W'),
    value: Math.round(w.average_score),
  }));

  const trendChart = analysis.score_trend.map((t) => ({
    label: t.date.split(' ')[0] ?? t.date,
    value: Math.round(t.score),
  }));

  const topicChart = analysis.topic_strength_distribution.slice(0, 8).map((t) => ({
    label: t.topic.length > 12 ? `${t.topic.slice(0, 11)}…` : t.topic,
    value: Math.round(t.accuracy_percentage),
    color: t.accuracy_percentage >= 70 ? colors.success : t.accuracy_percentage >= 45 ? colors.warning : colors.error,
  }));

  return (
    <ScreenWrapper refreshing={isLoading} onRefresh={() => fetchAnalysis(subject)}>
      {/* Hero performance card */}
      <AppCard style={styles.hero}>
        <View style={styles.heroLeft}>
          <Text style={styles.heroSubject} numberOfLines={1}>
            {subject}
          </Text>
          <Text style={styles.heroCaption}>Average Performance</Text>
          <View style={[styles.heroBadge, { backgroundColor: `${heroColor}1A` }]}>
            <Ionicons name="ribbon-outline" size={13} color={heroColor} />
            <Text style={[styles.heroBadgeText, { color: heroColor }]}>
              {performanceLabel(avg)}
            </Text>
          </View>
        </View>
        <View style={[styles.heroRing, { borderColor: heroColor }]}>
          <Text style={[styles.heroScore, { color: heroColor }]}>{avg}</Text>
          <Text style={styles.heroPercent}>%</Text>
        </View>
      </AppCard>

      {/* Stat tiles */}
      <View style={styles.statsGrid}>
        <StatTile
          label="Quizzes"
          value={String(analysis.total_quizzes_attempted)}
          icon="documents-outline"
          color={colors.primary}
        />
        <StatTile
          label="Highest"
          value={`${Math.round(analysis.highest_score)}%`}
          icon="trophy-outline"
          color={colors.success}
        />
        <StatTile
          label="Lowest"
          value={`${Math.round(analysis.lowest_score)}%`}
          icon="trending-down-outline"
          color={colors.error}
        />
        <StatTile
          label="Questions"
          value={String(analysis.total_questions_solved)}
          icon="help-circle-outline"
          color={colors.warning}
        />
      </View>

      {trendChart.length > 0 ? (
        <AppCard style={styles.card}>
          <SectionHeader
            icon="pulse-outline"
            color={colors.success}
            title="Score Trend"
            subtitle="Your recent attempt scores"
          />
          <SimpleLineChart data={trendChart} color={colors.success} />
        </AppCard>
      ) : null}

      {weeklyChart.length > 0 ? (
        <AppCard style={styles.card}>
          <SectionHeader
            icon="calendar-outline"
            color={colors.primary}
            title="Weekly Progress"
            subtitle="Average score per week"
          />
          <SimpleLineChart data={weeklyChart} color={colors.primary} />
        </AppCard>
      ) : null}

      {topicChart.length > 0 ? (
        <AppCard style={styles.card}>
          <SectionHeader
            icon="bar-chart-outline"
            color={colors.primaryDark}
            title="Topic Strength"
            subtitle="Accuracy by topic"
          />
          <SimpleBarChart data={topicChart} />
        </AppCard>
      ) : null}

      {analysis.strong_topics.length > 0 ? (
        <AppCard style={styles.card}>
          <SectionHeader
            icon="checkmark-circle-outline"
            color={colors.success}
            title="Strong Topics"
            subtitle="Keep it up"
          />
          {analysis.strong_topics.map((t) => (
            <View key={t.topic} style={styles.topicRow}>
              <Text style={styles.topicName} numberOfLines={1}>
                {t.topic}
              </Text>
              <View style={styles.topicBarTrack}>
                <View
                  style={[
                    styles.topicBarFill,
                    { width: `${Math.min(100, t.accuracy_percentage)}%`, backgroundColor: colors.success },
                  ]}
                />
              </View>
              <Text style={[styles.topicPct, { color: colors.success }]}>
                {Math.round(t.accuracy_percentage)}%
              </Text>
            </View>
          ))}
        </AppCard>
      ) : null}

      {analysis.weak_topics.length > 0 ? (
        <AppCard style={styles.card}>
          <SectionHeader
            icon="alert-circle-outline"
            color={colors.error}
            title="Weak Topics"
            subtitle="Focus your revision here"
          />
          {analysis.weak_topics.map((t) => (
            <View key={t.topic} style={styles.topicRow}>
              <Text style={styles.topicName} numberOfLines={1}>
                {t.topic}
              </Text>
              <View style={styles.topicBarTrack}>
                <View
                  style={[
                    styles.topicBarFill,
                    { width: `${Math.min(100, t.accuracy_percentage)}%`, backgroundColor: colors.error },
                  ]}
                />
              </View>
              <Text style={[styles.topicPct, { color: colors.error }]}>
                {Math.round(t.accuracy_percentage)}%
              </Text>
            </View>
          ))}
        </AppCard>
      ) : null}

      {analysis.improvement_suggestions.length > 0 ? (
        <AppCard style={StyleSheet.flatten([styles.card, styles.suggestCard])}>
          <SectionHeader
            icon="bulb-outline"
            color={colors.warning}
            title="Improvement Tips"
          />
          {analysis.improvement_suggestions.map((s, i) => (
            <View key={i} style={styles.suggestRow}>
              <View style={styles.suggestDot}>
                <Text style={styles.suggestNum}>{i + 1}</Text>
              </View>
              <Text style={styles.suggestText}>{s}</Text>
            </View>
          ))}
        </AppCard>
      ) : null}

      <View style={styles.footer} />
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
  },
  hero: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: spacing.lg,
    marginBottom: spacing.md,
  },
  heroLeft: {
    flex: 1,
    paddingRight: spacing.md,
  },
  heroSubject: {
    ...typography.h2,
    color: colors.text,
  },
  heroCaption: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: 2,
  },
  heroBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    alignSelf: 'flex-start',
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: radius.full,
    marginTop: spacing.sm,
  },
  heroBadgeText: {
    ...typography.caption,
    fontWeight: '700',
  },
  heroRing: {
    width: moderateScale(88),
    height: moderateScale(88),
    borderRadius: moderateScale(88) / 2,
    borderWidth: 6,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  heroScore: {
    fontSize: fontScale(30),
    fontWeight: '800',
  },
  heroPercent: {
    fontSize: fontScale(14),
    fontWeight: '700',
    color: colors.textMuted,
    marginTop: 6,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  statTile: {
    flexBasis: '47%',
    flexGrow: 1,
    minWidth: 140,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    padding: spacing.md,
  },
  statIcon: {
    width: moderateScale(36),
    height: moderateScale(36),
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  statTextWrap: {
    flex: 1,
  },
  statValue: {
    ...typography.h3,
    color: colors.text,
  },
  statLabel: {
    ...typography.caption,
    color: colors.textSecondary,
  },
  card: {
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  sectionIcon: {
    width: 32,
    height: 32,
    borderRadius: radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sectionTitle: {
    ...typography.label,
    color: colors.text,
  },
  sectionSubtitle: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 1,
  },
  topicRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  topicName: {
    ...typography.bodySmall,
    color: colors.text,
    flexBasis: '34%',
    flexShrink: 1,
  },
  topicBarTrack: {
    flex: 1,
    height: 8,
    borderRadius: radius.full,
    backgroundColor: colors.surfaceAlt,
    overflow: 'hidden',
  },
  topicBarFill: {
    height: '100%',
    borderRadius: radius.full,
  },
  topicPct: {
    ...typography.caption,
    fontWeight: '700',
    minWidth: moderateScale(38),
    textAlign: 'right',
  },
  suggestCard: {
    backgroundColor: colors.warningLight,
    borderColor: colors.warningLight,
  },
  suggestRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  suggestDot: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: colors.warning,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 1,
  },
  suggestNum: {
    fontSize: 11,
    fontWeight: '800',
    color: colors.white,
  },
  suggestText: {
    ...typography.bodySmall,
    color: colors.text,
    flex: 1,
    lineHeight: 20,
  },
  footer: {
    height: spacing.lg,
  },
});
