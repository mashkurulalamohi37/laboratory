/** Normalised error for every failed API call (HTTP error envelope or network failure). */

export interface ErrorDetail {
  field?: string | null;
  issue: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ErrorDetail[];
  readonly requestId: string | null;
  readonly retryAfter: number | null;

  constructor(init: {
    status: number;
    code: string;
    message: string;
    details?: ErrorDetail[];
    requestId?: string | null;
    retryAfter?: number | null;
  }) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code;
    this.details = init.details ?? [];
    this.requestId = init.requestId ?? null;
    this.retryAfter = init.retryAfter ?? null;
  }

  /** Map of field → issue, for binding server validation errors onto form fields. */
  fieldErrors(): Record<string, string> {
    return Object.fromEntries(
      this.details.filter((d) => d.field).map((d) => [d.field as string, d.issue]),
    );
  }

  get isNetwork(): boolean {
    return this.code === NETWORK_ERROR;
  }
}

export const NETWORK_ERROR = "NETWORK_ERROR";

interface ErrorEnvelope {
  success: false;
  error: { code: string; message: string; details?: ErrorDetail[]; request_id?: string | null };
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof (value as ErrorEnvelope).error?.code === "string"
  );
}

export function toApiError(response: Response, body: unknown): ApiError {
  const retryAfter = Number(response.headers.get("retry-after")) || null;
  if (isErrorEnvelope(body)) {
    return new ApiError({
      status: response.status,
      code: body.error.code,
      message: body.error.message,
      details: body.error.details ?? [],
      requestId: body.error.request_id ?? response.headers.get("x-request-id"),
      retryAfter,
    });
  }
  return new ApiError({
    status: response.status,
    code: response.status === 429 ? "RATE_LIMITED" : "HTTP_ERROR",
    message: response.statusText || "Request failed",
    requestId: response.headers.get("x-request-id"),
    retryAfter,
  });
}

export function networkError(cause: unknown): ApiError {
  const err = new ApiError({ status: 0, code: NETWORK_ERROR, message: "Network request failed" });
  (err as { cause?: unknown }).cause = cause;
  return err;
}
