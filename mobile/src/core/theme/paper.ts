import { MD3LightTheme, configureFonts } from 'react-native-paper';

import { colors, radius } from './index';

const fontConfig = {
  fontFamily: 'System',
};

export const paperTheme = {
  ...MD3LightTheme,
  roundness: radius.md,
  colors: {
    ...MD3LightTheme.colors,
    primary: colors.primary,
    onPrimary: colors.white,
    primaryContainer: colors.primaryLight,
    onPrimaryContainer: colors.primaryDark,
    secondary: colors.primary,
    background: colors.background,
    surface: colors.surface,
    surfaceVariant: colors.surfaceAlt,
    onSurface: colors.text,
    onSurfaceVariant: colors.textSecondary,
    outline: colors.border,
    error: colors.error,
  },
  fonts: configureFonts({ config: fontConfig }),
};
