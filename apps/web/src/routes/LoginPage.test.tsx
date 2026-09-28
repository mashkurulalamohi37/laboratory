import { session } from "@nirnoy/api-client";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { json, mockApi, ok, renderRoutes } from "@nirnoy/app-core/testing";
import LoginPage from "./LoginPage";

const routes = [
  { path: "/login", element: <LoginPage /> },
  { path: "/account", element: <p>account page</p> },
];

const future = () => new Date(Date.now() + 15 * 60_000).toISOString();
const noSession = () => json(401, { success: false, error: { code: "REFRESH_INVALID", message: "x" } });

afterEach(() => {
  vi.unstubAllGlobals();
  session.clear();
});

describe("patient OTP sign-in", () => {
  it("validates the phone before calling the API", async () => {
    const calls = mockApi({ "POST /api/v1/auth/refresh": noSession });
    renderRoutes(routes, "/login");
    await userEvent.type(await screen.findByLabelText(/Mobile number/), "12345");
    await userEvent.click(screen.getByRole("button", { name: "Send code" }));
    expect(await screen.findByText("Enter a valid Bangladesh mobile number.")).toBeInTheDocument();
    expect(calls.some((c) => c.path === "/api/v1/auth/send-otp")).toBe(false);
  });

  it("sends a normalised number, verifies the code and lands on the account page", async () => {
    const calls = mockApi({
      "POST /api/v1/auth/refresh": noSession,
      "POST /api/v1/auth/send-otp": () =>
        json(202, { success: true, data: { sent: true, expires_in: 300, resend_after: 60 } }),
      "POST /api/v1/auth/verify-otp": () =>
        ok({ access_token: "tok", expires_at: future(), is_new_user: true }),
      "GET /api/v1/me": () =>
        ok({ id: "u1", phone: "+8801712345678", full_name: null, is_staff: false,
             preferred_language: "en", has_password: false, roles: [], permissions: [] }),
    });
    const { router } = renderRoutes(routes, "/login");

    await userEvent.type(await screen.findByLabelText(/Mobile number/), "017-1234 5678");
    await userEvent.click(screen.getByRole("button", { name: "Send code" }));

    expect(await screen.findByText("We sent a code to 01712-345678.")).toBeInTheDocument();
    expect(calls.find((c) => c.path === "/api/v1/auth/send-otp")?.body).toEqual({
      phone: "+8801712345678",
      purpose: "LOGIN",
    });
    // Focus moves to the code field for keyboard and screen-reader users.
    await waitFor(() => expect(screen.getByLabelText(/6-digit code/)).toHaveFocus());

    await userEvent.type(screen.getByLabelText(/6-digit code/), "123456");
    await userEvent.click(screen.getByRole("button", { name: "Verify and continue" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/account"));
    expect(session.get()?.token).toBe("tok");
  });

  it("shows a translated message for a wrong code", async () => {
    mockApi({
      "POST /api/v1/auth/refresh": noSession,
      "POST /api/v1/auth/send-otp": () =>
        json(202, { success: true, data: { sent: true, expires_in: 300, resend_after: 60 } }),
      "POST /api/v1/auth/verify-otp": () =>
        json(401, { success: false, error: { code: "OTP_INVALID", message: "raw" } }),
    });
    renderRoutes(routes, "/login");
    await userEvent.type(await screen.findByLabelText(/Mobile number/), "01712345678");
    await userEvent.click(screen.getByRole("button", { name: "Send code" }));
    await userEvent.type(await screen.findByLabelText(/6-digit code/), "000000");
    await userEvent.click(screen.getByRole("button", { name: "Verify and continue" }));
    expect(await screen.findByText("That code is incorrect or has expired.")).toBeInTheDocument();
    expect(screen.getByText(/Resend code in \d+s/)).toBeInTheDocument();
  });
});
