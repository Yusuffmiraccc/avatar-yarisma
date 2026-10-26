import createClient from 'openapi-fetch';
import type { paths } from './generated';

const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '');
type Query = Record<string, string | number | boolean | null | undefined>;
type ErrorEnvelope = { error?: { code?: string; message?: string; details?: unknown }; request_id?: string };

let accessToken: string | null = null;
let refreshToken: string | null = typeof window === 'undefined' ? null : window.sessionStorage.getItem('avatar.refresh');
let refreshInFlight: Promise<boolean> | null = null;
const idempotencyKeys = new Map<string, { fingerprint: string; key: string }>();

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly code?: string,
    public readonly details?: unknown,
    public readonly requestId?: string,
    public readonly retryAfterSeconds?: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function dispatchExpired() {
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('avatar:auth-expired'));
}

export function setSessionTokens(tokens: { access_token: string; refresh_token: string }) {
  accessToken = tokens.access_token;
  refreshToken = tokens.refresh_token;
  if (typeof window !== 'undefined') window.sessionStorage.setItem('avatar.refresh', tokens.refresh_token);
}

export function hasRefreshSession() {
  return Boolean(refreshToken);
}

export function clearSessionTokens() {
  accessToken = null;
  refreshToken = null;
  if (typeof window !== 'undefined') window.sessionStorage.removeItem('avatar.refresh');
}

async function refreshAccessToken(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  if (!refreshToken) return false;
  const currentRefreshToken = refreshToken;
  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ refresh_token: currentRefreshToken }),
      });
      if (!response.ok) return false;
      const tokens = await response.json() as { access_token: string; refresh_token: string };
      setSessionTokens(tokens);
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

async function authenticatedFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const original = new Request(input, init);
  const url = new URL(original.url);
  const authRoute = /\/auth\/(login|refresh|logout)$/.test(url.pathname);
  const headers = new Headers(original.headers);
  headers.set('Accept', 'application/json');
  if (accessToken && !authRoute) headers.set('Authorization', `Bearer ${accessToken}`);
  const request = new Request(original, { headers });
  const response = await fetch(request);
  if (response.status !== 401 || authRoute || request.headers.has('X-Auth-Retry')) return response;
  if (!(await refreshAccessToken())) {
    clearSessionTokens();
    dispatchExpired();
    return response;
  }
  const retryHeaders = new Headers(request.headers);
  retryHeaders.set('X-Auth-Retry', '1');
  if (accessToken) retryHeaders.set('Authorization', `Bearer ${accessToken}`);
  return fetch(new Request(request.clone(), { headers: retryHeaders }));
}

const client = createClient<paths>({ baseUrl, fetch: authenticatedFetch });

async function unwrap<T>(result: { data?: unknown; error?: unknown; response: Response }): Promise<T> {
  const { data, error, response } = result;
  if (!response.ok) {
    let payload = error as ErrorEnvelope | undefined;
    if (!payload || !payload.error) {
      try { payload = await response.clone().json() as ErrorEnvelope; } catch { payload = undefined; }
    }
    const retry = response.headers.get('Retry-After');
    throw new ApiError(
      response.status,
      payload?.error?.message || `İstek tamamlanamadı (${response.status}).`,
      payload?.error?.code,
      payload?.error?.details,
      payload?.request_id || response.headers.get('X-Request-ID') || undefined,
      retry ? Number(retry) : undefined,
    );
  }
  return data as T;
}

const cleanQuery = (query?: Query) => Object.fromEntries(
  Object.entries(query || {}).filter(([, value]) => value !== undefined && value !== null && value !== ''),
);

export async function apiGet<T>(path: string, query?: Query): Promise<T> {
  const result = await client.GET(path as never, { params: { query: cleanQuery(query) } as never } as never);
  return unwrap<T>(result as never);
}

export async function apiPost<T>(path: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
  const result = await client.POST(path as never, { body: body as never, headers } as never);
  return unwrap<T>(result as never);
}

export async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  const result = await client.PATCH(path as never, { body: body as never } as never);
  return unwrap<T>(result as never);
}

export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  const result = await client.PUT(path as never, { body: body as never } as never);
  return unwrap<T>(result as never);
}

export async function apiPostIdempotent<T>(path: string, body: unknown, actionId: string): Promise<T> {
  const fingerprint = JSON.stringify(body);
  const prior = idempotencyKeys.get(actionId);
  const key = prior?.fingerprint === fingerprint ? prior.key : crypto.randomUUID();
  idempotencyKeys.set(actionId, { fingerprint, key });
  try {
    const result = await apiPost<T>(path, body, { 'Idempotency-Key': key });
    idempotencyKeys.delete(actionId);
    return result;
  } catch (error) {
    if (error instanceof ApiError && error.status < 500 && error.status !== 429) idempotencyKeys.delete(actionId);
    throw error;
  }
}

export async function apiPostIdempotentWithoutBody<T>(path: string, actionId: string): Promise<T> {
  const prior = idempotencyKeys.get(actionId);
  const key = prior?.key || crypto.randomUUID();
  idempotencyKeys.set(actionId, { fingerprint: '', key });
  try {
    const result = await apiPost<T>(path, undefined, { 'Idempotency-Key': key });
    idempotencyKeys.delete(actionId);
    return result;
  } catch (error) {
    if (error instanceof ApiError && error.status < 500 && error.status !== 429) idempotencyKeys.delete(actionId);
    throw error;
  }
}

export function __resetApiForTests() {
  clearSessionTokens();
  refreshInFlight = null;
  idempotencyKeys.clear();
}
