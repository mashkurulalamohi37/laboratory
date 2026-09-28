import createClient from "openapi-fetch";

import { ApiError, networkError, toApiError } from "./errors";
import type { paths } from "./schema";
import { session } from "./session";

export interface ApiClientOptions {
  /** Origin of the API. Empty string = same origin (dev proxy / gateway). */
  baseUrl?: string;
  /** Called once when the session cannot be refreshed (sign-in required). */
  onSessionExpired?: () => void;
  fetchImpl?: typeof fetch;
}

const REFRESH_PATH = "/api/v1/auth/refresh";
/** Codes after which a silent refresh + single retry is worthwhile. */
const RETRYABLE_AUTH_CODES = new Set(["TOKEN_EXPIRED"]);

interface TokenPayload {
  access_token: string;
  expires_at: string;
}

export function createApiClient(options: ApiClientOptions = {}) {
  const baseUrl = options.baseUrl ?? "";
  const rawFetch = options.fetchImpl ?? globalThis.fetch.bind(globalThis);
  let inflightRefresh: Promise<boolean> | null = null;

  /** Rotate the refresh cookie. Concurrent callers share one request (single-flight). */
  function refreshSession(): Promise<boolean> {
    inflightRefresh ??= (async () => {
      try {
        const res = await rawFetch(`${baseUrl}${REFRESH_PATH}`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        });
        if (!res.ok) {
          session.clear();
          return false;
        }
        const body = (await res.json()) as { data: TokenPayload };
        session.set(body.data.access_token, body.data.expires_at);
        return true;
      } catch {
        return false; // network failure: keep current state, caller surfaces the error
      } finally {
        inflightRefresh = null;
      }
    })();
    return inflightRefresh;
  }

  function withAuth(request: Request): Request {
    const token = session.get();
    const headers = new Headers(request.headers);
    if (token) headers.set("Authorization", `Bearer ${token.token}`);
    return new Request(request, { headers });
  }

  async function authFetch(input: Request): Promise<Response> {
    const isAuthEndpoint = new URL(input.url, "http://x").pathname.startsWith("/api/v1/auth/");
    const retryCopy = input.clone();
    if (!isAuthEndpoint && session.get() && session.isStale()) await refreshSession();

    let response: Response;
    try {
      response = await rawFetch(withAuth(input));
    } catch (cause) {
      throw networkError(cause);
    }
    if (response.status !== 401 || isAuthEndpoint || !session.get()) return response;

    const body = (await response.clone().json().catch(() => null)) as {
      error?: { code?: string };
    } | null;
    const code = body?.error?.code ?? "";
    if (RETRYABLE_AUTH_CODES.has(code) && (await refreshSession())) {
      try {
        return await rawFetch(withAuth(retryCopy));
      } catch (cause) {
        throw networkError(cause);
      }
    }
    session.clear();
    options.onSessionExpired?.();
    return response;
  }

  const client = createClient<paths>({
    baseUrl,
    credentials: "include",
    fetch: authFetch,
  });

  return { client, refreshSession };
}

export type ApiClient = ReturnType<typeof createApiClient>["client"];

interface FetchResult<TData> {
  data?: TData;
  error?: unknown;
  response: Response;
}

/**
 * Unwrap the `{success, data, meta}` envelope or throw an `ApiError`.
 *
 *   const me = await unwrap(api.GET("/api/v1/me"));
 */
export async function unwrap<TData extends { data: unknown }>(
  call: Promise<FetchResult<TData>>,
): Promise<TData["data"]> {
  const { data, error, response } = await call;
  if (error !== undefined || !response.ok) throw toApiError(response, error);
  if (data === undefined) return undefined as TData["data"];
  return data.data;
}

/** Like `unwrap` but keeps `meta` (pagination). */
export async function unwrapWithMeta<TData extends { data: unknown; meta?: unknown }>(
  call: Promise<FetchResult<TData>>,
): Promise<{ data: TData["data"]; meta: NonNullable<TData["meta"]> }> {
  const { data, error, response } = await call;
  if (error !== undefined || !response.ok || data === undefined) {
    throw toApiError(response, error);
  }
  return { data: data.data, meta: data.meta as NonNullable<TData["meta"]> };
}

/** For endpoints that return 204 No Content. */
export async function expectNoContent(call: Promise<FetchResult<unknown>>): Promise<void> {
  const { error, response } = await call;
  if (error !== undefined || !response.ok) throw toApiError(response, error);
}

export { ApiError };
