/**
 * In-memory access-token store. The access token is never persisted (no localStorage), so
 * XSS cannot lift a long-lived credential; the refresh token lives in an HttpOnly cookie.
 */

export interface AccessToken {
  token: string;
  expiresAt: number; // epoch ms
}

type Listener = (token: AccessToken | null) => void;

let current: AccessToken | null = null;
const listeners = new Set<Listener>();

export const session = {
  get(): AccessToken | null {
    return current;
  },
  set(token: string, expiresAtIso: string): void {
    current = { token, expiresAt: Date.parse(expiresAtIso) };
    listeners.forEach((l) => l(current));
  },
  clear(): void {
    if (current === null) return;
    current = null;
    listeners.forEach((l) => l(null));
  },
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  /** True when the token is missing or expires within `skewMs`. */
  isStale(skewMs = 30_000): boolean {
    return current === null || current.expiresAt - Date.now() < skewMs;
  },
};
