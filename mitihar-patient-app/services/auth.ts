import api from "../lib/axios";
import type { TokenResponse, GoogleVerifyResponse } from "../types";

// ── POST /auth/register ────────────────────────────────────────────────────
export interface RegisterPayload {
  email: string;
  password: string;
  name: string;
  gender: string;
  height: number;
  weight: number;
  activity_level: string;
  diet: string;
  health_condition: string;
  doctor_code?: string;
}

export async function registerPatient(payload: RegisterPayload) {
  const { data } = await api.post("/auth/register", payload);
  // Audit W-3: backend returns { message, doctor_connected } only — no user_id field.
  // Removed user_id from cast to prevent callers from reading undefined as a number.
  return data as { message: string; doctor_connected: boolean };
}

// ── POST /auth/token (form-encoded) ───────────────────────────────────────
export async function loginPatient(email: string, password: string): Promise<TokenResponse> {
  const form = new URLSearchParams({ username: email, password });
  const { data } = await api.post("/auth/token", form.toString(), {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data as TokenResponse;
}

// ── POST /auth/google/verify ───────────────────────────────────────────────
export async function verifyGoogleToken(id_token: string): Promise<GoogleVerifyResponse> {
  const { data } = await api.post("/auth/google/verify", { id_token });
  return data as GoogleVerifyResponse;
}

// ── POST /auth/logout ──────────────────────────────────────────────────────
export async function logoutPatient() {
  await api.post("/auth/logout");
}
