import { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer, useNavigationContainerRef } from '@react-navigation/native';
import { PaperProvider, Snackbar } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import * as SplashScreen from 'expo-splash-screen';

import { paperTheme } from '@/core/theme/paper';
import RootNavigator from '@/navigation/RootNavigator';
import { useAuthStore } from '@/store/authStore';
import { useUIStore } from '@/store/uiStore';
import { startupMark } from '@/utils/startupPerf';

SplashScreen.preventAutoHideAsync();

function AppContent() {
  const navigationRef = useNavigationContainerRef();
  const { snackbar, hideSnackbar } = useUIStore();
  const initialize = useAuthStore((s) => s.initialize);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isInitialized = useAuthStore((s) => s.isInitialized);

  useEffect(() => {
    startupMark('AppContent mounted');
    void initialize();
    const failsafe = setTimeout(() => {
      void SplashScreen.hideAsync().then(() => startupMark('SPLASH HIDDEN (failsafe)'));
    }, 3000);
    return () => clearTimeout(failsafe);
  }, [initialize]);

  useEffect(() => {
    if (!isInitialized || isAuthenticated || !navigationRef.isReady()) return;
    const route = navigationRef.getCurrentRoute()?.name;
    if (!route || route === 'Splash' || route === 'Login' || route === 'Signup') return;
    navigationRef.reset({
      index: 0,
      routes: [{ name: 'Auth', params: { screen: 'Login' } }],
    });
  }, [isAuthenticated, isInitialized, navigationRef]);

  if (!isInitialized) {
    // Keep the native splash up until the local token has been read.
    return null;
  }

  return (
    <>
      <StatusBar style="dark" />
      <NavigationContainer
        ref={navigationRef}
        onReady={() => {
          startupMark('NAVIGATION READY');
          void SplashScreen.hideAsync().then(() => startupMark('SPLASH HIDDEN'));
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
