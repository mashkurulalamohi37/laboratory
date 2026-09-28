import { defineConfig, devices } from "@playwright/test";

/**
 * Runs against a live stack. Defaults target the full docker stack behind nginx:
 *   docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile fullstack up -d
 * For local Vite dev servers set WEB_URL=http://localhost:5173 CONSOLE_URL=http://localhost:5174.
 */
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "mobile-web",
      testMatch: /patient-.*\.spec\.ts/,
      use: { ...devices["Pixel 7"], baseURL: process.env.WEB_URL ?? "http://localhost" },
    },
    {
      name: "desktop-console",
      testMatch: /staff-.*\.spec\.ts/,
      use: { ...devices["Desktop Chrome"], baseURL: process.env.CONSOLE_URL ?? "http://console.localhost" },
    },
  ],
});
