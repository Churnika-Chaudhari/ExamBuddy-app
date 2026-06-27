import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { colors } from '@/core/theme';
import AuthNavigator from '@/navigation/AuthNavigator';
import MainTabNavigator from '@/navigation/MainTabNavigator';
import type { RootStackParamList } from '@/navigation/types';
import AnalysisResultScreen from '@/presentation/screens/AnalysisResultScreen';
import NoteDetailScreen from '@/presentation/screens/NoteDetailScreen';
import QuizPlayScreen from '@/presentation/screens/QuizPlayScreen';
import QuizResultScreen from '@/presentation/screens/QuizResultScreen';
import QuizSubjectSelectScreen from '@/presentation/screens/QuizSubjectSelectScreen';
import QuizConfigScreen from '@/presentation/screens/QuizConfigScreen';
import QuizHistoryScreen from '@/presentation/screens/QuizHistoryScreen';
import QuizAnalysisScreen from '@/presentation/screens/QuizAnalysisScreen';
import QuizAttemptReviewScreen from '@/presentation/screens/QuizAttemptReviewScreen';
import SplashScreen from '@/presentation/screens/SplashScreen';
import SubjectNotesScreen from '@/presentation/screens/SubjectNotesScreen';
import TopicStudyNotesScreen from '@/presentation/screens/TopicStudyNotesScreen';
import UploadPYQScreen from '@/presentation/screens/UploadPYQScreen';
import UploadedDocumentsScreen from '@/presentation/screens/UploadedDocumentsScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function RootNavigator() {
  return (
    <Stack.Navigator
      initialRouteName="Splash"
      screenOptions={{
        headerStyle: { backgroundColor: colors.background },
        headerTintColor: colors.text,
        headerTitleStyle: { fontWeight: '600' },
        headerShadowVisible: false,
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      <Stack.Screen name="Splash" component={SplashScreen} options={{ headerShown: false }} />
      <Stack.Screen name="Auth" component={AuthNavigator} options={{ headerShown: false }} />
      <Stack.Screen name="Main" component={MainTabNavigator} options={{ headerShown: false }} />
      <Stack.Screen
        name="UploadPYQ"
        component={UploadPYQScreen}
        options={{ title: 'Upload PYQ' }}
      />
      <Stack.Screen
        name="UploadedDocuments"
        component={UploadedDocumentsScreen}
        options={{ title: 'Uploaded Documents' }}
      />
      <Stack.Screen
        name="AnalysisResult"
        component={AnalysisResultScreen}
        options={{ title: 'Analysis Result' }}
      />
      <Stack.Screen
        name="SubjectNotes"
        component={SubjectNotesScreen}
        options={{ title: 'Subject Notes' }}
      />
      <Stack.Screen
        name="TopicStudyNotes"
        component={TopicStudyNotesScreen}
        options={{ title: 'Study Notes' }}
      />
      <Stack.Screen
        name="NoteDetail"
        component={NoteDetailScreen}
        options={{ title: 'Note' }}
      />
      <Stack.Screen
        name="QuizPlay"
        component={QuizPlayScreen}
        options={{ title: 'Take Quiz' }}
      />
      <Stack.Screen
        name="QuizResult"
        component={QuizResultScreen}
        options={{ title: 'Quiz Result', headerLeft: () => null }}
      />
      <Stack.Screen
        name="QuizSubjectSelect"
        component={QuizSubjectSelectScreen}
        options={{ title: 'Select Subject' }}
      />
      <Stack.Screen
        name="QuizConfig"
        component={QuizConfigScreen}
        options={{ title: 'Quiz Settings' }}
      />
      <Stack.Screen
        name="QuizHistory"
        component={QuizHistoryScreen}
        options={{ title: 'Quiz History' }}
      />
      <Stack.Screen
        name="QuizAnalysis"
        component={QuizAnalysisScreen}
        options={{ title: 'Quiz Analysis' }}
      />
      <Stack.Screen
        name="QuizAttemptReview"
        component={QuizAttemptReviewScreen}
        options={{ title: 'Review Attempt' }}
      />
    </Stack.Navigator>
  );
}
