#!/usr/bin/env node
/**
 * Build a release APK against the configured public HTTPS API.
 * Set EXPO_PUBLIC_API_URL before running. The backend URL is not hardcoded here.
 */
const apiUrl = process.env.EXPO_PUBLIC_API_URL?.trim();
if (!apiUrl || !/^https:\/\//i.test(apiUrl)) {
  console.error(
    'Set EXPO_PUBLIC_API_URL to your HTTPS backend before building, for example https://YOUR-RENDER-BACKEND.onrender.com/api/v1'
  );
  process.exit(1);
}

process.env.EXPO_PUBLIC_API_FORCE = 'true';
process.env.APK_OUTPUT_NAME = process.env.APK_OUTPUT_NAME || 'SmartStudy-production.apk';
process.env.APK_BUILD_VARIANT = 'release';
process.env.EXPO_PREBUILD = '1';

require('./build-apk-local.js');
