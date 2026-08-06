import api from "../lib/axios";
import type { PatientProfile, OnboardingPayload, BMIResponse, ActivateResponse, RequestStatusResponse } from "../types";

// ── GET /users/me ──────────────────────────────────────────────────────────
export async function getMyProfile(): Promise<PatientProfile> {
  const { data } = await api.get("/users/me");
  return data;
}

// ── PUT /users/me ──────────────────────────────────────────────────────────
export async function updateProfile(payload: Partial<PatientProfile>): Promise<PatientProfile> {
  const { data } = await api.put("/users/me", payload);
  return data;
}

// ── GET /users/bmi ─────────────────────────────────────────────────────────
export async function getBMI(): Promise<BMIResponse> {
  const { data } = await api.get("/users/bmi");
  return data;
}

// ── POST /patients/onboarding ─────────────────────────────────────────────
export async function submitOnboarding(payload: OnboardingPayload) {
  const { data } = await api.post("/patients/onboarding", payload);
  return data;
}

// ── POST /patients/disclaimer ─────────────────────────────────────────────
export async function acceptDisclaimer() {
  const { data } = await api.post("/patients/disclaimer", {});
  return data;
}

// ── POST /patients/activate ────────────────────────────────────────────────
// Audit M-5: callers MUST store both tokens from the response in SecureStore:
//   await SecureStore.setItemAsync(SECURE_KEYS.ACCESS_TOKEN,  result.access_token);
//   await SecureStore.setItemAsync(SECURE_KEYS.REFRESH_TOKEN, result.refresh_token);
// Without this the patient's old refresh_token is used until it expires (7 days),
// at which point silent refresh fails and the user is forcibly logged out.
export async function activateSubscription(code: string): Promise<ActivateResponse> {
  const { data } = await api.post("/patients/activate", { code });
  return data;
}

// ── POST /patients/request-doctor ─────────────────────────────────────────
export async function requestDoctor(doctor_id: number) {
  const { data } = await api.post("/patients/request-doctor", { doctor_id });
  return data;
}

// ── GET /patients/request-status ──────────────────────────────────────────
export async function getRequestStatus(): Promise<RequestStatusResponse> {
  const { data } = await api.get("/patients/request-status");
  return data;
}

// ── GET /patients/doctors ──────────────────────────────────────────────────
export interface PublicDoctor {
  id: number;
  name: string;
  specialization: string | null;
  clinic_name: string | null;
  city: string | null;
  state: string | null;
  experience_years: number;
  fee_per_month: number;
  rating: number;
  review_count: number;
  is_accepting: boolean;
}

export async function listDoctors(search?: string): Promise<PublicDoctor[]> {
  const { data } = await api.get("/patients/doctors", {
    params: search ? { search } : undefined,
  });
  return data;
}

// ── POST /patients/request-renewal ───────────────────────────────────────
// Audit C-5: was calling /doctor/patients/{id}/request-renewal which is
// blocked by DoctorIsolationMiddleware for patient JWTs (always 403).
// Patient ID is resolved server-side from the JWT — no path param needed.
export async function requestRenewal() {
  const { data } = await api.post(`/patients/request-renewal`);
  return data;
}

// ── GET /patients/my-visit ─────────────────────────────────────────────────
export interface MyVisitResponse {
  has_visit: boolean;
  token_2: string | null;
  visit_counter: number;
  cycle_start: string | null;
  cycle_expiry: string | null;
  last_charged_at: string | null;
}

export async function getMyVisit(): Promise<MyVisitResponse> {
  const { data } = await api.get("/patients/my-visit");
  return data;
}

// ── GET /patients/pending-visits ───────────────────────────────────────────
// Visits the doctor flagged because Token 2 could not be shown. Nothing is
// charged until the patient answers here, so this is the only place a pending
// charge is visible to them.
export interface PendingVisit {
  id: number;
  doctor_id: number;
  doctor_name: string;
  visit_date: string;
  reason_code: string | null;
  /** Server-resolved label from a fixed vocabulary. */
  reason_label: string;
  /** Only set when the doctor chose "other" — preset reasons carry no free text. */
  doctor_note: string | null;
  status: string;
  created_at: string | null;
}

export async function getPendingVisits(): Promise<PendingVisit[]> {
  const { data } = await api.get("/patients/pending-visits");
  return data;
}

// ── POST /patients/pending-visits/{id}/respond ─────────────────────────────
export interface RespondVisitResult {
  status: "approved" | "rejected";
  charged: boolean;
  visit_counter?: number;
  message: string;
}

export async function respondToPendingVisit(
  approvalId: number,
  action: "approve" | "reject",
): Promise<RespondVisitResult> {
  const { data } = await api.post(
    `/patients/pending-visits/${approvalId}/respond`,
    { action },
  );
  return data;
}

// ── DELETE /users/me ───────────────────────────────────────────────────────
// Patient self-delete with password confirmation.
// Backend anonymises PII and hard-deletes all associated logs.
// Throws on wrong password (401) or Google account (400).
export async function deleteMyAccount(password: string): Promise<void> {
  await api.delete("/users/me", { data: { password } });
}
