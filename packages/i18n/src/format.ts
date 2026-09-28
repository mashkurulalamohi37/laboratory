/** Locale-aware formatting for Bangladesh: Taka (৳), Bangla digits, phone numbers. */

export type Locale = "en" | "bn";

const BN_DIGITS = ["০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯"] as const;

export function toBanglaDigits(value: string | number): string {
  return String(value).replace(/[0-9]/g, (d) => BN_DIGITS[Number(d)] ?? d);
}

export function fromBanglaDigits(value: string): string {
  return value.replace(/[০-৯]/g, (d) =>
    String(BN_DIGITS.indexOf(d as (typeof BN_DIGITS)[number])),
  );
}

/**
 * Money is stored as integer poisha (1/100 BDT). Uses the South Asian grouping
 * (1,00,000) that en-IN and bn-BD share.
 */
export function formatBDT(poisha: number, locale: Locale = "en"): string {
  const hasFraction = poisha % 100 !== 0;
  const number = new Intl.NumberFormat("en-IN", {
    minimumFractionDigits: hasFraction ? 2 : 0,
    maximumFractionDigits: 2,
  }).format(poisha / 100);
  return `৳${locale === "bn" ? toBanglaDigits(number) : number}`;
}

/** +8801712345678 → 01712-345678 (display only). */
export function formatBDPhone(e164: string, locale: Locale = "en"): string {
  const local = e164.replace(/^\+880/, "0");
  const pretty = local.length === 11 ? `${local.slice(0, 5)}-${local.slice(5)}` : local;
  return locale === "bn" ? toBanglaDigits(pretty) : pretty;
}

/** Client-side mirror of the API's normaliser, for instant form feedback only. */
export function normalizeBDPhone(raw: string): string | null {
  const compact = fromBanglaDigits(raw).replace(/[\s\-().]/g, "");
  const match = /^(?:\+?880|0)?(1[3-9]\d{8})$/.exec(compact);
  return match ? `+880${match[1]}` : null;
}

export function formatDateTime(iso: string, locale: Locale = "en"): string {
  return new Intl.DateTimeFormat(locale === "bn" ? "bn-BD" : "en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Dhaka",
  }).format(new Date(iso));
}

/** Plain number with South Asian grouping; Bangla digits in bn. */
export function formatNumber(value: number, locale: Locale = "en"): string {
  const text = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(value);
  return locale === "bn" ? toBanglaDigits(text) : text;
}

/** "07:00:00" (Bangladesh local time from the API) → "7:00 AM" / "সকাল ৭:০০". */
export function formatTimeOfDay(hhmm: string, locale: Locale = "en"): string {
  const [h = 0, m = 0] = hhmm.split(":").map(Number);
  const date = new Date(Date.UTC(2000, 0, 1, h, m));
  return new Intl.DateTimeFormat(locale === "bn" ? "bn-BD" : "en-US", {
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(date);
}

/** ISO date ("2026-12-16") → "16 Dec 2026" / Bangla. */
export function formatDate(iso: string, locale: Locale = "en"): string {
  return new Intl.DateTimeFormat(locale === "bn" ? "bn-BD" : "en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Dhaka",
  }).format(new Date(iso.length === 10 ? `${iso}T00:00:00+06:00` : iso));
}

/** Pick the Bangla text when the UI is Bangla and a translation exists. */
export function localized(locale: Locale, en: string, bn: string | null | undefined): string {
  return locale === "bn" && bn ? bn : en;
}
