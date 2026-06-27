#!/usr/bin/env node
/**
 * Build APK pointing at a public HTTPS API (Render, Railway, etc.).
 * Requires EXPO_PUBLIC_API_URL to be set before running.
 */
if (!process.env.EXPO_PUBLIC_API_URL?.trim()) {
  console.error('\nSet EXPO_PUBLIC_API_URL to your deployed backend, for example:');
  console.error('  PowerShell:');
  console.error('    $env:EXPO_PUBLIC_API_URL="https://smartstudy-api.onrender.com/api/v1"');
  console.error('    npm run build:apk:public');
  console.error('  CMD:');
  console.error('    set EXPO_PUBLIC_API_URL=https://smartstudy-api.onrender.com/api/v1');
  console.error('    npm run build:apk:public');
  process.exit(1);
}

require('./build-apk-local.js');
