/**
 * localStorage cache with 1-hour TTL and stale-while-revalidate support.
 * Mirrors the backend's _CACHE_TTL_SECONDS and _CACHE_REFRESH_THRESHOLD.
 * All functions are SSR-safe (no-op when window is undefined).
 */

const TTL_MS = 60 * 60 * 1000;       // 1 hour — matches backend cache TTL
const REFRESH_THRESHOLD = 0.80;       // background-refresh at 80% of TTL (48 min)

interface CacheEntry<T> {
  data: T;
  ts: number;
}

export function getCached<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const entry: CacheEntry<T> = JSON.parse(raw);
    if (Date.now() - entry.ts > TTL_MS) {
      localStorage.removeItem(key);
      return null;
    }
    return entry.data;
  } catch {
    return null;
  }
}

export function setCached<T>(key: string, data: T): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, JSON.stringify({ data, ts: Date.now() } satisfies CacheEntry<T>));
  } catch {
    // localStorage full or disabled — fail silently
  }
}

/** True when cached entry is older than 80% of TTL — time to background-refresh. */
export function isStale(key: string): boolean {
  if (typeof window === "undefined") return true;
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return true;
    const entry: CacheEntry<unknown> = JSON.parse(raw);
    return Date.now() - entry.ts > TTL_MS * REFRESH_THRESHOLD;
  } catch {
    return true;
  }
}
