import i18next, { type i18n as I18n } from "i18next";
import { initReactI18next } from "react-i18next";

import type { Locale } from "./format";
import bn from "./locales/bn";
import en, { type Messages } from "./locales/en";

export * from "./format";
export { Trans, useTranslation } from "react-i18next";
export type { Messages };

const STORAGE_KEY = "nirnoy.locale";
/** Mirrors the choice for the web prerender server, which cannot read localStorage. */
export const LOCALE_COOKIE = "nirnoy_lang";

export const SUPPORTED_LOCALES: readonly Locale[] = ["en", "bn"];

export function storedLocale(): Locale | null {
  try {
    const value = globalThis.localStorage?.getItem(STORAGE_KEY);
    return value === "en" || value === "bn" ? value : null;
  } catch {
    return null;
  }
}

/**
 * Initialise i18next once per app (idempotent). `lng` overrides the stored choice, e.g.
 * to hydrate server-rendered HTML in the language it was rendered in.
 */
export function initI18n(options: { lng?: Locale } = {}): I18n {
  if (!i18next.isInitialized) {
    void i18next.use(initReactI18next).init({
      resources: { en, bn },
      lng: options.lng ?? storedLocale() ?? "en",
      fallbackLng: "en",
      defaultNS: "common",
      ns: Object.keys(en),
      interpolation: { escapeValue: false }, // React escapes output
      initImmediate: false,
    });
    const applyLang = (lng: string) => {
      if (typeof document !== "undefined") document.documentElement.lang = lng;
    };
    applyLang(i18next.language);
    i18next.on("languageChanged", applyLang);
  }
  return i18next;
}

export function currentLocale(): Locale {
  return i18next.language === "bn" ? "bn" : "en";
}

export function setLocale(locale: Locale): void {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, locale);
  } catch {
    // Storage can be unavailable (private mode); the choice still applies to this visit.
  }
  if (typeof document !== "undefined") {
    document.cookie = `${LOCALE_COOKIE}=${locale}; Path=/; Max-Age=31536000; SameSite=Lax`;
  }
  void i18next.changeLanguage(locale);
}
