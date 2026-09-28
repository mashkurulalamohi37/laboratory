/** Test helpers for app packages (import from "@nirnoy/app-core/testing"; never in app code). */
import { AuthProvider, createAppApi } from "./auth";
import { createQueryClient } from "./misc";
import { initI18n } from "@nirnoy/i18n";
import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider, type RouteObject } from "react-router";
import { vi } from "vitest";

initI18n();

type Handler = (req: Request) => Response | Promise<Response>;

export const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

export const ok = (data: unknown) => json(200, { success: true, data, meta: {} });

/** Route fetch calls by "METHOD /path" to handlers; records every request. */
export function mockApi(handlers: Record<string, Handler>) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const req = input instanceof Request ? input : new Request(input, init);
      const path = new URL(req.url).pathname;
      const text = req.method === "GET" ? "" : await req.clone().text();
      calls.push({ method: req.method, path, body: text ? JSON.parse(text) : null });
      const handler = handlers[`${req.method} ${path}`];
      if (!handler) return json(404, { success: false, error: { code: "NOT_FOUND", message: path } });
      return handler(req);
    }),
  );
  return calls;
}

export function renderRoutes(routes: RouteObject[], initialPath: string) {
  const app = createAppApi({ baseUrl: "http://api.test" });
  const router = createMemoryRouter(routes, { initialEntries: [initialPath] });
  const ui: ReactElement = (
    <QueryClientProvider client={createQueryClient()}>
      <AuthProvider app={app}>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  );
  return { ...render(ui), router };
}
