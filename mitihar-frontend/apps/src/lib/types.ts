/**
 * TypeScript interfaces matching Mityahar FastAPI response shapes.
 *
 * These cover the auth layer only. Data-layer types (Patient, Doctor etc.)
 * live in mockData.ts until those screens are wired to the real API.
 */

// ─── Auth responses ──────────────────────────────────────────────────────────

/** Returned by /auth/doctor/login and /auth/admin/login on successful login (no MFA) */
// Audit W-7: doctor/admin logins place refresh_token in an HttpOnly cookie, NOT
// the response body. Marking it optional so the type contract matches reality.
export interface LoginResponse {
  access_token: string;
  refresh_token?: string; // present only for patient login; cookie-based for doctor/admin
  token_type: 'bearer';
}

/** Returned when the account has MFA enabled — client must proceed to step 2 */
export interface MFARequiredResponse {
  mfa_required: true;
  partial_token: string;
}

/** Union type — what login endpoints actually return */
export type LoginResult = LoginResponse | MFARequiredResponse;

/** Returned by /auth/refresh */
export interface RefreshResponse {
  access_token: string;
  token_type: 'bearer';
}

// ─── Decoded JWT claim shapes ────────────────────────────────────────────────
// DoctorTokenClaims, AdminTokenClaims, and TokenClaims were removed — they
// were never imported anywhere. authService.ts decodes JWTs with
// Record<string, unknown> and accesses claims by key directly.
// Restore here if typed JWT decoding is introduced.

// ─── MFA step-2 request bodies ───────────────────────────────────────────────

export interface MFALoginRequest {
  partial_token: string;
  totp_code: string;
}

// ─── Generic API error shape (FastAPI detail) ────────────────────────────────

export interface ApiError {
  detail: string;
}

// ─── Type guard helpers ───────────────────────────────────────────────────────

export function isMFARequired(result: LoginResult): result is MFARequiredResponse {
  return (result as MFARequiredResponse).mfa_required === true;
}

export function isLoginResponse(result: LoginResult): result is LoginResponse {
  return (result as LoginResponse).access_token !== undefined;
}
