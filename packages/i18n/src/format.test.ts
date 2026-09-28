import { describe, expect, it } from "vitest";

import {
  formatBDPhone,
  formatBDT,
  formatDate,
  formatNumber,
  formatTimeOfDay,
  fromBanglaDigits,
  localized,
  normalizeBDPhone,
  toBanglaDigits,
} from "./format";
import bn from "./locales/bn";
import en from "./locales/en";

describe("formatBDT", () => {
  it("formats whole taka from poisha with South Asian grouping", () => {
    expect(formatBDT(150_000)).toBe("৳1,500");
    expect(formatBDT(12_345_600)).toBe("৳1,23,456");
  });
  it("keeps poisha when present", () => {
    expect(formatBDT(150_050)).toBe("৳1,500.50");
  });
  it("renders Bangla digits in bn", () => {
    expect(formatBDT(150_000, "bn")).toBe("৳১,৫০০");
  });
});

describe("digits", () => {
  it("round-trips Bangla digits", () => {
    expect(toBanglaDigits("01712")).toBe("০১৭১২");
    expect(fromBanglaDigits("০১৭১২")).toBe("01712");
  });
});

describe("phone", () => {
  it.each(["01712345678", "+8801712345678", "8801712345678", "০১৭১২৩৪৫৬৭৮", "01712-345 678"])(
    "normalises %s",
    (raw) => expect(normalizeBDPhone(raw)).toBe("+8801712345678"),
  );
  it.each(["", "0171234567", "01212345678", "abc"])("rejects %s", (raw) =>
    expect(normalizeBDPhone(raw)).toBeNull(),
  );
  it("formats for display", () => {
    expect(formatBDPhone("+8801712345678")).toBe("01712-345678");
    expect(formatBDPhone("+8801712345678", "bn")).toBe("০১৭১২-৩৪৫৬৭৮");
  });
});

describe("catalogues", () => {
  const keys = (obj: object, prefix = ""): string[] =>
    Object.entries(obj).flatMap(([k, v]) =>
      typeof v === "object" && v !== null ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
    );
  it("bn covers exactly the en keys", () => {
    expect(keys(bn).sort()).toEqual(keys(en).sort());
  });
  it("bn keeps every interpolation placeholder", () => {
    const flat = (obj: object): Record<string, string> =>
      Object.fromEntries(
        keys(obj).map((k) => [k, k.split(".").reduce<unknown>((o, p) => (o as never)[p], obj)]),
      ) as Record<string, string>;
    const enFlat = flat(en);
    const bnFlat = flat(bn);
    for (const [key, value] of Object.entries(enFlat)) {
      const vars = value.match(/{{\w+}}/g) ?? [];
      for (const v of vars) expect(bnFlat[key], key).toContain(v);
    }
  });
});

describe("catalogue formatting", () => {
  it("formats times of day", () => {
    expect(formatTimeOfDay("07:00:00")).toBe("7:00 AM");
    expect(formatTimeOfDay("21:30")).toBe("9:30 PM");
  });
  it("formats dates in Bangladesh time", () => {
    expect(formatDate("2026-12-16")).toBe("16 Dec 2026");
  });
  it("groups numbers and localises digits", () => {
    expect(formatNumber(125000)).toBe("1,25,000");
    expect(formatNumber(12, "bn")).toBe("১২");
  });
  it("falls back to English when a translation is missing", () => {
    expect(localized("bn", "Thyroid", "থাইরয়েড")).toBe("থাইরয়েড");
    expect(localized("bn", "Thyroid", null)).toBe("Thyroid");
    expect(localized("en", "Thyroid", "থাইরয়েড")).toBe("Thyroid");
  });
});
