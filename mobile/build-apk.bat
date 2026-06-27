@echo off
setlocal
cd /d "%~dp0"

set GRADLE_USER_HOME=D:\gradle
set TEMP=D:\gradle\tmp
set TMP=D:\gradle\tmp
set EXPO_PUBLIC_API_URL=http://10.167.199.44:8000/api/v1

if not exist "%GRADLE_USER_HOME%" mkdir "%GRADLE_USER_HOME%"
if not exist "%TEMP%" mkdir "%TEMP%"

echo.
echo SmartStudy APK build (run this in CMD or PowerShell, not inside Cursor)
echo GRADLE_USER_HOME=%GRADLE_USER_HOME%
echo API URL=%EXPO_PUBLIC_API_URL%
echo.

node scripts\build-apk-local.js
if errorlevel 1 exit /b 1

echo.
echo Done. APK: dist\SmartStudy.apk
pause
