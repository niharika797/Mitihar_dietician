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

// ── POST /doctor/patients/{id}/request-renewal ────────────────────────────
export async function requestRenewal(patientId: number) {
  const { data } = await api.post(`/doctor/patients/${patientId}/request-renewal`);
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
