import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, createApiClient, unwrap } from "./index";
import { session } from "./session";

const json = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });

const BASE = "http://api.test";
const asRequest = (input: RequestInfo | URL) =>
  input instanceof Request ? input : new Request(input);

const future = () => new Date(Date.now() + 15 * 60_000).toISOString();
const me = { id: "u1", roles: [], permissions: [] };

afterEach(() => session.clear());

describe("createApiClient", () => {
  it("sends the bearer token and unwraps the envelope", async () => {
    session.set("tok-1", future());
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      expect(asRequest(input).headers.get("Authorization")).toBe("Bearer tok-1");
      return json(200, { success: true, data: me, meta: {} });
    });
    const { client } = createApiClient({ baseUrl: BASE, fetchImpl });
    await expect(unwrap(client.GET("/api/v1/me"))).resolves.toEqual(me);
  });

  it("refreshes once on TOKEN_EXPIRED and retries the original request", async () => {
    session.set("old", future());
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const req = asRequest(input);
      if (req.url.endsWith("/api/v1/auth/refresh")) {
        return json(200, { data: { access_token: "new", expires_at: future() } });
      }
      return req.headers.get("Authorization") === "Bearer new"
        ? json(200, { success: true, data: me, meta: {} })
        : json(401, { success: false, error: { code: "TOKEN_EXPIRED", message: "expired" } });
    });
    const { client } = createApiClient({ baseUrl: BASE, fetchImpl });
    await expect(unwrap(client.GET("/api/v1/me"))).resolves.toEqual(me);
    expect(session.get()?.token).toBe("new");
  });

  it("shares one refresh between concurrent requests (single flight)", async () => {
    session.set("old", new Date(Date.now() + 5_000).toISOString()); // stale → proactive refresh
    let refreshes = 0;
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const req = asRequest(input);
      if (req.url.endsWith("/api/v1/auth/refresh")) {
        refreshes += 1;
        await new Promise((r) => setTimeout(r, 10));
        return json(200, { data: { access_token: "new", expires_at: future() } });
      }
      return json(200, { success: true, data: me, meta: {} });
    });
    const { client } = createApiClient({ baseUrl: BASE, fetchImpl });
    await Promise.all([1, 2, 3].map(() => unwrap(client.GET("/api/v1/me"))));
    expect(refreshes).toBe(1);
  });

  it("clears the session and notifies when refresh fails", async () => {
    session.set("old", future());
    const onSessionExpired = vi.fn();
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const req = asRequest(input);
      if (req.url.endsWith("/api/v1/auth/refresh")) {
        return json(401, { success: false, error: { code: "REFRESH_INVALID", message: "x" } });
      }
      return json(401, { success: false, error: { code: "TOKEN_EXPIRED", message: "expired" } });
    });
    const { client } = createApiClient({ baseUrl: BASE, fetchImpl, onSessionExpired });
    const err = await unwrap(client.GET("/api/v1/me")).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(session.get()).toBeNull();
    expect(onSessionExpired).toHaveBeenCalledOnce();
  });

  it("maps error envelopes, validation details and Retry-After", async () => {
    const fetchImpl = vi.fn(async () =>
      json(
        429,
        {
          success: false,
          error: {
            code: "RATE_LIMITED",
            message: "slow down",
            details: [{ field: "phone", issue: "too many" }],
            request_id: "req-1",
          },
        },
        { "Retry-After": "42" },
      ),
    );
    const { client } = createApiClient({ baseUrl: BASE, fetchImpl });
    const err = (await unwrap(
      client.POST("/api/v1/auth/send-otp", { body: { phone: "01712345678" } }),
    ).catch((e: unknown) => e)) as ApiError;
    expect(err.code).toBe("RATE_LIMITED");
    expect(err.retryAfter).toBe(42);
    expect(err.requestId).toBe("req-1");
    expect(err.fieldErrors()).toEqual({ phone: "too many" });
  });

  it("turns fetch failures into NETWORK_ERROR", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });
    const { client } = createApiClient({ baseUrl: BASE, fetchImpl });
    const err = (await unwrap(client.GET("/api/v1/me")).catch((e: unknown) => e)) as ApiError;
    expect(err.isNetwork).toBe(true);
  });
});
