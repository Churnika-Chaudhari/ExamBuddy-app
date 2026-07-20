import Constants, { ExecutionEnvironment } from 'expo-constants';
import { Platform } from 'react-native';

export type RuntimePlatform =
  | 'web'
  | 'android-emulator'
  | 'android-device'
  | 'ios-simulator'
  | 'ios-device'
  | 'expo-go'
  | 'unknown';

const API_PORT = 8000;
const API_PATH = '/api/v1';

function extractHost(value: string | undefined): string | null {
  if (!value) return null;
  const cleaned = value.replace(/^[\w+]+:\/\//, '');
  const host = cleaned.split(':')[0]?.split('/')[0];
  if (!host || host === 'localhost' || host.startsWith('127.')) return null;
  return host;
}

/** IP/host of the dev machine from the active Metro / Expo Go connection. */
function getMetroDevHost(): string | null {
  const expoGo = Constants.expoGoConfig as { debuggerHost?: string } | undefined;
  if (expoGo?.debuggerHost) {
    return expoGo.debuggerHost.split(':')[0] ?? null;
  }

  const hostUri =
    Constants.expoConfig?.hostUri ??
    (Constants as { manifest2?: { extra?: { expoClient?: { hostUri?: string } } } }).manifest2
      ?.extra?.expoClient?.hostUri;

  const fromHostUri = extractHost(hostUri);
  if (fromHostUri) return fromHostUri;

  const fromLinking = extractHost(Constants.linkingUri);
  if (fromLinking) return fromLinking;

  return null;
}

function isAndroidEmulator(): boolean {
  if (Platform.OS !== 'android') return false;
  const name = (Constants.deviceName ?? '').toLowerCase();
  return (
    name.includes('emulator') ||
    name.includes('sdk_gphone') ||
    name.includes('generic') ||
    name.includes('virtual')
  );
}

function isIosSimulator(): boolean {
  if (Platform.OS !== 'ios') return false;
  const name = (Constants.deviceName ?? '').toLowerCase();
  return name.includes('simulator') || name.includes('iphone simulator');
}

export function detectRuntimePlatform(): RuntimePlatform {
  if (Platform.OS === 'web') return 'web';

  const inExpoGo = Constants.executionEnvironment === ExecutionEnvironment.StoreClient;
  if (inExpoGo) return 'expo-go';

  if (Platform.OS === 'android') {
    return isAndroidEmulator() ? 'android-emulator' : 'android-device';
  }

  if (Platform.OS === 'ios') {
    return isIosSimulator() ? 'ios-simulator' : 'ios-device';
  }

  return 'unknown';
}

function buildApiUrl(host: string): string {
  return `http://${host}:${API_PORT}${API_PATH}`;
}

function getConfiguredApiUrl(): string | undefined {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (fromEnv) return fromEnv;

  const fromExtra = Constants.expoConfig?.extra?.apiUrl;
  if (typeof fromExtra === 'string' && fromExtra.trim()) {
    return fromExtra.trim();
  }

  return undefined;
}

function isApiUrlForced(): boolean {
  if (process.env.EXPO_PUBLIC_API_FORCE === 'true') return true;
  return Constants.expoConfig?.extra?.apiForce === true;
}

function resolveApiUrl(): string {
  const configured = getConfiguredApiUrl();
  const forceConfigured = isApiUrlForced();
  const runtime = detectRuntimePlatform();

  if (forceConfigured && configured) {
    return configured;
  }

  if (runtime === 'web') {
    return configured?.includes('localhost') || configured?.includes('127.0.0.1')
      ? configured
      : buildApiUrl('localhost');
  }

  if (runtime === 'android-emulator') {
    return buildApiUrl('10.0.2.2');
  }

  if (runtime === 'ios-simulator') {
    return buildApiUrl('localhost');
  }

  const metroHost = getMetroDevHost();
  if (__DEV__ && metroHost) {
    return buildApiUrl(metroHost);
  }

  // Standalone APK / production: use full URL baked in at build time
  if (configured && /^https?:\/\//i.test(configured)) {
    return configured;
  }

  if (configured && (configured.includes('localhost') || configured.includes('127.0.0.1'))) {
    return configured;
  }

  return buildApiUrl('localhost');
}

function resolveHealthUrl(apiUrl: string): string {
  const base = apiUrl.replace(/\/api\/v1\/?$/, '');
  return `${base}/health`;
}

const runtimePlatform = detectRuntimePlatform();
const apiUrl = resolveApiUrl();

export const ENV = {
  API_URL: apiUrl,
  HEALTH_URL: resolveHealthUrl(apiUrl),
  API_PORT,
  RUNTIME_PLATFORM: runtimePlatform,
  METRO_HOST: getMetroDevHost(),
};

/** True when the app targets a deployed HTTPS API (e.g. Render), not local dev. */
export function isRemoteProductionApi(): boolean {
  return /^https:\/\//i.test(ENV.API_URL) && !/localhost|127\.0\.0\.1/i.test(ENV.API_URL);
}

export function getHealthCheckTimeoutMs(): number {
  return isRemoteProductionApi() ? 45000 : 8000;
}

export function getHealthCheckAttempts(): number {
  return isRemoteProductionApi() ? 3 : 1;
}

if (__DEV__) {
  // eslint-disable-next-line no-console
  console.log('[SmartStudy] Runtime:', ENV.RUNTIME_PLATFORM);
  // eslint-disable-next-line no-console
  console.log('[SmartStudy] Metro host:', ENV.METRO_HOST ?? '(none)');
  // eslint-disable-next-line no-console
  console.log('[SmartStudy] API URL:', ENV.API_URL);
  // eslint-disable-next-line no-console
  console.log('[SmartStudy] Health URL:', ENV.HEALTH_URL);
}
