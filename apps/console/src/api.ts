import { createAppApi } from "@nirnoy/app-core";

/** Same-origin API: Vite proxies /api in development, nginx does in production. */
export const app = createAppApi({ baseUrl: import.meta.env.VITE_API_BASE_URL ?? "" });
