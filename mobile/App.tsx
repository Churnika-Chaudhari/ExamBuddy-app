import { useEffect } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer, useNavigationContainerRef } from '@react-navigation/native';
import { PaperProvider, Snackbar } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import * as SplashScreen from 'expo-splash-screen';

import { paperTheme } from '@/core/theme/paper';
import RootNavigator from '@/navigation/RootNavigator';
import { useAuthStore } from '@/store/authStore';
import { useDashboardStore } from '@/store/dashboardStore';
import { useUIStore } from '@/store/uiStore';
import { clearDashboardCache } from '@/utils/dashboardCache';
import { markSplashHidden, startupMark } from '@/utils/startupPerf';

SplashScreen.preventAutoHideAsync();

function hideNativeSplash(source: string) {
  if (!markSplashHidden(source)) return;
  void SplashScreen.hideAsync();
}

function AppContent() {
  const navigationRef = useNavigationContainerRef();
  const { snackbar, hideSnackbar } = useUIStore();
  const initialize = useAuthStore((s) => s.initialize);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isInitialized = useAuthStore((s) => s.isInitialized);

  useEffect(() => {
    startupMark('AppContent mounted');
    startupMark('FIRST SCREEN RENDER');
    void initialize();
    // Last-resort only. Primary hide is NavigationContainer onReady after auth is known.
    const failsafe = setTimeout(() => hideNativeSplash('failsafe-8s'), 8000);
    return () => clearTimeout(failsafe);
  }, [initialize]);

  useEffect(() => {
    if (!isInitialized || isAuthenticated) return;
    useDashboardStore.getState().reset();
    void clearDashboardCache();
    if (!navigationRef.isReady()) return;
    const route = navigationRef.getCurrentRoute()?.name;
    if (!route || route === 'Splash' || route === 'Login' || route === 'Signup') return;
    navigationRef.reset({
      index: 0,
      routes: [{ name: 'Auth', params: { screen: 'Login' } }],
    });
  }, [isAuthenticated, isInitialized, navigationRef]);

  if (!isInitialized) {
    // Native splash stays up until Login/Home is ready. This tree is only
    // visible if the 8s failsafe hid the splash while SecureStore is still slow.
    return (
      <View style={styles.boot}>
        <ActivityIndicator size="large" color="#4A90D9" />
      </View>
    );
  }

  return (
    <>
      <StatusBar style="dark" />
      <NavigationContainer
        ref={navigationRef}
        onReady={() => {
          startupMark('NAVIGATION READY');
          hideNativeSplash('navigation-ready');
        }}
      >
        <RootNavigator />
      </NavigationContainer>
      <Snackbar
        visible={snackbar.visible}
        onDismiss={hideSnackbar}
        duration={3000}
        style={{
          backgroundColor:
            snackbar.type === 'error'
              ? '#EF4444'
              : snackbar.type === 'success'
                ? '#22C55E'
                : '#4A90D9',
        }}
      >
        {snackbar.message}
      </Snackbar>
    </>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <PaperProvider theme={paperTheme}>
        <AppContent />
      </PaperProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  boot: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
