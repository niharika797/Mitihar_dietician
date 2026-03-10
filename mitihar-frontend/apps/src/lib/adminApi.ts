/**
 * adminApi.ts
 * All TypeScript types and API functions for the Admin Dashboard.
 * Types mirror FastAPI Pydantic schemas in app/schemas/admin.py exactly.
 */

import apiClient from './axios';

// ── Response types ────────────────────────────────────────────────────────────

export interface DoctorAdminView {
  id: number;
  email: string;
  name: string;
  phone: string | null;
  specialization: string | null;
  clinic_name: string | null;
  city: string | null;
  is_active: boolean;
  created_at: string;
}

export interface DoctorDetailView extends DoctorAdminView {
  patient_count: number;
  mfa_enabled: boolean;
}

export interface PlatformStats {
  total_patients: number;
  active_subscriptions: number;
  total_doctors: number;
  total_plans_generated: number;
}

export interface AdminPatientView {
  id: number;
  name: string;
  email: string;
  gender: string;
  subscription_status: string;
  user_type: string;
  doctor_id: number | null;
  bmi: number | null;
  created_at: string;
}

export interface PaginatedAdminPatients {
  patients: AdminPatientView[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLogEntry {
  id: number;
  actor_id: number;
  actor_role: string;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  detail: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export interface PaginatedAuditLogs {
  logs: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface CodeAdminView {
  id: number;
  doctor_id: number;
  code: string;
  is_used: boolean;
  used_by_patient_id: number | null;
  expires_at: string | null;
  created_at: string;
}

export interface FoodAdminView {
  id: number;
  recipe_name: string;
  slot_type: string;
  diet_type: string;
  source: string;
  is_verified: boolean;
  cal_per_serving: number;
  created_at: string;
}

export interface BillingDoctor {
  doctor_id: number;
  name: string;
  email: string;
  codes_issued: number;
  codes_used: number;
}

export interface BillingOverview {
  total_codes_issued: number;
  total_codes_used: number;
  unused_codes: number;
  doctors: BillingDoctor[];
}

export interface CreateDoctorBody {
  email: string;
  password: string;
  name: string;
  phone?: string;
  specialization?: string;
  clinic_name?: string;
  city?: string;
}

// ── API functions ─────────────────────────────────────────────────────────────

export const adminApi = {
  // ── Stats ──────────────────────────────────────────────────────────────────
  getStats: () =>
    apiClient.get<PlatformStats>('/admin/stats').then(r => r.data),

  // ── Doctors ────────────────────────────────────────────────────────────────
  listDoctors: () =>
    apiClient.get<DoctorAdminView[]>('/admin/doctors').then(r => r.data),

  createDoctor: (body: CreateDoctorBody) =>
    apiClient.post<DoctorAdminView>('/admin/doctors', body).then(r => r.data),

  deactivateDoctor: (id: number) =>
    apiClient.patch(`/admin/doctors/${id}/deactivate`).then(r => r.data),

  deleteDoctor: (id: number) =>
    apiClient.delete(`/admin/doctors/${id}`).then(r => r.data),

  // ── Patients ───────────────────────────────────────────────────────────────
  listPatients: (page: number, search: string) =>
    apiClient
      .get<PaginatedAdminPatients>('/admin/patients', {
        params: { page, page_size: 15, ...(search.trim() ? { search: search.trim() } : {}) },
      })
      .then(r => r.data),

  overrideSubscription: (id: number, status: string, days = 30) =>
    apiClient
      .patch(`/admin/patients/${id}/subscription/override`, null, {
        params: { status, days },
      })
      .then(r => r.data),

  erasePatient: (id: number) =>
    apiClient.delete(`/admin/patients/${id}`).then(r => r.data),

  // ── Food database ──────────────────────────────────────────────────────────
  listFood: (params: { source?: string; is_verified?: boolean; page?: number; page_size?: number }) =>
    apiClient
      .get<FoodAdminView[]>('/admin/food', { params: { page: 1, page_size: 50, ...params } })
      .then(r => r.data),

  approveFood: (id: number) =>
    apiClient.patch(`/admin/food/${id}/approve`).then(r => r.data),

  rejectFood: (id: number, reason?: string) =>
    apiClient
      .patch(`/admin/food/${id}/reject`, null, { params: reason ? { reason } : {} })
      .then(r => r.data),

  deleteFood: (id: number) =>
    apiClient.delete(`/admin/food/${id}`).then(r => r.data),

  // ── Billing ────────────────────────────────────────────────────────────────
  getBilling: () =>
    apiClient.get<BillingOverview>('/admin/billing').then(r => r.data),

  markPaid: (doctorId: number, body: { amount?: number; notes?: string; period?: string }) =>
    apiClient.post(`/admin/billing/${doctorId}/mark-paid`, body).then(r => r.data),

  // ── Codes ──────────────────────────────────────────────────────────────────
  generateCodes: (body: { doctor_id: number; count: number; expires_in_days?: number }) =>
    apiClient
      .post<CodeAdminView[]>('/admin/codes/generate', { expires_in_days: 30, ...body })
      .then(r => r.data),

  listCodes: (doctor_id?: number) =>
    apiClient
      .get<CodeAdminView[]>('/admin/codes', { params: doctor_id ? { doctor_id } : {} })
      .then(r => r.data),

  // ── Audit logs ─────────────────────────────────────────────────────────────
  getAuditLogs: (params: { page?: number; actor_role?: string; action?: string }) =>
    apiClient
      .get<PaginatedAuditLogs>('/admin/audit-logs', {
        params: { page_size: 50, page: 1, ...params },
      })
      .then(r => r.data),
};
