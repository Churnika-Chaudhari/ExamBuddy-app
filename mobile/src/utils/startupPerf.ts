/** Temporary startup/pipeline timings. Filter Metro / logcat for `[STARTUP]`. */
const startedAt =
  typeof performance !== 'undefined' && typeof performance.now === 'function'
    ? performance.now()
    : Date.now();

let splashHiddenLogged = false;

export function nowMs(): number {
  return typeof performance !== 'undefined' && typeof performance.now === 'function'
    ? performance.now()
    : Date.now();
}

export function startupMark(label: string): void {
  // eslint-disable-next-line no-console
  console.log(`[STARTUP] ${label}: ${Math.round(nowMs() - startedAt)}ms`);
}

export function startupDuration(label: string, started: number): void {
  // eslint-disable-next-line no-console
  console.log(`[STARTUP] ${label}: ${Math.round(nowMs() - started)}ms`);
}

export function startupApiMark(label: string, started: number): void {
  // eslint-disable-next-line no-console
  console.log(
    `[STARTUP] API ${label}: ${Math.round(nowMs() - started)}ms (background, does not block splash)`
  );
}

/** Log splash hide once so failsafe vs navigation-ready don't double-count. */
export function markSplashHidden(source: string): boolean {
  if (splashHiddenLogged) {
    startupMark(`SPLASH HIDDEN skipped (${source})`);
    return false;
  }
  splashHiddenLogged = true;
  startupMark(`SPLASH HIDDEN (${source})`);
  return true;
}

startupMark('APP START');
