import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5174,
    // Same-origin API in development, so the HttpOnly refresh cookie just works.
    proxy: { "/api": { target: process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000", changeOrigin: false } },
  },
  build: {
    sourcemap: true,
    target: "es2022",
    rollupOptions: {
      output: {
        // Framework code changes rarely: separate chunks stay cached across app releases.
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (/[/\\](react|react-dom|react-router|scheduler)[/\\]/.test(id)) return "react";
          if (/[/\\](@tanstack|i18next|react-i18next|openapi-fetch)[/\\]/.test(id)) return "data";
          return undefined;
        },
      },
    },
  },
  test: { environment: "jsdom", setupFiles: ["./vitest.setup.ts"] },
});
