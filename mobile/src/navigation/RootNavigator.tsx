import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { colors } from '@/core/theme';
import AuthNavigator from '@/navigation/AuthNavigator';
import MainTabNavigator from '@/navigation/MainTabNavigator';
import type { RootStackParamList } from '@/navigation/types';
import { useAuthStore } from '@/store/authStore';
import { startupMark } from '@/utils/startupPerf';

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function RootNavigator() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  startupMark('RootNavigator started');

  return (
    <Stack.Navigator
      initialRouteName={isAuthenticated ? 'Main' : 'Auth'}
      screenOptions={{
        headerStyle: { backgroundColor: colors.background },
        headerTintColor: colors.text,
        headerTitleStyle: { fontWeight: '600' },
        headerShadowVisible: false,
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      <Stack.Screen
        name="Splash"
        getComponent={() => require('@/presentation/screens/SplashScreen').default}
        options={{ headerShown: false }}
      />
      <Stack.Screen name="Auth" component={AuthNavigator} options={{ headerShown: false }} />
      <Stack.Screen name="Main" component={MainTabNavigator} options={{ headerShown: false }} />
      <Stack.Screen
        name="UploadPYQ"
        getComponent={() => require('@/presentation/screens/UploadPYQScreen').default}
        options={({ route }) => ({
          title:
            route.params?.initialCategory === 'syllabus'
              ? 'Upload Syllabus'
              : route.params?.initialCategory === 'pyq'
                ? 'Analyze PYQ'
                : 'Upload Documents',
        })}
      />
      <Stack.Screen
        name="UploadedDocuments"
        getComponent={() => require('@/presentation/screens/UploadedDocumentsScreen').default}
        options={{ title: 'Uploaded Documents' }}
      />
      <Stack.Screen
        name="DocumentViewer"
        getComponent={() => require('@/presentation/screens/DocumentViewerScreen').default}
        options={({ route }) => ({ title: route.params.title })}
      />
      <Stack.Screen
        name="AnalysisResult"
        getComponent={() => require('@/presentation/screens/AnalysisResultScreen').default}
        options={{ title: 'Analysis Result' }}
      />
      <Stack.Screen
        name="SubjectNotes"
        getComponent={() => require('@/presentation/screens/SubjectNotesScreen').default}
        options={{ title: 'Subject Notes' }}
      />
      <Stack.Screen
        name="ModuleTopics"
        getComponent={() => require('@/presentation/screens/ModuleTopicsScreen').default}
        options={{ title: 'Module Topics' }}
      />
      <Stack.Screen
        name="TopicStudyNotes"
        getComponent={() => require('@/presentation/screens/TopicStudyNotesScreen').default}
        options={{ title: 'Study Notes' }}
      />
      <Stack.Screen
        name="NoteDetail"
        getComponent={() => require('@/presentation/screens/NoteDetailScreen').default}
        options={{ title: 'Note' }}
      />
      <Stack.Screen
        name="QuizPlay"
        getComponent={() => require('@/presentation/screens/QuizPlayScreen').default}
        options={{ title: 'Take Quiz' }}
      />
      <Stack.Screen
        name="QuizResult"
        getComponent={() => require('@/presentation/screens/QuizResultScreen').default}
        options={{ title: 'Quiz Result', headerLeft: () => null }}
      />
      <Stack.Screen
        name="QuizSubjectSelect"
        getComponent={() => require('@/presentation/screens/QuizSubjectSelectScreen').default}
        options={{ title: 'Select Subject' }}
      />
      <Stack.Screen
        name="QuizConfig"
        getComponent={() => require('@/presentation/screens/QuizConfigScreen').default}
        options={{ title: 'Quiz Settings' }}
      />
      <Stack.Screen
        name="QuizHistory"
        getComponent={() => require('@/presentation/screens/QuizHistoryScreen').default}
        options={{ title: 'Quiz History' }}
      />
      <Stack.Screen
        name="QuizAnalysis"
        getComponent={() => require('@/presentation/screens/QuizAnalysisScreen').default}
        options={{ title: 'Quiz Analysis' }}
      />
      <Stack.Screen
        name="QuizAttemptReview"
        getComponent={() => require('@/presentation/screens/QuizAttemptReviewScreen').default}
        options={{ title: 'Review Attempt' }}
      />
    </Stack.Navigator>
  );
}
