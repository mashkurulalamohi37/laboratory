import { expect, test } from "@playwright/test";

import { latestCode, randomPatientPhone, smsCount } from "./sms";

test.describe("patient sign-in (mobile)", () => {
  test("registers with an SMS code, updates profile, signs out", async ({ page }) => {
    const phone = randomPatientPhone();
    await page.goto("/");
    await page.getByRole("link", { name: "Sign in" }).click();

    const before = await smsCount(phone.e164);
    await page.getByLabel("Mobile number").fill(phone.local);
    await page.getByRole("button", { name: "Send code" }).click();
    await expect(page.getByText(/We sent a code to/)).toBeVisible();

    await page.getByLabel("6-digit code").fill(await latestCode(phone.e164, { after: before }));
    await page.getByRole("button", { name: "Verify and continue" }).click();

    await expect(page).toHaveURL(/\/account$/);
    await page.getByLabel("Full name").fill("DEMO E2E Patient");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByRole("heading", { name: "Hello, DEMO E2E Patient" })).toBeVisible();

    // Session survives a reload (refresh cookie → new access token).
    await page.reload();
    await expect(page.getByRole("heading", { name: "Hello, DEMO E2E Patient" })).toBeVisible();

    await page.getByRole("button", { name: "Sign out" }).first().click();
    await expect(page).toHaveURL(/\/$/);
    await page.goto("/account");
    await expect(page).toHaveURL(/\/login\?next=%2Faccount/);
  });

  test("switches the interface to Bangla", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "বাংলা" }).first().click();
    await expect(page.locator("html")).toHaveAttribute("lang", "bn");
    await expect(page.getByRole("link", { name: "সাইন ইন" })).toBeVisible();
  });
});
