import { createNativeStackNavigator } from '@react-navigation/native-stack';

import type { AuthStackParamList } from '@/navigation/types';
import LoginScreen from '@/presentation/screens/LoginScreen';
import SignupScreen from '@/presentation/screens/SignupScreen';

const Stack = createNativeStackNavigator<AuthStackParamList>();

export default function AuthNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="Signup" component={SignupScreen} />
    </Stack.Navigator>
  );
}
