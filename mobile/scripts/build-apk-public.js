#!/usr/bin/env node
/**
 * Build APK pointing at a public HTTPS API (Render, Railway, etc.).
 * Uses EXPO_PUBLIC_API_URL or defaults to the Render deployment.
 */
const DEFAULT_API_URL = 'https://exambuddy-app.onrender.com/api/v1';
const DEFAULT_APK_NAME = 'SmartStudy-production.apk';

if (!process.env.EXPO_PUBLIC_API_URL?.trim()) {
  process.env.EXPO_PUBLIC_API_URL = DEFAULT_API_URL;
}

process.env.EXPO_PUBLIC_API_FORCE = 'true';
process.env.APK_OUTPUT_NAME = process.env.APK_OUTPUT_NAME || DEFAULT_APK_NAME;

require('./build-apk-local.js');
