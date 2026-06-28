#!/usr/bin/env node
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const mobileDir = path.join(__dirname, '..');
const sdk = path.join(process.env.LOCALAPPDATA || '', 'Android', 'Sdk');
const gradleHome = process.env.GRADLE_USER_HOME || 'D:\\gradle';
const tmpDir = process.env.TEMP || path.join(mobileDir, '.tmp');
const apiUrl = process.env.EXPO_PUBLIC_API_URL || 'http://10.167.199.44:8000/api/v1';

fs.mkdirSync(gradleHome, { recursive: true });
fs.mkdirSync(tmpDir, { recursive: true });

if (!fs.existsSync(sdk)) {
  console.error('Android SDK not found at', sdk);
  console.error('Install Android Studio or use: npm run build:apk (EAS cloud build)');
  process.exit(1);
}

const env = {
  ...process.env,
  ANDROID_HOME: sdk,
  ANDROID_SDK_ROOT: sdk,
  GRADLE_USER_HOME: gradleHome,
  TEMP: tmpDir,
  TMP: tmpDir,
  EXPO_PUBLIC_API_URL: apiUrl,
};

console.log('\nSmartStudy local APK build');
console.log('ANDROID_HOME:', sdk);
console.log('GRADLE_USER_HOME:', gradleHome);
console.log('TEMP/TMP:', tmpDir);
console.log('API URL:', apiUrl);
console.log('');

function run(cmd, args, cwd) {
  const result = spawnSync(cmd, args, { cwd, stdio: 'inherit', shell: true, env });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

console.log('Step 1/2: Generating native Android project (expo prebuild)...');
if (!fs.existsSync(path.join(mobileDir, 'android'))) {
  run('npx', ['expo', 'prebuild', '--platform', 'android', '--no-install'], mobileDir);
} else {
  console.log('Android folder exists — skipping prebuild');
}

const gradleProps = path.join(mobileDir, 'android', 'gradle.properties');
if (fs.existsSync(gradleProps)) {
  let props = fs.readFileSync(gradleProps, 'utf8');
  if (!props.includes('android.overridePathCheck')) {
    props += '\nandroid.overridePathCheck=true\n';
    fs.writeFileSync(gradleProps, props);
  }
}

console.log('\nStep 2/2: Compiling APK (Gradle)...');
const androidDir = path.join(mobileDir, 'android');

// Stale .cxx caches embed old Gradle paths (e.g. Cursor sandbox) and break ninja on Windows.
function removeDir(dir) {
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}
for (const dir of [
  path.join(mobileDir, 'node_modules', 'expo-modules-core', 'android', '.cxx'),
  path.join(mobileDir, 'node_modules', 'react-native-screens', 'android', '.cxx'),
  path.join(androidDir, 'app', 'build'),
  path.join(androidDir, 'app', '.cxx'),
  path.join(androidDir, 'build'),
  path.join(androidDir, '.gradle'),
]) {
  if (fs.existsSync(dir)) {
    console.log('Cleaning', path.relative(mobileDir, dir));
    removeDir(dir);
  }
}

run('gradlew.bat', ['--stop'], androidDir);
run(
  'gradlew.bat',
  [
    '-g',
    gradleHome,
    'clean',
    'assembleDebug',
    '-x',
    'lint',
    '-x',
    'test',
    '-PreactNativeArchitectures=arm64-v8a',
  ],
  androidDir
);

const apkPath = path.join(androidDir, 'app', 'build', 'outputs', 'apk', 'debug', 'app-debug.apk');
const shareDir = path.join(mobileDir, 'dist');
const apkOutputName = process.env.APK_OUTPUT_NAME || 'SmartStudy.apk';
const shareApk = path.join(shareDir, apkOutputName);

if (!fs.existsSync(apkPath)) {
  console.error('Build finished but APK not found at', apkPath);
  process.exit(1);
}

fs.mkdirSync(shareDir, { recursive: true });
fs.copyFileSync(apkPath, shareApk);

console.log('\n========================================');
console.log('APK built successfully!');
console.log('Share this file with your friend:');
console.log(shareApk);
console.log('========================================\n');
