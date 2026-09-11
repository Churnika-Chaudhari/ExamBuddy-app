const startedAt = Date.now();

/** Temporary startup timings. Filter logcat / Metro for `[STARTUP]`. */
export function startupMark(label: string): void {
  // eslint-disable-next-line no-console
  console.log(`[STARTUP] ${label}: ${Date.now() - startedAt}ms`);
}

export function startupApiMark(label: string, started: number): void {
  // eslint-disable-next-line no-console
  console.log(`[STARTUP] API ${label}: ${Date.now() - started}ms (background, does not block splash)`);
}

startupMark('APP START');
