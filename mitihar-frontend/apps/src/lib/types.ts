/**
 * TypeScript interfaces matching Mityahar FastAPI response shapes.
 *
 * These cover the auth layer only. Data-layer types (Patient, Doctor etc.)
 * live in mockData.ts until those screens are wired to the real API.
 */

// ─── Auth responses ──────────────────────────────────────────────────────────

/** Returned by /auth/doctor/login and /auth/admin/login on successful login (no MFA) */
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
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
// These are what you get after decoding the access_token with jwt-decode.
// We use them to extract user_id and user_name after login.

export interface DoctorTokenClaims {
  sub: string;       // email
  role: 'doctor';
  user_type: 'doctor';
  doctor_id: number;
  exp: number;
  iat: number;
  nbf: number;
}

export interface AdminTokenClaims {
  sub: string;       // email
  role: 'admin';
  user_type: 'admin';
  admin_id: number;
  exp: number;
  iat: number;
  nbf: number;
}

export type TokenClaims = DoctorTokenClaims | AdminTokenClaims;

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
