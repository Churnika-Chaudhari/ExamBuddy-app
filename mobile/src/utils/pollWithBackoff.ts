export class PollTimeoutError extends Error {
  constructor(message = 'Processing is taking longer than expected. Please retry.') {
    super(message);
    this.name = 'PollTimeoutError';
  }
}

const DEFAULT_INTERVALS_MS = [2000, 3000, 5000, 8000];

export async function pollWithBackoff<T>(options: {
  fn: () => Promise<T>;
  isDone: (value: T) => boolean;
  intervalsMs?: number[];
  maxAttempts?: number;
  timeoutMs?: number;
  onAttempt?: (attempt: number, value: T) => void;
}): Promise<T> {
  const intervals = options.intervalsMs?.length ? options.intervalsMs : DEFAULT_INTERVALS_MS;
  const maxAttempts = options.maxAttempts ?? 40;
  const timeoutMs = options.timeoutMs ?? 180_000;
  const started = Date.now();
  let last: T | undefined;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    if (Date.now() - started > timeoutMs) {
      throw new PollTimeoutError();
    }

    last = await options.fn();
    options.onAttempt?.(attempt, last);
    if (options.isDone(last)) {
      return last;
    }

    const wait = intervals[Math.min(attempt - 1, intervals.length - 1)];
    await new Promise((resolve) => setTimeout(resolve, wait));
  }

  throw new PollTimeoutError();
}
