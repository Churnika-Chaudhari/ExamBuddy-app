# SmartStudy Mobile

React Native Expo frontend for the SmartStudy AI exam preparation platform.

## Tech Stack

- **Expo** ~52
- **TypeScript**
- **React Navigation** (Stack + Bottom Tabs)
- **Zustand** (state management)
- **React Native Paper** (UI components)
- **Axios** (API client with JWT refresh)

## Folder Structure

```
mobile/
├── App.tsx                          # Root app + providers
├── index.ts                         # Entry point
├── src/
│   ├── core/
│   │   ├── config/env.ts            # API URL config
│   │   └── theme/                   # Colors, typography, Paper theme
│   ├── domain/types/                # TypeScript interfaces
│   ├── data/api/
│   │   ├── client.ts                # Axios + JWT interceptor
│   │   └── endpoints.ts             # API service functions
│   ├── store/                       # Zustand stores
│   ├── navigation/                  # React Navigation setup
│   └── presentation/
│       ├── components/              # Reusable UI components
│       └── screens/                 # All app screens
```

## Screens

| Screen | File | Description |
|--------|------|-------------|
| Splash | `SplashScreen.tsx` | App launch + auth check |
| Login | `LoginScreen.tsx` | User login |
| Signup | `SignupScreen.tsx` | User registration |
| Dashboard | `DashboardScreen.tsx` | Stats, quick actions, activity |
| Upload PYQ | `UploadPYQScreen.tsx` | PDF upload + AI analysis |
| Analysis Result | `AnalysisResultScreen.tsx` | Topics, repeated Qs, patterns |
| Notes | `NotesScreen.tsx` | Notes list |
| Note Detail | `NoteDetailScreen.tsx` | Single note view |
| Quiz | `QuizScreen.tsx` | Quiz list + generate |
| Quiz Play | `QuizPlayScreen.tsx` | Take quiz |
| Quiz Result | `QuizResultScreen.tsx` | Score + answer review |
| Profile | `ProfileScreen.tsx` | User profile + logout |

## Setup

```bash
cd mobile
npm install
copy .env.example .env
# Set EXPO_PUBLIC_API_URL to your backend URL
# For Android emulator use: http://10.0.2.2:8000/api/v1
# For physical device use your machine's LAN IP

npx expo start
```

## Design

- White background (`#FFFFFF`)
- Soft blue accents (`#4A90D9`)
- Card-based UI with subtle shadows
- Student-friendly minimal layout
