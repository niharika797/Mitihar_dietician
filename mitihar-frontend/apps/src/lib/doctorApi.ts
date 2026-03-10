/**
 * doctorApi.ts
 * All TypeScript types and API functions for the Doctor Dashboard.
 * Types mirror the FastAPI Pydantic schemas in app/schemas/doctor.py exactly.
 */

import apiClient from './axios';

// ── Response types ────────────────────────────────────────────────────────────

export interface PatientSummary {
  id: number;
  name: string;
  email: string;
  gender: string;
  subscription_status: string;   // "active" | "inactive" | "expired"
  user_type: string;             // "standalone" | "doctor_assigned"
  date_of_birth: string | null;  // "YYYY-MM-DD"
  bmi: number | null;
  bmr: number | null;
  tdee: number | null;
  meals_per_day: number;
}

export interface PaginatedPatients {
  patients: PatientSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface MealEntry {
  Date: string;
  'Meal Type': string;
  'Menu Names': string;
  'Diet Type': string;
  'Total Calories': number;
  'Total Protein': number;
  'Total Carbs': number;
  'Total Fat': number;
  'Total Fiber': number;
  doctor_note?: string;
  food_id?: number;
}

export interface RecommendationDetail {
  id: number;
  patient_id: number;
  week_start_date: string | null;
  meals: MealEntry[];
  ingredient_checklist: unknown[];
  is_active: boolean;
  generated_by: string;
  doctor_notes: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface PatientRequestDetail {
  id: number;
  patient_id: number;
  doctor_id: number;
  status: string;
  rejection_note: string | null;
  requested_at: string;
  responded_at: string | null;
  patient: PatientSummary;
}

export interface SubscriptionCodeDetail {
  id: number;
  code: string;
  is_used: boolean;
  used_by_patient_id: number | null;
  used_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface MealLogEntry {
  id: number;
  logged_date: string;
  meal_type: string;
  calories_consumed: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  recommendation_id: number | null;
  custom_food_name: string | null;
  notes: string | null;
}

export interface PatientLogsResponse {
  patient_id: number;
  period_days: number;
  meal_logs: MealLogEntry[];
}

export interface PatientProgressEntry {
  log_date: string;
  weight_kg: number | null;
  water_glasses: number | null;
  steps: number | null;
  streak_days: number;
}

export interface PatientProgressResponse {
  patient_id: number;
  period_days: number;
  progress_logs: PatientProgressEntry[];
}

export interface ClinicalNoteResponse {
  id: number;
  doctor_id: number;
  patient_id: number;
  note_type: string;
  content: string;
  is_private: boolean;
  created_at: string;
  updated_at: string;
}

export interface FoodItemSummary {
  id: number;
  recipe_name: string;
  slot_type: string;
  cal_per_serving: number;
  protein_per_serving: number;
  carbs_per_serving: number;
  fat_per_serving: number;
  fiber_per_serving: number;
  diet_type: string;
  meal_time_tags: string[];
  plan_type_tags: string[];
  source: string;
  is_verified: boolean;
  image_url: string | null;
}

export interface DashboardStats {
  total_patients: number;
  active_patients: number;
  pending_requests: number;
  plans_generated_this_week: number;
  inactive_patients: { patient_id: number; name: string; email: string }[];
  expiring_soon: { patient_id: number; name: string; subscription_end_date: string }[];
}

export interface RecipeCreateBody {
  recipe_name: string;
  slot_type: string;
  cal_per_serving: number;
  protein_per_serving: number;
  carbs_per_serving: number;
  fat_per_serving: number;
  fiber_per_serving: number;
  diet_type: string;
  meal_time_tags: string[];
  plan_type_tags: string[];
  ingredients: { name: string; amount_g: number }[];
  region_tags: string[];
}

// ── API functions ─────────────────────────────────────────────────────────────

export const doctorApi = {
  // Dashboard
  getDashboard: () =>
    apiClient.get<DashboardStats>('/doctor/dashboard').then(r => r.data),

  // Patients
  listPatients: (page: number, search: string) =>
    apiClient
      .get<PaginatedPatients>('/doctor/patients', {
        params: { page, page_size: 10, ...(search.trim() ? { search: search.trim() } : {}) },
      })
      .then(r => r.data),

  getPatient: (id: number) =>
    apiClient.get<PatientSummary>(`/doctor/patients/${id}`).then(r => r.data),

  // Plans
  getPatientPlan: (id: number) =>
    apiClient
      .get<RecommendationDetail>(`/doctor/patients/${id}/plan`)
      .then(r => r.data),

  // Logs
  getPatientLogs: (id: number, days = 7) =>
    apiClient
      .get<PatientLogsResponse>(`/doctor/patients/${id}/logs`, { params: { days } })
      .then(r => r.data),

  // Notes
  getPatientNotes: (id: number) =>
    apiClient
      .get<ClinicalNoteResponse[]>(`/doctor/patients/${id}/notes`)
      .then(r => r.data),

  addPatientNote: (id: number, content: string, note_type = 'general') =>
    apiClient
      .post<ClinicalNoteResponse>(`/doctor/patients/${id}/notes`, {
        content,
        note_type,
        is_private: true,
      })
      .then(r => r.data),

  // Requests
  listRequests: () =>
    apiClient.get<PatientRequestDetail[]>('/doctor/requests').then(r => r.data),

  acceptRequest: (id: number) =>
    apiClient.post(`/doctor/requests/${id}/accept`).then(r => r.data),

  rejectRequest: (id: number, rejection_note?: string) =>
    apiClient
      .post(`/doctor/requests/${id}/reject`, { rejection_note: rejection_note ?? null })
      .then(r => r.data),

  // Subscription codes
  listCodes: () =>
    apiClient
      .get<SubscriptionCodeDetail[]>('/doctor/subscription-codes')
      .then(r => r.data),

  generateCodes: (count: number, expires_in_days = 30) =>
    apiClient
      .post<SubscriptionCodeDetail[]>('/doctor/subscription-codes', {
        count,
        expires_in_days,
      })
      .then(r => r.data),

  // Plan override
  overridePlan: (id: number, body: { meals?: unknown[]; doctor_notes?: string }) =>
    apiClient.put<RecommendationDetail>(`/doctor/patients/${id}/plan`, body).then(r => r.data),

  // Recipe assign
  assignRecipe: (
    recipeId: number,
    body: { patient_ids: number[]; meal_type: string; meal_date: string; note?: string },
  ) => apiClient.post(`/doctor/recipes/${recipeId}/assign`, body).then(r => r.data),

  // MFA setup flow (auth endpoints, not doctor endpoints)
  mfaSetup: () =>
    apiClient
      .post<{ message: string; totp_uri: string }>('/auth/doctor/mfa-setup')
      .then(r => r.data),

  mfaConfirm: (totp_code: string) =>
    apiClient
      .post<{ message: string }>('/auth/doctor/mfa-confirm', { totp_code })
      .then(r => r.data),

  mfaDisable: (totp_code: string) =>
    apiClient
      .post<{ message: string }>('/auth/doctor/mfa-disable', { totp_code })
      .then(r => r.data),

  // Fetch all patients (for assign modal — page_size=100)
  listAllPatients: () =>
    apiClient
      .get<PaginatedPatients>('/doctor/patients', { params: { page: 1, page_size: 100 } })
      .then(r => r.data.patients),

  // Recipes
  browseRecipes: (params: { search?: string; meal_time?: string; page?: number }) =>
    apiClient
      .get<FoodItemSummary[]>('/doctor/recipes', {
        params: { page_size: 20, page: 1, ...params },
      })
      .then(r => r.data),

  addRecipe: (body: RecipeCreateBody) =>
    apiClient.post<FoodItemSummary>('/doctor/recipes', body).then(r => r.data),
};
