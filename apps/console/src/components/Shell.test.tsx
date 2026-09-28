import { json, mockApi, ok, renderRoutes } from "@nirnoy/app-core/testing";
import { RequireAuth } from "@nirnoy/app-core";
import { session } from "@nirnoy/api-client";
import { screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Forbidden } from "./Forbidden";
import { Shell } from "./Shell";

const future = () => new Date(Date.now() + 15 * 60_000).toISOString();

function signedInAs(me: { is_staff: boolean; permissions: string[] }) {
  mockApi({
    "POST /api/v1/auth/refresh": () => ok({ access_token: "tok", expires_at: future() }),
    "GET /api/v1/me": () =>
      ok({ id: "u1", phone: "+8801811000001", full_name: "Test User", preferred_language: "en",
           has_password: true, roles: [], ...me }),
  });
}

const routes = [
  {
    element: (
      <RequireAuth>
        <Shell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <p>dashboard</p> },
      {
        path: "users",
        element: (
          <RequireAuth permission="user:manage" forbidden={<Forbidden />}>
            <p>users page</p>
          </RequireAuth>
        ),
      },
    ],
  },
  { path: "/login", element: <p>login page</p> },
];

afterEach(() => {
  vi.unstubAllGlobals();
  session.clear();
});

describe("console shell", () => {
  it("shows only the menu entries the user holds permissions for", async () => {
    signedInAs({ is_staff: true, permissions: ["audit:view"] });
    renderRoutes(routes, "/");
    const nav = await screen.findByRole("navigation", { name: "Menu" });
    expect(within(nav).getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(within(nav).getByRole("link", { name: "Audit log" })).toBeInTheDocument();
    expect(within(nav).queryByRole("link", { name: "Users" })).not.toBeInTheDocument();
    expect(within(nav).queryByRole("link", { name: "Roles & permissions" })).not.toBeInTheDocument();
  });

  it("blocks direct navigation to a page without permission", async () => {
    signedInAs({ is_staff: true, permissions: [] });
    renderRoutes(routes, "/users");
    expect(await screen.findByText("You don't have permission to view this page.")).toBeInTheDocument();
    expect(screen.queryByText("users page")).not.toBeInTheDocument();
  });

  it("refuses console access to non-staff accounts", async () => {
    signedInAs({ is_staff: false, permissions: [] });
    renderRoutes(routes, "/");
    expect(await screen.findByText("No console access")).toBeInTheDocument();
    expect(screen.queryByText("dashboard")).not.toBeInTheDocument();
  });

  it("sends anonymous visitors to sign in", async () => {
    mockApi({
      "POST /api/v1/auth/refresh": () =>
        json(401, { success: false, error: { code: "REFRESH_INVALID", message: "x" } }),
    });
    const { router } = renderRoutes(routes, "/users");
    expect(await screen.findByText("login page")).toBeInTheDocument();
    expect(router.state.location.search).toBe("?next=%2Fusers");
  });
});
