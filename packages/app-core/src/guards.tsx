import { useTranslation } from "@nirnoy/i18n";
import { Spinner } from "@nirnoy/ui";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";

import { useAuth } from "./auth";

export function FullPageSpinner() {
  const { t } = useTranslation();
  return (
    <div className="flex min-h-[50dvh] items-center justify-center">
      <Spinner label={t("loading")} />
    </div>
  );
}

/**
 * Route guard (UX only: the API enforces every permission independently).
 * Unauthenticated users go to `loginPath` and come back afterwards.
 */
export function RequireAuth({
  children,
  loginPath = "/login",
  permission,
  forbidden,
}: {
  children: ReactNode;
  loginPath?: string;
  permission?: string;
  forbidden?: ReactNode;
}) {
  const { status, can } = useAuth();
  const location = useLocation();
  if (status === "restoring") return <FullPageSpinner />;
  if (status === "anonymous") {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`${loginPath}?next=${next}`} replace />;
  }
  if (permission && !can(permission)) return <>{forbidden ?? null}</>;
  return <>{children}</>;
}

/** Only allow relative in-app redirects (prevents open-redirects via ?next=). */
export function safeNextPath(raw: string | null, fallback = "/"): string {
  if (!raw) return fallback;
  try {
    const decoded = decodeURIComponent(raw);
    return decoded.startsWith("/") && !decoded.startsWith("//") && !decoded.includes("\\")
      ? decoded
      : fallback;
  } catch {
    return fallback;
  }
}
