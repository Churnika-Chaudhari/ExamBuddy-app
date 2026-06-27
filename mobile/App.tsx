import { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { PaperProvider, Snackbar } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import * as SplashScreen from 'expo-splash-screen';

import { paperTheme } from '@/core/theme/paper';
import RootNavigator from '@/navigation/RootNavigator';
import { useUIStore } from '@/store/uiStore';

SplashScreen.preventAutoHideAsync();

function AppContent() {
  const { snackbar, hideSnackbar } = useUIStore();

  useEffect(() => {
    SplashScreen.hideAsync();
  }, []);

  return (
    <>
      <StatusBar style="dark" />
      <NavigationContainer>
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
