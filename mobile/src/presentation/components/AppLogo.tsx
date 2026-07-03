import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';

import { colors, radius, spacing, typography } from '@/core/theme';
import { moderateScale } from '@/core/theme/responsive';

interface AppLogoProps {
  size?: 'splash' | 'small' | 'icon';
  showWordmark?: boolean;
}

export default function AppLogo({ size = 'splash', showWordmark = false }: AppLogoProps) {
  const badgeSize = moderateScale(size === 'splash' ? 112 : size === 'small' ? 72 : 48);
  const iconSize = moderateScale(size === 'splash' ? 52 : size === 'small' ? 34 : 24);
  const capSize = moderateScale(size === 'splash' ? 22 : size === 'small' ? 14 : 10);

  return (
    <View style={styles.wrap}>
      <View
        style={[
          styles.badge,
          {
            width: badgeSize,
            height: badgeSize,
            borderRadius: moderateScale(size === 'icon' ? 14 : 28),
          },
        ]}
      >
        <View style={styles.iconStack}>
          <Ionicons name="book" size={iconSize} color={colors.white} />
          <View style={[styles.cap, { top: -capSize * 0.55, right: -capSize * 0.35 }]}>
            <Ionicons name="school" size={capSize} color={colors.primaryLight} />
          </View>
        </View>
      </View>

      {showWordmark || size === 'splash' ? (
        <>
          <Text style={[styles.brand, size === 'splash' ? styles.brandSplash : styles.brandSmall]}>
            ExamBuddy
          </Text>
          {size === 'splash' ? (
            <Text style={styles.tagline}>Study smarter, score higher</Text>
          ) : null}
        </>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
  },
  badge: {
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.primaryDark,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.28,
    shadowRadius: 16,
    elevation: 8,
  },
  iconStack: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  cap: {
    position: 'absolute',
  },
  brand: {
    color: colors.text,
    fontWeight: '700',
  },
  brandSplash: {
    ...typography.h1,
    marginTop: spacing.lg,
  },
  brandSmall: {
    ...typography.h3,
    marginTop: spacing.sm,
  },
  tagline: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.xs,
    textAlign: 'center',
  },
});
