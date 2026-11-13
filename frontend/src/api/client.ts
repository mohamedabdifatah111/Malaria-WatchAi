import axios, { AxiosError, type AxiosInstance } from "axios";
import type { ApiErrorBody, Envelope, Paged } from "../types/api";

const TOKEN_KEY = "mwai.token";

export function apiBaseUrl(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";
  return raw.replace(/\/+$/, "");
}

/** Normalised error: every failed request becomes one of these. */
export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string;

  constructor(message: string, status: number | null, code: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }

  get isAuth(): boolean {
    return this.status === 401;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }
}

// Token storage. The token is never logged. sessionStorage limits it to this tab session.
export const tokenStore = {
  get(): string | null {
    try {
      return sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string) {
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* storage unavailable: token lives only in memory for this page */
    }
  },
  clear() {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      /* ignore */
    }
  },
};

type UnauthorizedHandler = () => void;
let onUnauthorized: UnauthorizedHandler | null = null;
export function setUnauthorizedHandler(fn: UnauthorizedHandler | null) {
  onUnauthorized = fn;
}

export function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err;
  if (axios.isAxiosError(err)) {
    const e = err as AxiosError<Partial<ApiErrorBody> & { detail?: string; non_field_errors?: string[] }>;
    const status = e.response?.status ?? null;
    const body = e.response?.data;
    const message =
      body?.error?.message ??
      body?.detail ??
      body?.non_field_errors?.[0] ??
      (status === null
        ? "The server could not be reached. Check that the backend is running and VITE_API_BASE_URL is correct."
        : status >= 500
          ? "The server had a problem completing this request."
          : "The request could not be completed.");
    const code = body?.error?.code ?? (status === null ? "NETWORK_ERROR" : `HTTP_${status}`);
    return new ApiError(message, status, code);
  }
  return new ApiError("Unexpected error.", null, "UNKNOWN");
}

export function createClient(): AxiosInstance {
  const client = axios.create({
    baseURL: `${apiBaseUrl()}/api/v1/`,
    timeout: 60_000,
    headers: { Accept: "application/json", "Content-Type": "application/json" },
  });
  client.interceptors.request.use((config) => {
    const token = tokenStore.get();
    if (token) config.headers.set("Authorization", `Token ${token}`);
    return config;
  });
  client.interceptors.response.use(
    (r) => r,
    (err) => {
      const apiErr = toApiError(err);
      if (apiErr.isAuth && tokenStore.get()) {
        tokenStore.clear();
        onUnauthorized?.();
      }
      return Promise.reject(apiErr);
    },
  );
  return client;
}

export const api = createClient();

/** Unwrap {success, data, meta}. */
export function unwrap<T>(body: Envelope<T> | T): T {
  if (body && typeof body === "object" && "success" in body && "data" in body) {
    return (body as Envelope<T>).data;
  }
  return body as T;
}

/** Unwrap a paginated list envelope, keeping the backend's data_status. */
export function unwrapPaged<T>(body: Envelope<T[]>): Paged<T> {
  const items = Array.isArray(body?.data) ? body.data : [];
  return {
    items,
    pagination: body?.meta?.pagination ?? null,
    dataStatus: body?.meta?.data_status ?? (items.length ? "available" : "no_data"),
    message: body?.meta?.message,
  };
}

/** Drop empty filter values so they are not sent as `?country=`. */
export function cleanParams(params: Record<string, unknown>): Record<string, string | number | boolean> {
  const out: Record<string, string | number | boolean> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    out[k] = v as string | number | boolean;
  }
  return out;
}

export async function getPaged<T>(path: string, params: Record<string, unknown> = {}): Promise<Paged<T>> {
  const r = await api.get<Envelope<T[]>>(path, { params: cleanParams({ page_size: 200, ...params }) });
  return unwrapPaged<T>(r.data);
}

export async function getOne<T>(path: string, params: Record<string, unknown> = {}): Promise<T> {
  const r = await api.get<Envelope<T>>(path, { params: cleanParams(params) });
  return unwrap<T>(r.data);
}
