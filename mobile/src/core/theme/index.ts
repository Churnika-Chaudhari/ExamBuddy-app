export const colors = {
  primary: '#4A90D9',
  primaryLight: '#E8F4FD',
  primaryDark: '#2E6BAD',
  background: '#FFFFFF',
  surface: '#F8FAFC',
  surfaceAlt: '#F1F5F9',
  card: '#FFFFFF',
  text: '#1E293B',
  textSecondary: '#64748B',
  textMuted: '#94A3B8',
  border: '#E2E8F0',
  success: '#22C55E',
  successLight: '#DCFCE7',
  warning: '#F59E0B',
  warningLight: '#FEF3C7',
  error: '#EF4444',
  errorLight: '#FEE2E2',
  white: '#FFFFFF',
};

import { fontScale, moderateScale } from './responsive';

// Spacing scales gently with screen width so small phones feel tighter and
// large phones/tablets get a bit more breathing room.
export const spacing = {
  xs: moderateScale(4),
  sm: moderateScale(8),
  md: moderateScale(16),
  lg: moderateScale(24),
  xl: moderateScale(32),
  xxl: moderateScale(48),
};

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  full: 999,
};

// Font sizes adapt to the device so text never looks oversized on small
// screens or cramped on large ones.
export const typography = {
  h1: { fontSize: fontScale(28), fontWeight: '700' as const },
  h2: { fontSize: fontScale(22), fontWeight: '700' as const },
  h3: { fontSize: fontScale(18), fontWeight: '600' as const },
  body: { fontSize: fontScale(16), fontWeight: '400' as const },
  bodySmall: { fontSize: fontScale(14), fontWeight: '400' as const },
  caption: { fontSize: fontScale(12), fontWeight: '400' as const },
  label: { fontSize: fontScale(14), fontWeight: '600' as const },
};

export const shadows = {
  card: {
    shadowColor: '#64748B',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
};
