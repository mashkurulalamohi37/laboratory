import { describe, expect, it } from "vitest";

import { safeNextPath } from "./guards";

describe("safeNextPath", () => {
  it.each([
    ["/account", "/account"],
    ["%2Faccount%3Ftab%3Dsecurity", "/account?tab=security"],
  ])("keeps in-app path %s", (raw, expected) => {
    expect(safeNextPath(raw)).toBe(expected);
  });

  it.each(["https://evil.example", "//evil.example", "/\\evil.example", "javascript:alert(1)", "%E0%A4%A"])(
    "rejects %s",
    (raw) => {
      expect(safeNextPath(raw, "/home")).toBe("/home");
    },
  );

  it("falls back when missing", () => {
    expect(safeNextPath(null)).toBe("/");
  });
});
