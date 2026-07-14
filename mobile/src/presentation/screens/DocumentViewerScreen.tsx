import { useCallback, useState } from 'react';
import { ActivityIndicator, Linking, Platform, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import { WebView } from 'react-native-webview';
import { Ionicons } from '@expo/vector-icons';

import { colors, spacing, typography } from '@/core/theme';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';

type Route = RouteProp<RootStackParamList, 'DocumentViewer'>;

function pdfViewerUri(fileUrl: string): string {
  if (Platform.OS === 'android') {
    return `https://docs.google.com/gview?embedded=true&url=${encodeURIComponent(fileUrl)}`;
  }
  return fileUrl;
}

export default function DocumentViewerScreen() {
  const route = useRoute<Route>();
  const { title, fileUrl } = route.params;
  const [loading, setLoading] = useState(true);
  const [webError, setWebError] = useState(false);

  const handleOpenExternal = useCallback(async () => {
    await Linking.openURL(fileUrl);
  }, [fileUrl]);

  if (webError) {
    return (
      <ScreenWrapper scrollable={false}>
        <View style={styles.fallback}>
          <Ionicons name="document-text-outline" size={48} color={colors.primary} />
          <Text style={styles.fallbackTitle}>{title}</Text>
          <Text style={styles.fallbackText}>
            In-app preview is unavailable. Open the PDF in your device&apos;s viewer instead.
          </Text>
          <AppButton label="Open PDF" onPress={handleOpenExternal} icon="open-outline" />
        </View>
      </ScreenWrapper>
    );
  }

  return (
    <ScreenWrapper scrollable={false} padded={false}>
      <View style={styles.container}>
        {loading ? (
          <View style={styles.loadingOverlay}>
            <ActivityIndicator size="large" color={colors.primary} />
            <Text style={styles.loadingText}>Loading PDF…</Text>
          </View>
        ) : null}
        <WebView
          source={{ uri: pdfViewerUri(fileUrl) }}
          style={styles.webview}
          onLoadEnd={() => setLoading(false)}
          onError={() => {
            setLoading(false);
            setWebError(true);
          }}
          onHttpError={() => {
            setLoading(false);
            setWebError(true);
          }}
          startInLoadingState
          scalesPageToFit
          javaScriptEnabled
          domStorageEnabled
        />
        <View style={styles.toolbar}>
          <AppButton
            label="Open Externally"
            mode="outlined"
            icon="open-outline"
            onPress={handleOpenExternal}
          />
        </View>
      </View>
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  webview: {
    flex: 1,
    backgroundColor: colors.background,
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
    zIndex: 1,
  },
  loadingText: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  toolbar: {
    padding: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.background,
  },
  fallback: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.lg,
    gap: spacing.md,
  },
  fallbackTitle: {
    ...typography.h3,
    color: colors.text,
    textAlign: 'center',
  },
  fallbackText: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
});
