@echo off
setlocal
cd /d "%~dp0"

if "%EXPO_PUBLIC_API_URL%"=="" set EXPO_PUBLIC_API_URL=https://exambuddy-app.onrender.com/api/v1
if "%APK_OUTPUT_NAME%"=="" set APK_OUTPUT_NAME=SmartStudy-production.apk

set GRADLE_USER_HOME=D:\gradle
set TEMP=D:\gradle\tmp
set TMP=D:\gradle\tmp

if not exist "%GRADLE_USER_HOME%" mkdir "%GRADLE_USER_HOME%"
if not exist "%TEMP%" mkdir "%TEMP%"

echo.
echo SmartStudy public APK build
echo API URL=%EXPO_PUBLIC_API_URL%
echo Output=%APK_OUTPUT_NAME%
echo.

node scripts\build-apk-public.js
if errorlevel 1 exit /b 1

echo.
echo Done. Share: dist\%APK_OUTPUT_NAME%
pause
