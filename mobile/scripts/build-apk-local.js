#!/usr/bin/env node
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const mobileDir = path.join(__dirname, '..');
const sdk = path.join(process.env.LOCALAPPDATA || '', 'Android', 'Sdk');
const gradleHome = process.env.GRADLE_USER_HOME || 'D:\\gradle';
const tmpDir = process.env.TEMP || path.join(mobileDir, '.tmp');
const apiUrl = process.env.EXPO_PUBLIC_API_URL || 'http://10.167.199.44:8000/api/v1';
const apiForce = process.env.EXPO_PUBLIC_API_FORCE === 'true';
const buildVariant = process.env.APK_BUILD_VARIANT === 'release' ? 'release' : 'debug';
const assembleTask = buildVariant === 'release' ? 'assembleRelease' : 'assembleDebug';
const envFilePath = path.join(mobileDir, '.env');

function writeBuildEnvFile() {
  const lines = [`EXPO_PUBLIC_API_URL=${apiUrl}`];
  if (apiForce) {
    lines.push('EXPO_PUBLIC_API_FORCE=true');
  }
  fs.writeFileSync(envFilePath, `${lines.join('\n')}\n`, 'utf8');
  console.log('Wrote', path.relative(mobileDir, envFilePath));
}

function cleanMetroCaches() {
  for (const dir of [
    path.join(mobileDir, '.expo'),
    path.join(mobileDir, 'node_modules', '.cache'),
  ]) {
    if (fs.existsSync(dir)) {
      console.log('Cleaning', path.relative(mobileDir, dir));
      fs.rmSync(dir, { recursive: true, force: true });
    }
  }
}

function verifyBundleApiUrl() {
  const bundlePath = path.join(
    androidDir,
    'app',
    'build',
    'generated',
    'assets',
    `createBundle${buildVariant === 'release' ? 'Release' : 'Debug'}JsAndAssets`,
    'index.android.bundle'
  );

  if (!fs.existsSync(bundlePath)) {
    console.warn('Could not verify bundle URL: bundle file missing at', bundlePath);
    return;
  }

  const bundleText = fs.readFileSync(bundlePath);
  if (!bundleText.includes(Buffer.from(apiUrl))) {
    console.error('\nBuild verification failed: JS bundle does not contain the expected API URL.');
    console.error('Expected:', apiUrl);
    process.exit(1);
  }

  console.log('Verified bundle contains API URL:', apiUrl);
}

fs.mkdirSync(gradleHome, { recursive: true });
fs.mkdirSync(tmpDir, { recursive: true });
writeBuildEnvFile();
cleanMetroCaches();

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
  NODE_ENV: buildVariant === 'release' ? 'production' : 'development',
  EXPO_PUBLIC_API_URL: apiUrl,
  EXPO_PUBLIC_API_FORCE: apiForce ? 'true' : 'false',
};

console.log('\nSmartStudy local APK build');
console.log('ANDROID_HOME:', sdk);
console.log('GRADLE_USER_HOME:', gradleHome);
console.log('TEMP/TMP:', tmpDir);
console.log('API URL:', apiUrl);
console.log('Build variant:', buildVariant);
console.log('');

function run(cmd, args, cwd) {
  const result = spawnSync(cmd, args, { cwd, stdio: 'inherit', shell: true, env });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

console.log('Step 1/2: Generating native Android project (expo prebuild)...');
const shouldPrebuild = process.env.EXPO_PREBUILD === '1' || !fs.existsSync(path.join(mobileDir, 'android'));
if (shouldPrebuild) {
  const prebuildArgs = ['expo', 'prebuild', '--platform', 'android', '--no-install'];
  if (process.env.EXPO_PREBUILD === '1') {
    prebuildArgs.push('--clean');
  }
  run('npx', prebuildArgs, mobileDir);
} else {
  console.log('Android folder exists — skipping prebuild (set EXPO_PREBUILD=1 to refresh native assets)');
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

// Stop daemons first so .gradle locks are released before cleanup.
if (fs.existsSync(path.join(androidDir, 'gradlew.bat'))) {
  run('gradlew.bat', ['--stop'], androidDir);
}

// Stale .cxx caches embed old Gradle paths (e.g. Cursor sandbox) and break ninja on Windows.
function removeDir(dir) {
  if (!fs.existsSync(dir)) return;
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch (err) {
    if (err && err.code === 'EBUSY') {
      console.warn('Skipping locked directory:', path.relative(mobileDir, dir));
      return;
    }
    throw err;
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

run(
  'gradlew.bat',
  [
    '-g',
    gradleHome,
    'clean',
    assembleTask,
    '-x',
    'lint',
    '-x',
    'test',
    '-PreactNativeArchitectures=arm64-v8a',
  ],
  androidDir
);

const apkPath = path.join(
  androidDir,
  'app',
  'build',
  'outputs',
  'apk',
  buildVariant,
  buildVariant === 'release' ? 'app-release.apk' : 'app-debug.apk'
);
const shareDir = path.join(mobileDir, 'dist');
const apkOutputName = process.env.APK_OUTPUT_NAME || 'SmartStudy.apk';
const shareApk = path.join(shareDir, apkOutputName);

if (!fs.existsSync(apkPath)) {
  console.error('Build finished but APK not found at', apkPath);
  process.exit(1);
}

fs.mkdirSync(shareDir, { recursive: true });
fs.copyFileSync(apkPath, shareApk);
verifyBundleApiUrl();

console.log('\n========================================');
console.log('APK built successfully!');
console.log('Share this file with your friend:');
console.log(shareApk);
console.log('========================================\n');
