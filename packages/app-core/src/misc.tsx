import { ApiError } from "@nirnoy/api-client";
import { currentLocale, setLocale, useTranslation, type Locale } from "@nirnoy/i18n";
import { cn } from "@nirnoy/ui";
import { QueryClient } from "@tanstack/react-query";

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        // Retry only transient failures; 4xx answers will not change on retry.
        retry: (count, err) =>
          count < 2 && (!(err instanceof ApiError) || err.isNetwork || err.status >= 500),
      },
      mutations: { retry: false },
    },
  });
}

/** Human message for an error: known auth codes are translated, the rest fall back. */
export function useErrorMessage() {
  const { t, i18n } = useTranslation();
  return (err: unknown): string => {
    if (err instanceof ApiError) {
      if (err.isNetwork) return t("networkError");
      const key = `auth:errors.${err.code}`;
      if (i18n.exists(key)) return t(key);
      if (err.code === "SESSION_REVOKED" || err.code === "REFRESH_INVALID") {
        return t("auth:sessionExpired");
      }
      return err.message || t("somethingWrong");
    }
    return t("somethingWrong");
  };
}

export function requestIdOf(err: unknown): string | null {
  return err instanceof ApiError ? err.requestId : null;
}

const LABELS: Record<Locale, string> = { en: "English", bn: "বাংলা" };

export function LanguageSwitch({ className }: { className?: string }) {
  const { t } = useTranslation();
  const active = currentLocale();
  return (
    <div
      role="group"
      aria-label={t("language")}
      className={cn(
        "inline-flex rounded-full border border-border bg-surface-muted/60 p-0.5 text-sm transition-colors hover:border-brand-300",
        className,
      )}
    >
      {(["en", "bn"] as const).map((locale) => (
        <button
          key={locale}
          type="button"
          lang={locale}
          aria-pressed={active === locale}
          onClick={() => setLocale(locale)}
          className={cn(
            "rounded-full px-3 py-1 font-medium transition-all",
            active === locale
              ? "bg-gradient-brand text-white shadow-[var(--shadow-brand)] dark:text-bg"
              : "text-muted hover:bg-surface hover:text-brand-700",
          )}
        >
          {LABELS[locale]}
        </button>
      ))}
    </div>
  );
}
