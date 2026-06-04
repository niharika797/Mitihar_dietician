/**
 * authService.ts — all auth-related API calls.
 *
 * Endpoint mapping (FastAPI router prefix: /api/v1/auth):
 *   Doctor login step 1:  POST /auth/doctor/login      (form-encoded)
 *   Doctor login step 2:  POST /auth/doctor/mfa-login  (JSON)
 *   Admin  login step 1:  POST /auth/admin/login       (form-encoded)
 *   Admin  login step 2:  POST /auth/admin/mfa-login   (JSON)
 *   Token  refresh:       POST /auth/refresh           (cookie auto-sent)
 *
 * Note on form-encoding: FastAPI's OAuth2PasswordRequestForm requires
 * Content-Type: application/x-www-form-urlencoded with fields
 * `username` and `password` — NOT JSON. We use URLSearchParams for this.
 */

import apiClient from './axios';
import { useAuthStore } from '../stores/authStore';
import type {
  LoginResult,
  MFALoginRequest,
  LoginResponse,
  RefreshResponse,
} from './types';

// ─── Helper: decode JWT payload without a library ────────────────────────────
// The JWT is three base64url segments separated by dots.
// We only need the payload (middle segment).

function decodeJwtPayload(token: string): Record<string, unknown> {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join(''),
    );
    return JSON.parse(json);
  } catch {
    return {};
  }
}

// ─── Helper: form-encoded login POST ─────────────────────────────────────────

async function postFormLogin(
  url: string,
  email: string,
  password: string,
): Promise<LoginResult> {
  const params = new URLSearchParams();
  params.append('username', email);
  params.append('password', password);

  const { data } = await apiClient.post<LoginResult>(url, params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data;
}

// ─── Doctor auth ─────────────────────────────────────────────────────────────

export async function loginDoctor(
  email: string,
  password: string,
): Promise<LoginResult> {
  return postFormLogin('/auth/doctor/login', email, password);
}

export async function loginDoctorMfa(
  partial_token: string,
  totp_code: string,
): Promise<LoginResponse> {
  const body: MFALoginRequest = { partial_token, totp_code };
  const { data } = await apiClient.post<LoginResponse>(
    '/auth/doctor/mfa-login',
    body,
  );
  return data;
}

// ─── Admin auth ───────────────────────────────────────────────────────────────

export async function loginAdmin(
  email: string,
  password: string,
): Promise<LoginResult> {
  return postFormLogin('/auth/admin/login', email, password);
}

export async function loginAdminMfa(
  partial_token: string,
  totp_code: string,
): Promise<LoginResponse> {
  const body: MFALoginRequest = { partial_token, totp_code };
  const { data } = await apiClient.post<LoginResponse>(
    '/auth/admin/mfa-login',
    body,
  );
  return data;
}

// ─── Token refresh ────────────────────────────────────────────────────────────

export async function refreshToken(): Promise<string> {
  const { data } = await apiClient.post<RefreshResponse>('/auth/refresh');
  return data.access_token;
}

// ─── Commit login response to Zustand store ──────────────────────────────────
// Call this after receiving a successful LoginResponse (non-MFA or post-MFA).
// Decodes the JWT to extract user_id and email (used as display name fallback).

export function commitLogin(
  tokens: LoginResponse,
  role: 'doctor' | 'admin',
): void {
  const payload = decodeJwtPayload(tokens.access_token);

  const user_id =
    role === 'doctor'
      ? (payload['doctor_id'] as number)
      : (payload['admin_id'] as number);

  const user_name = (payload['name'] as string) ?? (payload['sub'] as string) ?? '';

  useAuthStore.getState().setAuth({
    access_token: tokens.access_token,
    role,
    user_id,
    user_name,
  });
}

// ─── Logout ───────────────────────────────────────────────────────────────────

export function logout(): void {
  // Fire-and-forget: ask the server to delete the HttpOnly refresh_token cookie.
  // We don't await this — the user sees instant logout regardless of network speed.
  // The cookie path /api/v1/auth matches set_cookie() exactly, so the browser
  // drops it the moment the Set-Cookie: Max-Age=0 response arrives.
  // withCredentials on apiClient ensures the cookie is sent with the request.
  apiClient.post('/auth/logout').catch(() => {
    // Network failure is acceptable here — the access token will expire in 15
    // minutes on its own, and the refresh cookie may still be valid but that's
    // a residual risk we accept rather than trapping the user in a logged-in state.
  });

  // Always clear local state immediately — navigation happens in the caller
  useAuthStore.getState().clearAuth();
}
