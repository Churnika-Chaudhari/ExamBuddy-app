@echo off
setlocal
cd /d "%~dp0"

if "%EXPO_PUBLIC_API_URL%"=="" (
  echo.
  echo ERROR: Set your public API URL first, for example:
  echo   set EXPO_PUBLIC_API_URL=https://smartstudy-api.onrender.com/api/v1
  echo   build-apk.bat
  echo.
  exit /b 1
)

set GRADLE_USER_HOME=D:\gradle
set TEMP=D:\gradle\tmp
set TMP=D:\gradle\tmp

if not exist "%GRADLE_USER_HOME%" mkdir "%GRADLE_USER_HOME%"
if not exist "%TEMP%" mkdir "%TEMP%"

echo.
echo SmartStudy public APK build
echo API URL=%EXPO_PUBLIC_API_URL%
echo.

node scripts\build-apk-local.js
if errorlevel 1 exit /b 1

echo.
echo Done. Share: dist\SmartStudy.apk
pause
