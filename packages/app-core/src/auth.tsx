import {
  ApiError,
  createApiClient,
  expectNoContent,
  session,
  unwrap,
  type ApiClient,
  type Me,
} from "@nirnoy/api-client";
import { setLocale } from "@nirnoy/i18n";
import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

export type AuthStatus = "restoring" | "authenticated" | "anonymous";

interface AuthContextValue {
  api: ApiClient;
  status: AuthStatus;
  me: Me | null;
  /** Set when the session ended unexpectedly (expired/revoked), for a friendly notice. */
  sessionEnded: boolean;
  completeSignIn: (token: { access_token: string; expires_at: string }) => Promise<Me>;
  signOut: (options?: { everywhere?: boolean }) => Promise<void>;
  reloadMe: () => Promise<void>;
  can: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** One API client per app, created at module load (the token store is global). */
export function createAppApi(options: { baseUrl?: string } = {}) {
  const listeners = new Set<() => void>();
  const { client, refreshSession } = createApiClient({
    baseUrl: options.baseUrl ?? "",
    onSessionExpired: () => listeners.forEach((l) => l()),
  });
  return {
    api: client,
    refreshSession,
    onSessionExpired(listener: () => void) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}

export type AppApi = ReturnType<typeof createAppApi>;

export function AuthProvider({ app, children }: { app: AppApi; children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthStatus>("restoring");
  const [me, setMe] = useState<Me | null>(null);
  const [sessionEnded, setSessionEnded] = useState(false);
  const restored = useRef(false);

  const loadMe = useCallback(async () => {
    const profile = await unwrap(app.api.GET("/api/v1/me"));
    setMe(profile);
    setStatus("authenticated");
    if (profile.preferred_language === "en" || profile.preferred_language === "bn") {
      setLocale(profile.preferred_language);
    }
    return profile;
  }, [app.api]);

  const resetToAnonymous = useCallback(() => {
    session.clear();
    setMe(null);
    setStatus("anonymous");
    queryClient.clear();
  }, [queryClient]);

  // Restore a session from the HttpOnly refresh cookie on first load.
  useEffect(() => {
    if (restored.current) return;
    restored.current = true;
    void (async () => {
      try {
        if (await app.refreshSession()) {
          await loadMe();
          return;
        }
      } catch {
        // fall through to anonymous; pages surface their own errors
      }
      resetToAnonymous();
    })();
  }, [app, loadMe, resetToAnonymous]);

  useEffect(
    () =>
      app.onSessionExpired(() => {
        setSessionEnded(true);
        resetToAnonymous();
      }),
    [app, resetToAnonymous],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      api: app.api,
      status,
      me,
      sessionEnded,
      async completeSignIn(token) {
        session.set(token.access_token, token.expires_at);
        setSessionEnded(false);
        return loadMe();
      },
      async signOut({ everywhere = false } = {}) {
        try {
          await expectNoContent(
            everywhere ? app.api.POST("/api/v1/auth/logout-all") : app.api.POST("/api/v1/auth/logout"),
          );
        } catch (err) {
          // Access token may already be gone: revoke via the refresh cookie instead.
          if (err instanceof ApiError && err.status === 401) {
            await app.api.POST("/api/v1/auth/logout-cookie").catch(() => undefined);
          }
        } finally {
          resetToAnonymous();
        }
      },
      async reloadMe() {
        await loadMe();
      },
      can(permission) {
        return me?.permissions.includes(permission) ?? false;
      },
    }),
    [app.api, status, me, sessionEnded, loadMe, resetToAnonymous],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
