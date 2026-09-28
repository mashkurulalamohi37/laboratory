import { expect, test } from "@playwright/test";

import { latestCode, smsCount } from "./sms";

// Seeded by `python -m app.scripts.seed --demo` (development only).
const ADMIN = { local: "01900000001", e164: "+8801900000001" };
const TECH = { local: "01900000004", e164: "+8801900000004" };
const PASSWORD = process.env.DEMO_STAFF_PASSWORD ?? "Demo-Staff-2026";

async function staffSignIn(page: import("@playwright/test").Page, who: typeof ADMIN) {
  await page.goto("/login");
  const before = await smsCount(who.e164);
  await page.getByLabel("Mobile number or email").fill(who.local);
  await page.getByRole("textbox", { name: "Password", exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("heading", { name: "Verify it's you" })).toBeVisible();
  await page.getByLabel("6-digit code").fill(await latestCode(who.e164, { after: before }));
  await page.getByRole("button", { name: "Verify and continue" }).click();
  await expect(page.getByRole("navigation", { name: "Menu" })).toBeVisible();
}

test.describe("staff console (desktop)", () => {
  test("admin signs in with 2FA and manages users; audit is recorded", async ({ page }) => {
    await staffSignIn(page, ADMIN);
    await page.getByRole("link", { name: "Users" }).click();
    await expect(page.getByRole("heading", { name: "Users" })).toBeVisible();
    await page.getByPlaceholder("Search name, phone or email").fill("DEMO Lab");
    await expect(page.getByRole("cell", { name: /DEMO Lab Technician/ })).toBeVisible();

    await page.getByRole("link", { name: "Audit log" }).click();
    await page.getByLabel("Action").fill("auth.login");
    await expect(page.getByRole("cell", { name: "auth.login" }).first()).toBeVisible();
  });

  test("technician cannot see or open admin pages", async ({ page }) => {
    await staffSignIn(page, TECH);
    const nav = page.getByRole("navigation", { name: "Menu" });
    await expect(nav.getByRole("link", { name: "Users" })).toHaveCount(0);
    await page.goto("/users");
    await expect(page.getByText("You don't have permission to view this page.")).toBeVisible();
  });
});
