import { Platform } from 'react-native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';

import { colors } from '@/core/theme';
import { fontScale, moderateScale } from '@/core/theme/responsive';
import type { MainTabParamList } from '@/navigation/types';
import AppTabBar from '@/presentation/components/AppTabBar';
import DashboardScreen from '@/presentation/screens/DashboardScreen';

const Tab = createBottomTabNavigator<MainTabParamList>();

const TAB_ICONS: Record<
  keyof MainTabParamList,
  { active: keyof typeof Ionicons.glyphMap; inactive: keyof typeof Ionicons.glyphMap }
> = {
  Dashboard: { active: 'home', inactive: 'home-outline' },
  Notes: { active: 'document-text', inactive: 'document-text-outline' },
  Quiz: { active: 'help-circle', inactive: 'help-circle-outline' },
  Profile: { active: 'person', inactive: 'person-outline' },
};

const TAB_LABELS: Record<keyof MainTabParamList, string> = {
  Dashboard: 'Home',
  Notes: 'Notes',
  Quiz: 'Quiz',
  Profile: 'Profile',
};

export default function MainTabNavigator() {
  return (
    <Tab.Navigator
      tabBar={(props) => <AppTabBar {...props} />}
      screenOptions={({ route }) => {
        const tabName = route.name as keyof MainTabParamList;
        const icons = TAB_ICONS[tabName];

        return {
          headerShown: false,
          tabBarShowLabel: true,
          tabBarHideOnKeyboard: true,
          tabBarActiveTintColor: colors.primary,
          tabBarInactiveTintColor: colors.textMuted,
          tabBarLabel: TAB_LABELS[tabName],
          tabBarStyle: {
            backgroundColor: colors.white,
            height: Platform.OS === 'ios' ? 52 : 58,
            paddingTop: moderateScale(6),
            paddingBottom: Platform.OS === 'ios' ? moderateScale(4) : moderateScale(6),
          },
          tabBarItemStyle: {
            minHeight: moderateScale(44),
          },
          tabBarLabelStyle: {
            fontSize: fontScale(12),
            fontWeight: '600',
            marginTop: moderateScale(2),
          },
          tabBarIcon: ({ color, focused }) => (
            <Ionicons
              name={focused ? icons.active : icons.inactive}
              size={moderateScale(24)}
              color={color}
            />
          ),
          sceneContainerStyle: {
            backgroundColor: colors.background,
          },
        };
      }}
    >
      <Tab.Screen name="Dashboard" component={DashboardScreen} />
      <Tab.Screen
        name="Notes"
        getComponent={() => require('@/presentation/screens/NotesScreen').default}
      />
      <Tab.Screen
        name="Quiz"
        getComponent={() => require('@/presentation/screens/QuizScreen').default}
      />
      <Tab.Screen
        name="Profile"
        getComponent={() => require('@/presentation/screens/ProfileScreen').default}
      />
    </Tab.Navigator>
  );
}
